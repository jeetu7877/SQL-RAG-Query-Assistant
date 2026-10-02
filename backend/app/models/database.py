from typing import Optional

from pydantic import BaseModel, Field


class DatabaseConnectRequest(BaseModel):
    database_url: str = Field(..., min_length=10)


class DatabaseConnectResponse(BaseModel):
    connection_id: str
    database_type: str = "postgresql"
    database_name: str
    host: str
    status: str = "connected"


class ColumnSchema(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str] = None
    primary_key: bool = False
    foreign_key: bool = False


class ForeignKeySchema(BaseModel):
    columns: list[str]
    referred_table: str
    referred_columns: list[str]


class IndexSchema(BaseModel):
    name: str
    columns: list[str]
    unique: bool = False


class TableSchema(BaseModel):
    name: str
    columns: list[ColumnSchema]
    primary_keys: list[str] = []
    foreign_keys: list[ForeignKeySchema] = []
    indexes: list[IndexSchema] = []
    row_estimate: Optional[int] = None


class RelationshipSchema(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class SchemaResponse(BaseModel):
    database_name: str
    host: str
    tables: list[TableSchema]
    relationships: list[RelationshipSchema]
    table_count: int
    column_count: int
    relationship_count: int
