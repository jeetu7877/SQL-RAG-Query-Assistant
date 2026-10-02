"""Dynamic PostgreSQL schema inspection using SQLAlchemy's inspector."""
import hashlib
import json
import threading

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.inspection import inspect

from app.models.database import (
    ColumnSchema,
    ForeignKeySchema,
    IndexSchema,
    RelationshipSchema,
    TableSchema,
)

_cache: dict[int, tuple[list[TableSchema], list[RelationshipSchema]]] = {}
_cache_lock = threading.Lock()


def _row_estimates(engine: Engine, schema: str) -> dict[str, int]:
    """Cheap row estimates from pg_class (no table scans)."""
    sql = text(
        "SELECT c.relname, c.reltuples::bigint FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = :s AND c.relkind IN ('r','p')"
    )
    try:
        with engine.connect() as conn:
            return {r[0]: max(int(r[1]), 0) for r in conn.execute(sql, {"s": schema})}
    except Exception:
        return {}


def inspect_schema(
    engine: Engine, schema: str = "public", use_cache: bool = True
) -> tuple[list[TableSchema], list[RelationshipSchema]]:
    key = id(engine)
    if use_cache:
        with _cache_lock:
            if key in _cache:
                return _cache[key]

    insp = inspect(engine)
    estimates = _row_estimates(engine, schema)
    tables: list[TableSchema] = []
    relationships: list[RelationshipSchema] = []

    for name in sorted(insp.get_table_names(schema=schema)):
        pk = insp.get_pk_constraint(name, schema=schema).get("constrained_columns", []) or []
        fks = insp.get_foreign_keys(name, schema=schema)
        fk_cols = {c for fk in fks for c in fk["constrained_columns"]}

        columns = [
            ColumnSchema(
                name=c["name"],
                type=str(c["type"]),
                nullable=bool(c["nullable"]),
                default=str(c["default"]) if c.get("default") is not None else None,
                primary_key=c["name"] in pk,
                foreign_key=c["name"] in fk_cols,
            )
            for c in insp.get_columns(name, schema=schema)
        ]

        fk_models = []
        for fk in fks:
            fk_models.append(
                ForeignKeySchema(
                    columns=fk["constrained_columns"],
                    referred_table=fk["referred_table"],
                    referred_columns=fk["referred_columns"],
                )
            )
            for src, dst in zip(fk["constrained_columns"], fk["referred_columns"]):
                relationships.append(
                    RelationshipSchema(
                        from_table=name, from_column=src,
                        to_table=fk["referred_table"], to_column=dst,
                    )
                )

        indexes = [
            IndexSchema(
                name=i["name"],
                columns=[c for c in i["column_names"] if c],
                unique=bool(i.get("unique", False)),
            )
            for i in insp.get_indexes(name, schema=schema)
        ]

        tables.append(
            TableSchema(
                name=name, columns=columns, primary_keys=list(pk),
                foreign_keys=fk_models, indexes=indexes,
                row_estimate=estimates.get(name),
            )
        )

    result = (tables, relationships)
    with _cache_lock:
        _cache[key] = result
    return result


def clear_cache(engine: Engine) -> None:
    with _cache_lock:
        _cache.pop(id(engine), None)


def tables_to_ddl(tables: list[TableSchema]) -> list[str]:
    """Render tables as compact DDL strings for the LLM (no credentials, no data)."""
    ddls = []
    for t in tables:
        lines = []
        for c in t.columns:
            line = f'  "{c.name}" {c.type}'
            if not c.nullable:
                line += " NOT NULL"
            lines.append(line)
        if t.primary_keys:
            lines.append("  PRIMARY KEY (" + ", ".join(f'"{k}"' for k in t.primary_keys) + ")")
        for fk in t.foreign_keys:
            lines.append(
                "  FOREIGN KEY (" + ", ".join(f'"{c}"' for c in fk.columns) + ") REFERENCES "
                f'"{fk.referred_table}" (' + ", ".join(f'"{c}"' for c in fk.referred_columns) + ")"
            )
        ddls.append(f'CREATE TABLE "{t.name}" (\n' + ",\n".join(lines) + "\n);")
    return ddls


def schema_fingerprint(tables: list[TableSchema]) -> str:
    payload = json.dumps([t.model_dump(exclude={"row_estimate"}) for t in tables], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
