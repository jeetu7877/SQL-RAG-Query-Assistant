from app.database.connection_manager import ConnectionManager
from app.database.schema_inspector import inspect_schema, schema_fingerprint, tables_to_ddl


def test_inspects_tables_columns_and_relationships(db_url):
    mgr = ConnectionManager()
    cid, active = mgr.create_connection(db_url)
    try:
        tables, rels = inspect_schema(active.engine, use_cache=False)
        by_name = {t.name: t for t in tables}
        assert {"customers", "orders", "products", "employees"} <= set(by_name)

        orders = by_name["orders"]
        assert "id" in orders.primary_keys
        cust_col = next(c for c in orders.columns if c.name == "customer_id")
        assert cust_col.foreign_key and not cust_col.nullable
        assert any(
            r.from_table == "orders" and r.from_column == "customer_id"
            and r.to_table == "customers" and r.to_column == "id"
            for r in rels
        )
        assert by_name["orders"].indexes

        ddl = "\n".join(tables_to_ddl(tables))
        assert 'CREATE TABLE "customers"' in ddl and "FOREIGN KEY" in ddl
        assert schema_fingerprint(tables) == schema_fingerprint(tables)
    finally:
        mgr.remove_connection(cid)
