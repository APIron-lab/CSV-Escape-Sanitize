from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ============================================================
# プロジェクトルートを sys.path に追加
# （Lambda / uvicorn どちらでも core パッケージを解決できるように）
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.csv_escape.models import CsvEscapeRequest  # noqa: E402
from core.csv_escape.service import (  # noqa: E402
    InvalidBase64Error,
    process_csv,
)

# ============================================================
# API Gateway 側で /csv をプレフィックスとしてルーティングしているため、
# FastAPI には root_path="/csv" を指定し、ルート定義は /v0/... にする
# ============================================================
app = FastAPI(
    title="CSV Escape & Sanitize API",
    version="0.1.0",
    description="Pre-AI Input Tools: CSV Escape & Sanitize API (v0.1)",
    root_path="/csv",
)


@app.exception_handler(InvalidBase64Error)
async def invalid_base64_handler(_: Request, exc: InvalidBase64Error) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INVALID_BASE64",
                "message": str(exc),
            },
            "meta": {
                "version": "0.1.0",
            },
        },
    )


# NOTE:
# API Gateway の URL は /dev/csv/v0/escape で来るが、
# FastAPI には root_path="/csv" が入っているため、ここは /v0/escape にする
@app.post("/v0/escape")
async def csv_escape_endpoint(payload: CsvEscapeRequest):
    response = process_csv(payload)
    return response.model_dump()

