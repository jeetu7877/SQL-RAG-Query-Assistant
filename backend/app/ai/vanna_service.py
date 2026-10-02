"""Text-to-SQL using Vanna 0.7.x (legacy API) + Google Gemini + ChromaDB.

We use ONE Vanna API generation: the classic `VannaBase` mixin style
(vector store class + LLM class). Vanna 2.x (agent API) is NOT used.

Isolation: one Vanna instance (and one on-disk Chroma folder) per schema
fingerprint, so embeddings from different databases never mix.
Only table DDL (structure) is sent to Gemini - never credentials or row data.
"""
import logging
import os
import re
import threading

from google import genai
from google.genai import errors as genai_errors
from vanna.base import VannaBase
from vanna.chromadb import ChromaDB_VectorStore

from app.core.config import get_settings
from app.database.schema_inspector import schema_fingerprint, tables_to_ddl
from app.models.database import TableSchema

logger = logging.getLogger("vanna_service")


class AIServiceError(Exception):
    """Safe, user-facing AI error."""


class AIQuotaError(AIServiceError):
    pass


class GeminiChat(VannaBase):
    """Minimal Gemini adapter (the bundled Vanna class pulls in the Vertex AI SDK)."""

    def __init__(self, config=None):
        VannaBase.__init__(self, config=config)
        self.client = genai.Client(api_key=config["api_key"])
        self.model_name = config["model_name"]
        self.temperature = config.get("temperature", 0.1)

    def system_message(self, message: str):
        return message

    def user_message(self, message: str):
        return message

    def assistant_message(self, message: str):
        return message

    def submit_prompt(self, prompt, **kwargs) -> str:
        text = "\n\n".join(prompt) if isinstance(prompt, list) else str(prompt)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=text,
            config={"temperature": self.temperature},
        )
        return response.text or ""

    def log(self, message: str, title: str = "Info"):
        logger.debug("%s: %s", title, message)  # keep prompts out of normal logs


class PostgresVanna(ChromaDB_VectorStore, GeminiChat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        GeminiChat.__init__(self, config=config)


_INITIAL_PROMPT = (
    "You are a PostgreSQL expert. Generate exactly ONE read-only PostgreSQL SELECT query "
    "(CTEs allowed) that answers the question, using only the tables and columns in the "
    "context. Never write INSERT/UPDATE/DELETE/DDL. Quote identifiers with double quotes "
    "when they contain capitals or special characters. Return only the SQL. "
)

_RULES_DOC = (
    "PostgreSQL rules: use ILIKE for case-insensitive text matching; use date_trunc / "
    "CURRENT_DATE / INTERVAL for date logic; use ::numeric casts before ROUND(); "
    "join tables through the foreign keys shown in the DDL."
)

# Test hook: lets tests inject an offline embedding function.
_embedding_function = None

_instances: dict[str, PostgresVanna] = {}
_lock = threading.Lock()


def _build(fingerprint: str, tables: list[TableSchema]) -> PostgresVanna:
    s = get_settings()
    if not s.google_api_key:
        raise AIServiceError("The AI service is not configured. Set GOOGLE_API_KEY on the server.")
    path = os.path.join(s.vanna_data_dir, fingerprint)  # isolated per schema
    extra = {"embedding_function": _embedding_function} if _embedding_function else {}
    vn = PostgresVanna(
        config={
            **extra,
            "path": path,
            "api_key": s.google_api_key,
            "model_name": s.gemini_model,
            "dialect": "PostgreSQL",
            "initial_prompt": _INITIAL_PROMPT,
            "n_results_ddl": 8,
            "n_results_sql": 3,
            "n_results_documentation": 2,
        }
    )
    # Train once per fingerprint (ids are deterministic, so this is idempotent anyway)
    if vn.ddl_collection.count() == 0:
        for ddl in tables_to_ddl(tables):
            vn.add_ddl(ddl)
        vn.add_documentation(_RULES_DOC)
    return vn


def get_vanna(tables: list[TableSchema]) -> PostgresVanna:
    fingerprint = schema_fingerprint(tables)
    with _lock:
        if fingerprint not in _instances:
            _instances[fingerprint] = _build(fingerprint, tables)
        return _instances[fingerprint]


def generate_sql(question: str, tables: list[TableSchema]) -> str:
    """One Gemini call. Returns raw SQL text (to be validated by the caller)."""
    vn = get_vanna(tables)
    try:
        return vn.generate_sql(question=question)
    except AIServiceError:
        raise
    except Exception as exc:
        code = getattr(exc, "code", None)
        logger.error(
            "Gemini error: %s code=%s status=%s msg=%s",
            type(exc).__name__, code, getattr(exc, "status", None),
            str(getattr(exc, "message", "") or exc)[:300],
        )
        if code == 429 or "RESOURCE_EXHAUSTED" in str(exc):
            raise AIQuotaError("AI service quota has been exceeded. Please try again later.")
        if code == 404:
            raise AIServiceError("Gemini model not found. Update GEMINI_MODEL in backend/.env.")
        if code in (400, 403):
            raise AIServiceError("Gemini rejected the request. Check GOOGLE_API_KEY and GEMINI_MODEL.")
        raise AIServiceError("The AI service could not generate a query. Please try again.")


def clean_sql(raw: str) -> str:
    """Strip markdown fences / trailing semicolons the model may add."""
    raw = re.sub(r"^```(?:sql)?|```$", "", raw.strip(), flags=re.I | re.M).strip()
    return raw.rstrip(";").strip() if raw.count(";") <= 1 else raw
