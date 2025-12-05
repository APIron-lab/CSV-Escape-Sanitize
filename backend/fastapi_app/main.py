# backend/fastapi_app/main.py

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ============================================================
# プロジェクトルートを sys.path に追加
# （uvicorn のリロード子プロセスでも core パッケージを解決できるようにする）
# ============================================================
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.csv_escape.models import CsvEscapeRequest  # noqa: E402
from core.csv_escape.service import (               # noqa: E402
    InvalidBase64Error,
    process_csv,
)

app = FastAPI(
    title="CSV Escape & Sanitize API",
    version="0.1.0",
    description="Pre-AI Input Tools: CSV Escape & Sanitize API (v0.1)",
)


@app.exception_handler(InvalidBase64Error)
async def invalid_base64_handler(_: Request, exc: InvalidBase64Error) -> JSONResponse:
    """Base64 デコードエラーを APIron 風エラー形式で返す"""
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


@app.post("/csv/v0/escape")
async def csv_escape_endpoint(payload: CsvEscapeRequest):
    """CSV Escape & Sanitize API メインエンドポイント"""

    response = process_csv(payload)
    # Pydantic モデルをそのまま dict にして返す
    return response.model_dump()

