"""
Generate OpenAPI spec from FastAPI app without starting the server.

Usage:
    cd backend
    python scripts/generate_openapi.py

Output:
    docs/api/openapi.json  (relative to repo root)
"""
import json
import sys
import os

# Add backend directory to path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables required by app.config before importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/placeholder")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET", "placeholder-for-openapi-generation")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRY_HOURS", "24")
os.environ.setdefault("ENCRYPTION_KEY", "placeholder-32-char-key-for-gen=")
os.environ.setdefault("ANTHROPIC_API_KEY", "placeholder")

from app.main import app  # noqa: E402 — imports after sys.path setup

spec = app.openapi()

output_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "api", "openapi.json"
)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

path_count = len(spec.get("paths", {}))
schema_count = len(spec.get("components", {}).get("schemas", {}))
print(f"OpenAPI spec written to: {output_path}")
print(f"  Paths:   {path_count}")
print(f"  Schemas: {schema_count}")
print(f"  Version: {spec.get('info', {}).get('version', 'unknown')}")
