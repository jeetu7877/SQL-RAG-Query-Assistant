from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "writes_enabled": s.allow_writes}
