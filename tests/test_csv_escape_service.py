import base64

from core.csv_escape.models import CsvEscapeRequest
from core.csv_escape.service import process_csv


def _b64(s: str) -> str:
    """テスト用 Base64 ヘルパー"""
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def test_escape_excel_keeps_well_formed_csv():
    """
    mode=escape / profile=excel で、
    きれいな CSV を壊さないこと & Excel 向けの改行/BOM が付与されることを確認する。
    """
    raw_csv = "a,b\n1,2\n"
    req = CsvEscapeRequest(
        mode="escape",
        csv_b64=_b64(raw_csv),
        target_profile="excel",
    )

    resp = process_csv(req)

    # BOM が先頭に付いている
    assert resp.result.csv_text.startswith("\ufeff")

    # 改行コードが CRLF になっている
    assert "\r\n" in resp.result.csv_text
    assert "\n" not in resp.result.csv_text.replace("\r\n", "")

    # 内容が壊れていない（ヘッダ・データが維持されている）
    assert "a,b" in resp.result.csv_text
    assert "1,2" in resp.result.csv_text

    # stats が期待どおり
    assert resp.result.stats.rows == 2
    assert resp.result.stats.columns_min == 2
    assert resp.result.stats.columns_max == 2
    assert resp.result.stats.columns_mode == 2


def test_sanitize_fixes_misaligned_rows():
    """
    mode=sanitize / profile=ai_safety で、
    列数がバラバラな CSV が期待列数に揃えられることを確認する。

    元 CSV:
        col1,col2,col3
        1,2,3
        4,5
        6,7,8,9
        ,
    """
    raw_csv = (
        "col1,col2,col3\n"
        "1,2,3\n"
        "4,5\n"
        "6,7,8,9\n"
        ",\n"
    )

    req = CsvEscapeRequest(
        mode="sanitize",
        csv_b64=_b64(raw_csv),
        target_profile="ai_safety",
    )

    resp = process_csv(req)

    # サニタイズ後の CSV テキスト（LF・全クォート）
    expected_csv = (
        '"col1","col2","col3"\n'
        '"1","2","3"\n'
        '"4","5",""\n'
        '"6","7","8,9"\n'
        '"","",""\n'
    )
    assert resp.result.csv_text == expected_csv

    # 構造が揃っている
    stats = resp.result.stats
    assert stats.rows == 5
    assert stats.columns_min == 3
    assert stats.columns_max == 3
    assert stats.columns_mode == 3
    assert stats.fixed_issues_count == 3
    assert stats.unfixed_issues_count == 0

    # structure_stats_before では列数がバラバラだったことが分かる
    before = resp.meta["structure_stats_before"]
    assert before["columns_min"] == 2
    assert before["columns_max"] == 4
    assert before["columns_mode"] == 3

    # issues に MISMATCH（診断）と PADDED/TRUNCATED（修正）が両方入っている
    issue_types = [i["type"] if isinstance(i, dict) else i.type for i in resp.result.issues]
    assert "COLUMN_COUNT_MISMATCH" in issue_types
    assert "ROW_PADDED" in issue_types
    assert "ROW_TRUNCATED" in issue_types


def test_analyze_mode_does_not_change_content_except_line_endings():
    """
    mode=analyze では、内容を変えずに構造だけ解析することを確認。

    - line_ending=lf を指定した場合、改行は LF に統一される
    - 内容（セル値）は変化しない
    """
    raw_csv = "a,b\r\n1,2\r\n"
    req = CsvEscapeRequest(
        mode="analyze",
        csv_b64=_b64(raw_csv),
        target_profile="custom",
        line_ending="lf",  # analyze モードで lf を指定
    )

    resp = process_csv(req)

    # 改行が LF になっている
    assert resp.result.csv_text == "a,b\n1,2\n"

    # stats は構造を正しく反映している
    stats = resp.result.stats
    assert stats.rows == 2
    assert stats.columns_min == 2
    assert stats.columns_max == 2
    assert stats.columns_mode == 2

    # meta の mode_used が analyze であること
    assert resp.meta["mode_used"] == "analyze"

