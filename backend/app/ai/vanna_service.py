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

from chromadb import Documents, EmbeddingFunction, Embeddings
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


class GeminiEmbedding(EmbeddingFunction):
    """Embeddings via the Gemini API: no local ONNX model, so far less RAM (fits Render free)."""

    DIM = 768

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    @staticmethod
    def name() -> str:
        return "gemini-embedding"

    def __call__(self, input: Documents) -> Embeddings:
        out: list[list[float]] = []
        texts = list(input)
        for i in range(0, len(texts), 50):  # API batch limit is 100
            res = self.client.models.embed_content(
                model=self.model,
                contents=texts[i : i + 50],
                config={"output_dimensionality": self.DIM},
            )
            out.extend(e.values for e in res.embeddings)
        return out


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

_INSERT_PROMPT = (
    "You are a PostgreSQL expert. Write exactly ONE INSERT statement for the user's request, using only "
    "the tables and columns in the context. Rules: use ONLY values the user gave - never invent data; "
    "leave out auto-generated columns (serial/identity ids and columns with defaults) unless the user "
    "supplied them; use single quotes for text; no RETURNING, no ON CONFLICT DO UPDATE, no UPDATE/DELETE/DDL. "
    "If a required (NOT NULL, no default) value is missing, or the request is not an insert, reply with "
    "exactly: CANNOT_INSERT: <short reason>. Return only the SQL. "
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
    emb = _embedding_function or GeminiEmbedding(s.google_api_key, s.embedding_model)
    tag = f"{fingerprint}-{s.embedding_model}-{GeminiEmbedding.DIM}"
    path = os.path.join(s.vanna_data_dir, tag)  # isolated per schema + embedding model
    vn = PostgresVanna(
        config={
            "embedding_function": emb,
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
    try:
        vn = get_vanna(tables)
        return vn.generate_sql(question=question)
    except AIServiceError:
        raise
    except Exception as exc:
        code = getattr(exc, "code", None) if isinstance(exc, genai_errors.APIError) else None
        # log class, HTTP code and the first 200 chars of the message (never keys, URLs or prompts)
        logger.error("Gemini/Vanna error: %s code=%s msg=%s", type(exc).__name__, code,
                     str(getattr(exc, "message", "") or exc)[:200])
        if code == 429 or "RESOURCE_EXHAUSTED" in str(exc):
            raise AIQuotaError("AI service quota has been exceeded. Please try again later.")
        if code == 404:
            raise AIServiceError("Gemini model not found. Check GEMINI_MODEL / EMBEDDING_MODEL on the server.")
        if code in (400, 403):
            raise AIServiceError("Gemini rejected the request. Check GOOGLE_API_KEY and the model names.")
        raise AIServiceError("The AI service could not generate a query. Please try again.")


def generate_insert(request: str, tables: list[TableSchema]) -> str:
    """One Gemini call that produces an INSERT (or 'CANNOT_INSERT: reason'). Always validated afterwards."""
    try:
        vn = get_vanna(tables)
        prompt = vn.get_sql_prompt(
            initial_prompt=_INSERT_PROMPT,
            question=request,
            question_sql_list=[],
            ddl_list=vn.get_related_ddl(request),
            doc_list=[],
        )
        return vn.submit_prompt(prompt)
    except AIServiceError:
        raise
    except Exception as exc:
        code = getattr(exc, "code", None) if isinstance(exc, genai_errors.APIError) else None
        logger.error("Gemini/Vanna error: %s code=%s", type(exc).__name__, code)
        if code == 429 or "RESOURCE_EXHAUSTED" in str(exc):
            raise AIQuotaError("AI service quota has been exceeded. Please try again later.")
        raise AIServiceError("The AI service could not generate the insert. Please try again.")


def clean_sql(raw: str) -> str:
    """Strip markdown fences / trailing semicolons the model may add."""
    raw = re.sub(r"^```(?:sql)?|```$", "", raw.strip(), flags=re.I | re.M).strip()
    return raw.rstrip(";").strip() if raw.count(";") <= 1 else raw
