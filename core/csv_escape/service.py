from __future__ import annotations

import base64
import csv
import io
import statistics
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict, Any

from .models import (
    CsvEscapeRequest,
    CsvEscapeResult,
    CsvEscapeResponse,
    Issue,
    Stats,
    ResponseLevel,
)


class InvalidBase64Error(Exception):
    """Base64 デコード失敗時に投げる独自例外"""

    pass


@dataclass
class EffectiveConfig:
    """実際に Escape / Sanitize 処理に用いる設定（プロファイル適用・自動判定後の値）"""

    profile: str
    delimiter: str
    quote_char: str
    escape_style: str
    line_ending: str  # "lf" / "crlf"
    quote_policy: str  # "minimal" / "all" / "non_numeric"
    excel_injection_protection: str  # "none" / "prefix_quote" / "strip_formula"
    trim_whitespace: str  # "none" / "left" / "right" / "both"
    null_representation: Optional[str]
    add_bom: bool
    max_rows: int
    has_header: Optional[bool]


# ---------------------------------------------------------------------------
# Base64 / テキストユーティリティ
# ---------------------------------------------------------------------------


def _decode_base64_to_text(csv_b64: str) -> str:
    """Base64 -> UTF-8 テキストに変換

    - 先に空白類（スペース・改行・タブなど）をすべて削除
    - そのうえで validate=True で厳密に Base64 を検証
    """
    try:
        compact = "".join(csv_b64.split())
        raw = base64.b64decode(compact, validate=True)
        return raw.decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise InvalidBase64Error("csv_b64 is not valid Base64 UTF-8 text") from exc


def _normalize_line_endings(text: str) -> tuple[str, str]:
    """改行コードを \n に正規化し、元の代表的な改行種別を返す

    Returns:
        normalized_text: 改行を \n に統一したテキスト
        detected: 'crlf' or 'lf' or 'none'
    """
    if "\r\n" in text:
        detected = "crlf"
        normalized = text.replace("\r\n", "\n")
        normalized = normalized.replace("\r", "\n")
    elif "\r" in text:
        detected = "crlf"
        normalized = text.replace("\r", "\n")
    elif "\n" in text:
        detected = "lf"
        normalized = text
    else:
        detected = "none"
        normalized = text
    return normalized, detected


def _detect_delimiter(line: str) -> str:
    """ごく簡易な区切り文字推定

    - , ; \t | の出現回数を比較し、最多のものを採用
    - どれもほぼ出てこない場合は ',' をデフォルトとする
    """
    candidates = [",", ";", "\t", "|"]
    counts = {c: line.count(c) for c in candidates}
    best = max(counts.items(), key=lambda x: x[1])
    if best[1] == 0:
        return ","
    return best[0]


def _split_rows(text: str) -> List[str]:
    """改行コードを問わず行に分割（解析用・補助関数）"""
    return text.split("\n")


def _rows_from_text(text: str, delimiter: str, quote_char: str) -> List[List[str]]:
    """csv.reader を使って CSV を 2 次元配列として読み出す

    - ここでは RFC4180 風の比較的素直な設定で読む
    - csv.Error が出た場合は「素直な split」にフォールバックする
    """
    rows: List[List[str]] = []

    try:
        reader = csv.reader(
            io.StringIO(text),
            delimiter=delimiter,
            quotechar=quote_char,
            doublequote=True,
            skipinitialspace=False,
        )
        for row in reader:
            rows.append(row)
    except csv.Error:
        for line in _split_rows(text):
            if line == "":
                rows.append([])
            else:
                rows.append(line.split(delimiter))

    return rows


# ---------------------------------------------------------------------------
# 構造解析 / Stats
# ---------------------------------------------------------------------------


def _analyze_structure(
    rows: List[List[str]],
    delimiter: str,
    has_header: bool | None,
) -> Tuple[Stats, List[Issue]]:
    """簡易な構造解析。Sanitize 前の「元データ状態」を表現する。"""
    issues: List[Issue] = []

    non_empty_rows = [r for r in rows if not (len(r) == 0 or (len(r) == 1 and r[0] == ""))]
    if not non_empty_rows:
        stats = Stats(
            rows=0,
            columns_min=0,
            columns_max=0,
            columns_mode=0,
            delimiter_detected=delimiter,
            has_header=has_header,
        )
        return stats, issues

    col_counts = [len(r) for r in non_empty_rows]
    rows_count = len(non_empty_rows)

    columns_min = min(col_counts)
    columns_max = max(col_counts)
    try:
        columns_mode = int(statistics.mode(col_counts))
    except statistics.StatisticsError:
        columns_mode = int(round(statistics.mean(col_counts)))

    fixed = 0
    unfixed = 0

    for i, (col_count) in enumerate(col_counts, start=1):
        if col_count != columns_mode:
            issue = Issue(
                type="COLUMN_COUNT_MISMATCH",
                row=i,
                column=None,
                severity="warning",
                description=(
                    f"Row has {col_count} columns (expected ~{columns_mode}). "
                    "No automatic fix in this step."
                ),
                fixed=False,
            )
            issues.append(issue)
            unfixed += 1

    stats = Stats(
        rows=rows_count,
        columns_min=columns_min,
        columns_max=columns_max,
        columns_mode=columns_mode,
        fixed_issues_count=fixed,
        unfixed_issues_count=unfixed,
        delimiter_detected=delimiter,
        has_header=has_header,
    )
    return stats, issues


# ---------------------------------------------------------------------------
# Sanitize ロジック
# ---------------------------------------------------------------------------


def _sanitize_rows(
    rows: List[List[str]],
    expected_columns: int,
    delimiter: str,
) -> Tuple[List[List[str]], List[Issue], int]:
    """列数の揃っていない行や空行を修正して、構造を安定させる。"""
    sanitized: List[List[str]] = []
    issues: List[Issue] = []
    fixed_count = 0

    for idx, row in enumerate(rows, start=1):
        if len(row) == 0 or (len(row) == 1 and row[0] == ""):
            issues.append(
                Issue(
                    type="EMPTY_ROW_REMOVED",
                    row=idx,
                    column=None,
                    severity="info",
                    description="Empty row removed during sanitize.",
                    fixed=True,
                )
            )
            fixed_count += 1
            continue

        col_count = len(row)

        if col_count == expected_columns:
            sanitized.append(row)
            continue

        if col_count < expected_columns:
            pad_n = expected_columns - col_count
            new_row = row + ["" for _ in range(pad_n)]
            issues.append(
                Issue(
                    type="ROW_PADDED",
                    row=idx,
                    column=None,
                    severity="warning",
                    description=(
                        f"Row had {col_count} columns; padded with {pad_n} empty cell(s) "
                        f"to match expected {expected_columns}."
                    ),
                    fixed=True,
                )
            )
            fixed_count += 1
            sanitized.append(new_row)
            continue

        if expected_columns <= 1:
            merged = delimiter.join(row)
            new_row = [merged]
        else:
            head = row[: expected_columns - 1]
            tail = row[expected_columns - 1 :]
            merged_last = delimiter.join(tail)
            new_row = head + [merged_last]

        issues.append(
            Issue(
                type="ROW_TRUNCATED",
                row=idx,
                column=None,
                severity="warning",
                description=(
                    f"Row had {col_count} columns; merged surplus cells into the last "
                    f"column to match expected {expected_columns}."
                ),
                fixed=True,
            )
        )
        fixed_count += 1
        sanitized.append(new_row)

    return sanitized, issues, fixed_count


# ---------------------------------------------------------------------------
# プロファイル解決
# ---------------------------------------------------------------------------


def _resolve_effective_config(
    request: CsvEscapeRequest,
    detected_le: str,
    detected_delimiter: str,
    has_header_bool: Optional[bool],
) -> EffectiveConfig:
    """target_profile と検出結果から実際に用いる設定値 (EffectiveConfig) を決定する。"""

    if request.line_ending == "auto":
        if detected_le in ("crlf", "lf"):
            base_le = detected_le
        else:
            base_le = "lf"
    else:
        base_le = request.line_ending

    base_delimiter = request.delimiter or detected_delimiter
    base_max_rows = max(0, int(request.max_rows or 0))

    cfg = EffectiveConfig(
        profile=request.target_profile,
        delimiter=base_delimiter,
        quote_char=request.quote_char,
        escape_style=request.escape_style,
        line_ending=base_le,
        quote_policy=request.quote_policy,
        excel_injection_protection=request.excel_injection_protection,
        trim_whitespace=request.trim_whitespace,
        null_representation=request.null_representation,
        add_bom=request.add_bom,
        max_rows=base_max_rows,
        has_header=has_header_bool,
    )

    profile = request.target_profile

    if profile == "excel":
        cfg.line_ending = "crlf"
        cfg.add_bom = True
        cfg.quote_policy = "minimal"
        cfg.excel_injection_protection = "prefix_quote"
        cfg.trim_whitespace = "right"
        cfg.escape_style = "rfc4180"

    elif profile == "db_rfc4180":
        cfg.line_ending = "crlf"
        cfg.add_bom = False
        cfg.quote_policy = "all"
        cfg.excel_injection_protection = "none"
        cfg.trim_whitespace = "none"
        cfg.escape_style = "rfc4180"
        if cfg.null_representation is None:
            cfg.null_representation = "\\N"

    elif profile == "ai_safety":
        cfg.line_ending = "lf"
        cfg.add_bom = False
        cfg.quote_policy = "all"
        cfg.excel_injection_protection = "strip_formula"
        cfg.trim_whitespace = "both"
        cfg.escape_style = "rfc4180"

    return cfg


# ---------------------------------------------------------------------------
# Escape 本体
# ---------------------------------------------------------------------------


def _escape_rows_to_text(
    rows: List[List[str]],
    cfg: EffectiveConfig,
) -> str:
    """2 次元配列の rows を CSV テキストに再構成する。"""

    if cfg.line_ending == "crlf":
        lineterminator = "\r\n"
    else:
        lineterminator = "\n"

    if cfg.quote_policy == "all":
        quoting = csv.QUOTE_ALL
    elif cfg.quote_policy == "non_numeric":
        quoting = csv.QUOTE_NONNUMERIC
    else:
        quoting = csv.QUOTE_MINIMAL

    if cfg.escape_style in ("rfc4180", "double"):
        csv_doublequote = True
        csv_escapechar = None
    elif cfg.escape_style == "backslash":
        csv_doublequote = False
        csv_escapechar = "\\"
    else:
        csv_doublequote = True
        csv_escapechar = None

    output = io.StringIO()

    writer_kwargs = {
        "delimiter": cfg.delimiter,
        "quotechar": cfg.quote_char,
        "quoting": quoting,
        "lineterminator": lineterminator,
        "doublequote": csv_doublequote,
    }
    if csv_escapechar is not None:
        writer_kwargs["escapechar"] = csv_escapechar

    writer = csv.writer(output, **writer_kwargs)

    dangerous_prefixes = ("=", "+", "-", "@", "\t")

    for row in rows:
        processed_row: List[str] = []
        for cell in row:
            value = "" if cell is None else str(cell)

            if cfg.trim_whitespace in ("left", "both"):
                value = value.lstrip()
            if cfg.trim_whitespace in ("right", "both"):
                value = value.rstrip()

            if cfg.null_representation is not None and value == "":
                value = cfg.null_representation

            if cfg.excel_injection_protection != "none" and value:
                if value[0] in dangerous_prefixes:
                    if cfg.excel_injection_protection == "prefix_quote":
                        value = "'" + value
                    elif cfg.excel_injection_protection == "strip_formula":
                        while value and value[0] in dangerous_prefixes:
                            value = value[1:]

            processed_row.append(value)

        writer.writerow(processed_row)

    csv_text = output.getvalue()

    if cfg.add_bom and not csv_text.startswith("\ufeff"):
        csv_text = "\ufeff" + csv_text

    return csv_text


# ---------------------------------------------------------------------------
# response_level による間引き
# ---------------------------------------------------------------------------


def _minimize_response(
    level: ResponseLevel,
    csv_text: str,
    issues: List[Issue],
    stats: Stats,
    meta_full: Dict[str, Any],
) -> CsvEscapeResponse:
    """
    互換性のためトップ構造 {result, meta} は維持しつつ、
    response_level に応じて result/meta の中身を最小化する。
    """

    # 共通の最小 meta
    meta_simple: Dict[str, Any] = {
        "version": meta_full.get("version"),
        "profile": meta_full.get("profile"),
        "mode_used": meta_full.get("mode_used"),
        "response_level_used": level.value,
    }

    if level == ResponseLevel.simple:
        result = CsvEscapeResult(
            csv_text=csv_text,
            issues=[],
            stats=None,
        )
        return CsvEscapeResponse(result=result, meta=meta_simple)

    if level == ResponseLevel.standard:
        meta_standard: Dict[str, Any] = dict(meta_simple)
        # standard では「適用された設定」までは返す（挙動説明に必要）
        if "effective_config" in meta_full:
            meta_standard["effective_config"] = meta_full["effective_config"]
        # sanitize の場合だけ、ユーザーに有益なので sanitized フラグは残す
        if "sanitized" in meta_full:
            meta_standard["sanitized"] = meta_full["sanitized"]

        result = CsvEscapeResult(
            csv_text=csv_text,
            issues=issues,
            stats=stats,
        )
        return CsvEscapeResponse(result=result, meta=meta_standard)

    # debug: 現在のフル仕様を維持（meta_full をそのまま返す）
    result = CsvEscapeResult(
        csv_text=csv_text,
        issues=issues,
        stats=stats,
    )
    return CsvEscapeResponse(result=result, meta=meta_full)


# ---------------------------------------------------------------------------
# API エントリーポイント
# ---------------------------------------------------------------------------


def process_csv(request: CsvEscapeRequest) -> CsvEscapeResponse:
    """CSV Escape & Sanitize API のメイン処理（v0.2）"""

    # 1) Base64 -> UTF-8
    text_raw = _decode_base64_to_text(request.csv_b64)

    # 2) 改行コード正規化
    text_normalized, detected_le = _normalize_line_endings(text_raw)

    # 3) delimiter 推定
    rows_for_detect = _split_rows(text_normalized)
    first_non_empty = next((r for r in rows_for_detect if r.strip() != ""), "")
    detected_delimiter = _detect_delimiter(first_non_empty or text_normalized)

    # 4) has_header (v0.2 でも auto 判定は未実装で None 扱い)
    if request.has_header == "auto":
        has_header_bool: bool | None = None
    else:
        has_header_bool = bool(request.has_header)

    # 5) プロファイル適用後の設定を決定
    cfg = _resolve_effective_config(
        request=request,
        detected_le=detected_le,
        detected_delimiter=detected_delimiter,
        has_header_bool=has_header_bool,
    )

    # 6) csv.reader で 2 次元配列へ
    all_rows = _rows_from_text(text_normalized, cfg.delimiter, cfg.quote_char)

    if cfg.max_rows > 0:
        rows = all_rows[: cfg.max_rows]
    else:
        rows = all_rows

    # 7) 構造解析（Sanitize 前の状態）
    stats_before, issues_before = _analyze_structure(rows, cfg.delimiter, cfg.has_header)

    # 8) mode に応じて処理を分岐（ここでは “フル情報” を作る）
    issues_out: List[Issue]
    stats_out: Stats
    csv_text_out: str
    meta_full: Dict[str, Any]

    if request.mode == "analyze":
        if cfg.line_ending == "crlf":
            csv_text_out = text_normalized.replace("\n", "\r\n")
        else:
            csv_text_out = text_normalized

        stats_out = stats_before
        issues_out = issues_before

        meta_full = {
            "version": "0.2.0",
            "profile": cfg.profile,
            "mode_used": request.mode,
            "effective_config": asdict(cfg),
            "structure_stats_before": stats_before.dict(),
        }

    elif request.mode == "sanitize":
        expected_cols = stats_before.columns_mode or stats_before.columns_max or 0

        sanitized_rows, sanitize_issues, fixed_count = _sanitize_rows(
            rows=rows,
            expected_columns=expected_cols,
            delimiter=cfg.delimiter,
        )

        stats_out = Stats(
            rows=len(sanitized_rows),
            columns_min=expected_cols,
            columns_max=expected_cols,
            columns_mode=expected_cols,
            fixed_issues_count=fixed_count,
            unfixed_issues_count=0,
            delimiter_detected=stats_before.delimiter_detected,
            has_header=stats_before.has_header,
        )

        issues_out = issues_before + sanitize_issues
        csv_text_out = _escape_rows_to_text(rows=sanitized_rows, cfg=cfg)

        meta_full = {
            "version": "0.2.0",
            "profile": cfg.profile,
            "mode_used": request.mode,
            "effective_config": asdict(cfg),
            "structure_stats_before": stats_before.dict(),
            "sanitized": True,
        }

    else:  # "escape"
        csv_text_out = _escape_rows_to_text(rows=rows, cfg=cfg)
        stats_out = stats_before
        issues_out = issues_before

        meta_full = {
            "version": "0.2.0",
            "profile": cfg.profile,
            "mode_used": request.mode,
            "effective_config": asdict(cfg),
        }

    # 9) response_level に応じて最終レスポンスを生成
    return _minimize_response(
        level=request.response_level,
        csv_text=csv_text_out,
        issues=issues_out,
        stats=stats_out,
        meta_full=meta_full,
    )

