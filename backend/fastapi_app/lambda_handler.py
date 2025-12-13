from __future__ import annotations

from typing import Any, Dict

from mangum import Mangum

from backend.fastapi_app.main import app


def handler(event: Dict[str, Any], context: Any):
    """
    API Gateway HTTP API (payload v2.0) + Lambda Proxy を想定。

    ステージ付きURLの場合、API Gateway は rawPath に /dev や /prod を含めて渡すため、
    FastAPI 側では /csv/... のルートと一致せず 404 になりがち。

    requestContext.stage を参照して api_gateway_base_path を動的に設定し、
    /{stage} を剥がしたパスで FastAPI に渡す。
    """
    stage = event.get("requestContext", {}).get("stage")

    # stage が "$default" の場合は通常 base path を付けない
    if stage and stage != "$default":
        base_path = f"/{stage}"
    else:
        base_path = None

    asgi_handler = Mangum(app, api_gateway_base_path=base_path)
    return asgi_handler(event, context)

