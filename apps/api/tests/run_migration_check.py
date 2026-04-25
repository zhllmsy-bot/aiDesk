import os
import tempfile

from sqlalchemy import create_engine, inspect

from tests.helpers import run_migrations

tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, "test.db")
database_url = f"sqlite+pysqlite:///{db_path}"
run_migrations(database_url)
print("Migration to head succeeded!")

engine = create_engine(database_url)
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables: {sorted(tables)}")
assert "secrets" in tables, "secrets table missing"
assert "audit_log" in tables, "audit_log table missing"
print("secrets table: OK")
print("audit_log table: OK")

cols = [c["name"] for c in inspector.get_columns("secrets")]
print(f"secrets columns: {cols}")
assert "project_id" in cols
assert "name" in cols
assert "scope" in cols
assert "encrypted_value" in cols
assert "expires_at" in cols
assert "created_by" in cols

cols = [c["name"] for c in inspector.get_columns("audit_log")]
print(f"audit_log columns: {cols}")
assert "event_type" in cols
assert "project_id" in cols
assert "actor" in cols
assert "resource_kind" in cols
assert "resource_id" in cols
assert "detail_json" in cols
assert "occurred_at" in cols

print("ALL MIGRATION CHECKS PASSED")
