from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, List, Dict

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


Mode = Literal["escape", "analyze", "sanitize"]
LineEnding = Literal["auto", "lf", "crlf"]
EscapeStyle = Literal["rfc4180", "double", "backslash", "none"]
HasHeader = Literal["auto"] | bool
TargetProfile = Literal["excel", "db_rfc4180", "ai_safety", "custom"]
QuotePolicy = Literal["minimal", "all", "non_numeric"]
ExcelInjectionProtection = Literal["none", "prefix_quote", "strip_formula"]
TrimWhitespace = Literal["none", "left", "right", "both"]


class ResponseLevel(str, Enum):
    """
    Response verbosity level.
    - simple   : Minimal payload for end-users (csv_text + minimal meta)
    - standard : Includes issues + stats + effective_config
    - debug    : Full response for diagnostics (includes structure_stats_before, etc.)
    """

    simple = "simple"
    standard = "standard"
    debug = "debug"


class Issue(BaseModel):
    type: str
    row: Optional[int] = None
    column: Optional[int] = None
    severity: Literal["info", "warning", "error"] = "warning"
    description: str
    fixed: bool = False


class Stats(BaseModel):
    rows: int = 0
    columns_min: int = 0
    columns_max: int = 0
    columns_mode: int = 0
    fixed_issues_count: int = 0
    unfixed_issues_count: int = 0
    delimiter_detected: Optional[str] = None
    has_header: Optional[bool] = None


class CsvEscapeResult(BaseModel):
    """
    result 部は response_level に応じて省略されうるため、
    stats は Optional とする（simple 時は stats なし）。
    """

    csv_text: str
    issues: List[Issue] = Field(default_factory=list)
    stats: Optional[Stats] = None


class CsvEscapeResponse(BaseModel):
    result: CsvEscapeResult
    meta: Dict[str, Any]


class CsvEscapeRequest(BaseModel):
    """
    CSV Escape & Sanitize API (v0.2) リクエストモデル

    基本利用者は以下だけ意識すればよい想定:
      - mode ("escape" / "analyze" / "sanitize")
      - csv_b64
      - target_profile

    それ以外の項目は target_profile ごとのプロファイルがよしなに設定する。
    target_profile="custom" のときのみ、追加オプションを直接制御する想定。
    """

    mode: Mode = "escape"
    csv_b64: str

    # 形式関連（v0.1 と互換）
    delimiter: Optional[str] = None
    quote_char: str = '"'
    escape_style: EscapeStyle = "rfc4180"
    line_ending: LineEnding = "auto"
    has_header: HasHeader = "auto"
    target_profile: TargetProfile = "excel"
    max_rows: int = 0  # 0 の場合は無制限（API 全体の制限は別途）

    # v0.2 追加の詳細オプション
    quote_policy: QuotePolicy = "minimal"
    excel_injection_protection: ExcelInjectionProtection = "none"
    trim_whitespace: TrimWhitespace = "none"
    null_representation: Optional[str] = None
    add_bom: bool = False

    # v0.2 追加: レスポンス冗長度
    response_level: ResponseLevel = Field(
        default=ResponseLevel.simple,
        description="Response verbosity: simple | standard | debug",
    )

    # Pydantic v2: schema_extra -> json_schema_extra
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "mode": "escape",
                "csv_b64": "<Base64 encoded CSV string>",
                "target_profile": "excel",
                "response_level": "simple",
            }
        }
    )

