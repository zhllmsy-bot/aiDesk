import json
import os
import tempfile

from fastapi.testclient import TestClient

from api.app import create_app
from api.config import Settings

db_path = os.path.join(tempfile.mkdtemp(), "test.db")
settings = Settings(
    database_url=f"sqlite+pysqlite:///{db_path}",
    web_origin="http://localhost:3000",
    temporal_address="localhost:7233",
    temporal_namespace="test",
)

app = create_app(settings, include_runtime_surface=False, include_execution_surface=False)
client = TestClient(app)

print("=== /health/live ===")
resp = client.get("/health/live")
print(f"status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))

print("\n=== /health/ready ===")
resp = client.get("/health/ready")
print(f"status: {resp.status_code}")
data = resp.json()
print(f"overall: {data['status']}")
print(f"required: {json.dumps(data['required'], indent=2)}")
print(f"optional: {json.dumps(data['optional'], indent=2)}")
print(f"degraded_reasons: {data['degraded_reasons']}")

print("\n=== /observability/metrics ===")
resp = client.get("/observability/metrics")
print(f"status: {resp.status_code}")
metrics = resp.json()
print(f"counters: {len(metrics['counters'])}")
print(f"gauges: {len(metrics['gauges'])}")

print("\n=== Correlation Middleware ===")
resp = client.get("/", headers={"X-Trace-ID": "my-trace-123", "X-Request-ID": "my-req-456"})
print(f"X-Trace-ID in response: {resp.headers.get('X-Trace-ID')}")
print(f"X-Request-ID in response: {resp.headers.get('X-Request-ID')}")
