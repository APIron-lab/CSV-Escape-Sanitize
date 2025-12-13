from __future__ import annotations

from mangum import Mangum

from backend.fastapi_app.main import app

# API Gateway HTTP API (payload v2.0) + Lambda Proxy に対応
handler = Mangum(app)

