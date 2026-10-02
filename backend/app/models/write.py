from typing import Optional

from pydantic import BaseModel, Field


class WritePreviewRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1500)


class WritePreviewResponse(BaseModel):
    token: str
    sql: str
    table: str
    row_count: Optional[int] = None  # None for INSERT ... SELECT
    expires_in_seconds: int


class WriteConfirmRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=100)


class WriteConfirmResponse(BaseModel):
    inserted_rows: int
    table: str
    execution_time_ms: float
    message: str
