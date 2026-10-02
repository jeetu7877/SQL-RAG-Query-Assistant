"""AST-based read-only SQL validation using SQLGlot (PostgreSQL dialect)."""
import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

DIALECT = "postgres"


class SQLValidationError(Exception):
    pass


# Node types that are never allowed anywhere in the tree (also catches
# data-modifying CTEs such as: WITH x AS (DELETE ... RETURNING *) SELECT ...).
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Merge", "Create", "Drop", "Alter", "AlterTable",
    "TruncateTable", "Command", "Copy", "Grant", "Revoke", "Set", "Transaction",
    "Commit", "Rollback", "Use", "Into", "Lock", "Analyze", "Kill", "Pragma",
    "Declare", "Execute", "Refresh", "Attach", "Detach", "Comment", "LoadData",
]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

# Functions that read files, sleep, change settings, or reach other servers.
FORBIDDEN_FUNCTIONS = {
    "pg_sleep", "pg_sleep_for", "pg_sleep_until", "pg_read_file", "pg_read_binary_file",
    "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export", "lo_get", "lo_put",
    "dblink", "dblink_exec", "set_config", "pg_terminate_backend", "pg_cancel_backend",
    "pg_reload_conf", "pg_rotate_logfile", "pg_advisory_lock", "nextval", "setval",
    "query_to_xml", "database_to_xml", "current_setting",
}


class SQLValidator:
    @staticmethod
    def validate(sql: str, max_rows: int | None = None, pretty: bool = False) -> str:
        """Return cleaned, validated SQL or raise SQLValidationError."""
        if not sql or not sql.strip():
            raise SQLValidationError("Empty SQL.")

        try:
            statements = [s for s in sqlglot.parse(sql.strip(), read=DIALECT) if s is not None]
        except SqlglotError:
            raise SQLValidationError("The SQL could not be parsed.")

        if len(statements) != 1:
            raise SQLValidationError("Exactly one SQL statement is allowed.")

        tree = statements[0]
        if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
            raise SQLValidationError("Only SELECT queries are allowed.")

        for node in tree.walk():
            if isinstance(node, FORBIDDEN_NODES):
                raise SQLValidationError(f"{type(node).__name__.upper()} operations are not allowed.")
            if isinstance(node, exp.Func):
                name = (node.sql_name() if not isinstance(node, exp.Anonymous) else node.name).lower()
                if name in FORBIDDEN_FUNCTIONS:
                    raise SQLValidationError(f"Function {name}() is not allowed.")

        if max_rows:
            tree = SQLValidator._apply_limit(tree, max_rows)

        return tree.sql(dialect=DIALECT, pretty=pretty)

    @staticmethod
    def _apply_limit(tree: exp.Expression, max_rows: int) -> exp.Expression:
        """Add or cap LIMIT on the outermost query. Single-row aggregates are left untouched."""
        if isinstance(tree, exp.Subquery):
            tree = tree.unnest()
        existing = tree.args.get("limit")
        if existing is not None:
            expr = existing.expression
            if isinstance(expr, exp.Literal) and expr.is_int and int(expr.name) <= max_rows:
                return tree
            return tree.limit(max_rows, copy=False)

        if isinstance(tree, exp.Select) and not tree.args.get("group"):
            projections = tree.expressions
            if projections and all(p.find(exp.AggFunc) for p in projections):
                return tree  # e.g. SELECT COUNT(*) FROM users -> always one row
        return tree.limit(max_rows, copy=False)


class InsertCheck:
    """Result of validating a write statement."""

    def __init__(self, sql: str, table: str, row_count: int | None):
        self.sql = sql
        self.table = table
        self.row_count = row_count  # None when it cannot be known up front (INSERT ... SELECT)


def validate_insert(sql: str, allowed_tables: set[str], max_rows: int, pretty: bool = True) -> InsertCheck:
    """Allow exactly ONE plain INSERT into a known public table. Everything else is rejected."""
    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL.")
    try:
        statements = [s for s in sqlglot.parse(sql.strip(), read=DIALECT) if s is not None]
    except SqlglotError:
        raise SQLValidationError("The SQL could not be parsed.")
    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed.")

    tree = statements[0]
    if not isinstance(tree, exp.Insert):
        raise SQLValidationError("Write mode only allows INSERT statements.")

    # nothing other than the root INSERT may modify data (blocks data-modifying CTEs etc.)
    for node in tree.walk():
        if node is tree:
            continue
        if isinstance(node, FORBIDDEN_NODES):
            raise SQLValidationError(f"{type(node).__name__.upper()} operations are not allowed.")
        if isinstance(node, exp.Func):
            name = (node.sql_name() if not isinstance(node, exp.Anonymous) else node.name).lower()
            if name in FORBIDDEN_FUNCTIONS:
                raise SQLValidationError(f"Function {name}() is not allowed.")

    if tree.args.get("returning"):
        raise SQLValidationError("RETURNING is not allowed in write mode.")

    conflict = tree.args.get("conflict")
    if conflict is not None and "DO NOTHING" not in conflict.sql(dialect=DIALECT).upper():
        raise SQLValidationError("ON CONFLICT ... DO UPDATE is not allowed (it modifies existing rows).")

    target = tree.this.this if isinstance(tree.this, exp.Schema) else tree.this
    if not isinstance(target, exp.Table):
        raise SQLValidationError("The INSERT target must be a table.")
    if target.catalog or (target.db and target.db.lower() != "public"):
        raise SQLValidationError("Only tables in the public schema can be written to.")
    if target.name.lower() not in {t.lower() for t in allowed_tables}:
        raise SQLValidationError("The INSERT target is not a known table in this database.")

    row_count = None
    if isinstance(tree.expression, exp.Values):
        row_count = len(tree.expression.expressions)
        if row_count > max_rows:
            raise SQLValidationError(f"At most {max_rows} rows can be inserted at once.")

    return InsertCheck(tree.sql(dialect=DIALECT, pretty=pretty), target.name, row_count)
