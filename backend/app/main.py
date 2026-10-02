import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, database, health
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

# Chroma telemetry off
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

settings = get_settings()
app = FastAPI(title="PostgreSQL Text-to-SQL AI Assistant", version="1.0.0")

origins = {settings.frontend_url, "http://localhost:5173"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Connection-ID"],
)

app.include_router(health.router)
app.include_router(database.router)
app.include_router(chat.router)
