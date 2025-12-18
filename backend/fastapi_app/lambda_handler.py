from __future__ import annotations

import json

from mangum import Mangum

from backend.fastapi_app.main import app


def _safe_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def handler(event, context):
    stage = _safe_get(event, "requestContext", "stage", default=None)
    raw_path = event.get("rawPath")
    http_path = _safe_get(event, "requestContext", "http", "path", default=None)
    method = _safe_get(event, "requestContext", "http", "method", default=None)

    print(
        json.dumps(
            {
                "diag": "incoming_request",
                "stage": stage,
                "method": method,
                "rawPath": raw_path,
                "requestContext.http.path": http_path,
            },
            ensure_ascii=False,
        )
    )

    # ここが本丸：/dev や /prod を Mangum 側で剥がして FastAPI に渡す
    base_path = f"/{stage}" if stage and stage != "$default" else None

    asgi = Mangum(app, api_gateway_base_path=base_path)
    return asgi(event, context)
