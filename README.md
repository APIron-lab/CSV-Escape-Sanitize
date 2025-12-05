# CSV Escape & Sanitize API (v0.2)

Robust CSV normalization API providing **Escape**, **Sanitize**, and **Analyze** modes for enterprise-grade CSV workflows.  
Designed for **ETL pipelines, LLM preprocessing, database ingestion, and spreadsheet interoperability**.

[![CI](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml/badge.svg)](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize/graph/badge.svg?token=WCRL7ZQbIE)](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize)

---

## Overview

CSV Escape & Sanitize API accepts Base64-encoded CSV text and provides:

### **Escape Mode**
Safely rewrites CSV using a chosen profile (Excel / RFC4180 / AI-safe), controlling:

- delimiter  
- quote behavior  
- line endings  
- Excel-injection protection  
- BOM addition  
- whitespace trimming  
- null representation  

### **Sanitize Mode**
Repairs CSV structural issues:

- uneven columns  
- missing cells  
- surplus columns  
- inconsistent row lengths  
- empty rows  

Sanitize produces a **structurally correct table** before applying Escape rules.

### **Analyze Mode**
Performs structural inspection without modifying content.  
Useful for ETL validation and CSV health-check workflows.

---

## Profiles

Three built-in profiles optimize CSV export for different environments.

### 1. **excel**
Optimized for Microsoft Excel / Office tools.

| Setting | Value |
|--------|-------|
| delimiter | `,` |
| quote policy | minimal |
| line ending | CRLF |
| BOM | added |
| excel injection protection | prefix with `'` |

### 2. **db_rfc4180**
Strict RFC 4180 for databases and ETL ingestion.

| Setting | Value |
|--------|-------|
| quote policy | all |
| null representation | `\N` |
| BOM | none |

### 3. **ai_safety**
For safe ingestion into LLMs / ChatGPT / Claude.

| Setting | Value |
|--------|-------|
| line ending | LF |
| quote policy | all |
| excel injection protection | strip formula characters |
| whitespace trimming | both |

---

## Endpoint

### `POST /csv/v0/escape`

This single endpoint handles all three modes:

```json
{
  "mode": "escape | sanitize | analyze",
  "csv_b64": "<Base64 string>",
  "target_profile": "excel | db_rfc4180 | ai_safety"
}
```

---

## Response Structure (All Modes)

Every response returns the same top-level structure:

```json
{
  "result": { ... },
  "meta": {
    "version": "0.2.0",
    "profile": "excel",
    "mode_used": "escape",
    "effective_config": { ... }
  }
}
```

### Mapped across modes:

| Mode | `result.csv_text` | `result.issues` | `meta.structure_stats_before` | `meta.sanitized` |
|------|------------------|------------------|-------------------------------|------------------|
| escape | Yes (rewritten CSV) | Escape-related issues | Yes | false |
| sanitize | Yes (repaired CSV) | structure fixes (ROW_PADDED, TRUNCATED, etc.) | Yes | true |
| analyze | Yes (original CSV except LF normalization) | detection only (no fixing) | Yes | false |

---

## Escape Mode – Response Details

Escape applies formatting rules without altering row count or column count.

### Example (Excel profile)

```json
{
  "result": {
    "csv_text": "\"A\",\"B\",\"C\"\r\n\"1\",\"2\",\"3\"\r\n",
    "issues": []
  },
  "meta": {
    "profile": "excel",
    "mode_used": "escape"
  }
}
```

You can customize:

- delimiter  
- quoting behavior  
- whitespace trimming  
- BOM  
- Excel-injection handling  
- null text  
- line ending normalization  

---

## Sanitize Mode – Response Details

Sanitize repairs structural corruption **before** Escape is applied.

Fixes include:

| Issue | Meaning |
|-------|---------|
| `EMPTY_ROW_REMOVED` | blank row deleted |
| `ROW_PADDED` | missing columns filled with empty cells |
| `ROW_TRUNCATED` | surplus columns merged into last cell |
| `COLUMN_COUNT_MISMATCH` | row length differs from mode column count |

### Example

Input (Base64):
```
col1,col2,col3
1,2,3
4,5
6,7,8,9
,
```

Output:

```json
{
  "result": {
    "csv_text": "\"col1\",\"col2\",\"col3\"\n\"1\",\"2\",\"3\"\n\"4\",\"5\",\"\"\n\"6\",\"7\",\"8,9\"\n\"\",\"\",\"\"\n",
    "issues": [
      { "type": "COLUMN_COUNT_MISMATCH", "row": 3, "column": null, "severity": "warning", "description": "Row has 2 columns (expected ~3). No automatic fix in this step.", "fixed": false },
      { "type": "COLUMN_COUNT_MISMATCH", "row": 4, "column": null, "severity": "warning", "description": "Row has 4 columns (expected ~3). No automatic fix in this step.", "fixed": false },
      { "type": "COLUMN_COUNT_MISMATCH", "row": 5, "column": null, "severity": "warning", "description": "Row has 2 columns (expected ~3). No automatic fix in this step.", "fixed": false },
      { "type": "ROW_PADDED", "row": 3, "column": null, "severity": "warning", "description": "Row had 2 columns; padded with 1 empty cell(s) to match expected 3.", "fixed": true },
      { "type": "ROW_TRUNCATED", "row": 4, "column": null, "severity": "warning", "description": "Row had 4 columns; merged surplus cells into the last column to match expected 3.", "fixed": true },
      { "type": "ROW_PADDED", "row": 5, "column": null, "severity": "warning", "description": "Row had 2 columns; padded with 1 empty cell(s) to match expected 3.", "fixed": true }
    ],
    "stats": {
      "rows": 5,
      "columns_min": 3,
      "columns_max": 3,
      "columns_mode": 3,
      "fixed_issues_count": 3,
      "unfixed_issues_count": 0,
      "delimiter_detected": ",",
      "has_header": null
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "ai_safety",
    "mode_used": "sanitize",
    "effective_config": {
      "profile": "ai_safety",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "lf",
      "quote_policy": "all",
      "excel_injection_protection": "strip_formula",
      "trim_whitespace": "both",
      "null_representation": null,
      "add_bom": false,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 3,
      "delimiter_detected": ",",
      "has_header": null
    },
    "sanitized": true
  }
}
```

---

## Analyze Mode – Response Details

Analyze does **not fix** anything.  
Only reports structural problems.

### Example:

```json
{
  "result": {
    "csv_text": "same-as-input-but-LF-normalized",
    "issues": [
      { "type": "COLUMN_COUNT_MISMATCH", "row": 2 },
      { "type": "COLUMN_COUNT_MISMATCH", "row": 4 }
    ],
    "stats": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 2,
      "delimiter_detected": ",",
      "has_header": null
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "ai_safety",
    "mode_used": "analyze",
    "effective_config": {
      "profile": "ai_safety",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "lf",
      "quote_policy": "all",
      "excel_injection_protection": "strip_formula",
      "trim_whitespace": "both",
      "null_representation": null,
      "add_bom": false,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 2,
      "delimiter_detected": ",",
      "has_header": null
    }
  }
}
```

Useful when:

- Building ETL validation steps  
- Detecting malformed CSV before pipeline processing  
- Creating automated CSV health dashboards  

---

## Base64 Input Requirements

The API always accepts **Base64 text**, not raw CSV.

This guarantees:

- encoding integrity  
- no line-ending corruption  
- no JSON escaping issues  
- safe binary transport  

Example:

```bash
cat sample.csv | base64 -w0
```

Input JSON:

```json
{
  "mode": "sanitize",
  "csv_b64": "Y29sMSxjb2wyLGNvbDMKMSwyLDMKNCw1CjYsNyw4LDkKLAo=",
  "target_profile": "ai_safety"
}
```

---

## Python Example

```python
import base64, requests

with open("input.csv", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

payload = {
    "mode": "sanitize",
    "csv_b64": b64,
    "target_profile": "excel"
}

res = requests.post("http://localhost:8000/csv/v0/escape", json=payload)
print(res.json())
```

---

# 🇯🇵 日本語版 README

以下は英語版と完全一致した構成です。

---

# CSV Escape & Sanitize API (v0.2)

CSV の **Escape（整形）・Sanitize（修復）・Analyze（検査）** を行う高信頼 API。  
ETL、LLM 前処理、Excel 取込、データベース投入など、あらゆる現場で利用できます。

[![CI](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml/badge.svg)](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize/graph/badge.svg?token=WCRL7ZQbIE)](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize)

---

## 概要

本 API は、Base64 で入力された CSV を解析し、以下の３つのモードを提供します。

- Escape モード（形式整形）  
- Sanitize モード（構造修復）  
- Analyze モード（構造検査のみ）  

---

## Escape モード

選択したプロファイル（Excel / RFC4180 / AI-safe）に基づき、  
**内容を変えずに安全な CSV 形式へ整形**します。

制御できる項目：

- 区切り文字（delimiter）  
- クォートの有無・方針（quote policy）  
- 改行コード（CRLF / LF）  
- Excel インジェクション対策の有無・方式  
- BOM 付与の有無  
- 前後の空白トリム（trim_whitespace）  
- NULL の文字列表現（例: `\N`）  

Escape では、**行数や列数は変えず**、あくまで表現・フォーマットだけを揃えます。

---

## Sanitize モード

壊れた CSV の構造を修復するモードです。  
Sanitize では、まず CSV を行・列単位の 2 次元配列として解析し、**列数の揺れや空行を補正**します。

修復できる主な問題：

| 種類 | 内容 |
|------|------|
| `EMPTY_ROW_REMOVED` | 完全な空行を削除 |
| `ROW_PADDED` | 列数が少ない行の末尾に空セルを追加 |
| `ROW_TRUNCATED` | 列数が多い行の余剰セルを 1 セルに結合 |
| `COLUMN_COUNT_MISMATCH` | 想定列数と異なる行の検出（修復前時点） |

Sanitize の流れ：

1. 元の CSV を行に分解し、行ごとの列数をカウント  
2. 最頻値（mode）の列数を「正しい列数」とみなす  
3. 列数が少ない行はパディング（空セル追加）、多い行は結合  
4. 空行は削除  
5. その後 Escape のプロファイル設定を適用し、出力 CSV を生成  

Sanitize 後の行・列数を元に、`stats` も更新されます。

---

## Analyze モード

Analyze モードは **CSV を一切修正せず**、構造のみを検査してレポートします。  
ETL 事前チェックや「この CSV は安全に読み込めるか？」の判定に適しています。

特徴：

- `csv_text` は元の内容を維持（改行コードのみ LF 正規化される場合あり）  
- 列数不一致や空行などが `issues` に記録される  
- 自動修正は行わない（`fixed: false` のまま）  

利用シーン：

- 取り込み前 CSV の自動品質チェック  
- バッチ前後の CSV 構造モニタリング  
- ダッシュボード用のヘルスレポート生成  

---

## プロファイル

3 種類のプロファイルを内蔵しています。

### 1. excel プロファイル

Excel / Office 系ツールでの利用を前提にしたプロファイルです。

| 設定 | 値 |
|------|-----|
| delimiter | `,` |
| quote policy | minimal（必要な時だけクォート） |
| line ending | CRLF |
| add_bom | true（BOM 付与） |
| excel_injection_protection | prefix_quote（`'=...` 形式） |

### 2. db_rfc4180 プロファイル

データベースや ETL 向けの RFC 4180 準拠プロファイルです。

| 設定 | 値 |
|------|-----|
| delimiter | `,` |
| quote policy | all（すべてクォート） |
| null_representation | `\N` |
| add_bom | false |
| line ending | CRLF |

### 3. ai_safety プロファイル

LLM（ChatGPT / Claude など）への投入を想定したプロファイルです。

| 設定 | 値 |
|------|-----|
| line ending | LF |
| quote policy | all |
| excel_injection_protection | strip_formula（先頭の `= + - @` などを除去） |
| trim_whitespace | both（前後の空白を除去） |

---

## エンドポイント

### `POST /csv/v0/escape`

### リクエスト共通形式

```json
{
  "mode": "escape | sanitize | analyze",
  "csv_b64": "<Base64 string>",
  "target_profile": "excel | db_rfc4180 | ai_safety"
}
```

- `mode`  
  - `"escape"` : 形式整形のみ  
  - `"sanitize"` : 構造修復 + 形式整形  
  - `"analyze"` : 構造検査のみ（修正なし）  

- `csv_b64`  
  - CSV ファイルの中身を Base64 文字列にしたもの  
  - 文字コードは UTF-8 を推奨  

- `target_profile`  
  - 出力の形式を制御するプロファイル名  

---

## レスポンス構造（共通）

全モード共通で、レスポンスは以下の 2 階層構造です：

```json
{
  "result": {
    "csv_text": "string",
    "issues": [ ... ],
    "stats": {
      "rows": 0,
      "columns_min": 0,
      "columns_max": 0,
      "columns_mode": 0,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 0,
      "delimiter_detected": ",",
      "has_header": null
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "excel",
    "mode_used": "escape | sanitize | analyze",
    "effective_config": {
      "profile": "excel | db_rfc4180 | ai_safety",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "crlf | lf",
      "quote_policy": "minimal | all",
      "excel_injection_protection": "prefix_quote | strip_formula | none",
      "trim_whitespace": "left | right | both | none",
      "null_representation": null,
      "add_bom": true,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 0,
      "columns_min": 0,
      "columns_max": 0,
      "columns_mode": 0,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 0,
      "delimiter_detected": ",",
      "has_header": null
    },
    "sanitized": false
  }
}
```

### モードごとの違いまとめ

| Mode | `result.csv_text` | `result.issues` | `meta.structure_stats_before` | `meta.sanitized` |
|------|------------------|------------------|-------------------------------|------------------|
| escape | 整形済み CSV | Escape による警告・情報 | あり | false |
| sanitize | 修復 + 整形された CSV | 構造修復に関する詳細 | あり | true |
| analyze | 入力と同等（改行のみ LF 正規化の可能性） | 検知のみ（fixed: false） | あり | false |

---

## Escape モードのレスポンス例

```json
{
  "result": {
    "csv_text": ""A","B","C"\r\n"1","2","3"\r\n",
    "issues": []
  },
  "meta": {
    "version": "0.2.0",
    "profile": "excel",
    "mode_used": "escape",
    "effective_config": {
      "profile": "excel",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "crlf",
      "quote_policy": "minimal",
      "excel_injection_protection": "prefix_quote",
      "trim_whitespace": "right",
      "null_representation": null,
      "add_bom": true,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 2,
      "columns_min": 3,
      "columns_max": 3,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 0,
      "delimiter_detected": ",",
      "has_header": null
    },
    "sanitized": false
  }
}
```

---

## Sanitize モードのレスポンス例

入力 CSV（概念的な例）：

```csv
col1,col2,col3
1,2,3
4,5
6,7,8,9
,
```

この CSV は、2 行目・4 行目で列数が揺れており、**そのままでは多くの CSV パーサでエラー**になります。  
Sanitize モードでは、以下のように修復します：

- 列数不足の行 → 空セルでパディング  
- 列数過多の行 → 余りを最後の列に結合  
- 空行 → 空セル 3 列に正規化（または要件次第で削除も可能な設計）  

出力例（実際に API から返却された JSON）：

```json
{
  "result": {
    "csv_text": ""col1","col2","col3"\n"1","2","3"\n"4","5",""\n"6","7","8,9"\n"","",""\n",
    "issues": [
      {
        "type": "COLUMN_COUNT_MISMATCH",
        "row": 3,
        "column": null,
        "severity": "warning",
        "description": "Row has 2 columns (expected ~3). No automatic fix in this step.",
        "fixed": false
      },
      {
        "type": "COLUMN_COUNT_MISMATCH",
        "row": 4,
        "column": null,
        "severity": "warning",
        "description": "Row has 4 columns (expected ~3). No automatic fix in this step.",
        "fixed": false
      },
      {
        "type": "COLUMN_COUNT_MISMATCH",
        "row": 5,
        "column": null,
        "severity": "warning",
        "description": "Row has 2 columns (expected ~3). No automatic fix in this step.",
        "fixed": false
      },
      {
        "type": "ROW_PADDED",
        "row": 3,
        "column": null,
        "severity": "warning",
        "description": "Row had 2 columns; padded with 1 empty cell(s) to match expected 3.",
        "fixed": true
      },
      {
        "type": "ROW_TRUNCATED",
        "row": 4,
        "column": null,
        "severity": "warning",
        "description": "Row had 4 columns; merged surplus cells into the last column to match expected 3.",
        "fixed": true
      },
      {
        "type": "ROW_PADDED",
        "row": 5,
        "column": null,
        "severity": "warning",
        "description": "Row had 2 columns; padded with 1 empty cell(s) to match expected 3.",
        "fixed": true
      }
    ],
    "stats": {
      "rows": 5,
      "columns_min": 3,
      "columns_max": 3,
      "columns_mode": 3,
      "fixed_issues_count": 3,
      "unfixed_issues_count": 0,
      "delimiter_detected": ",",
      "has_header": null
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "ai_safety",
    "mode_used": "sanitize",
    "effective_config": {
      "profile": "ai_safety",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "lf",
      "quote_policy": "all",
      "excel_injection_protection": "strip_formula",
      "trim_whitespace": "both",
      "null_representation": null,
      "add_bom": false,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 3,
      "delimiter_detected": ",",
      "has_header": null
    },
    "sanitized": true
  }
}
```

---

## Analyze モードのレスポンス例

Analyze モードでは、構造の問題を検出するだけで、修復は行いません。

例：

```json
{
  "result": {
    "csv_text": "same-as-input-but-LF-normalized",
    "issues": [
      { "type": "COLUMN_COUNT_MISMATCH", "row": 2 },
      { "type": "COLUMN_COUNT_MISMATCH", "row": 4 }
    ],
    "stats": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 2,
      "delimiter_detected": ",",
      "has_header": null
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "ai_safety",
    "mode_used": "analyze",
    "effective_config": {
      "profile": "ai_safety",
      "delimiter": ",",
      "quote_char": """,
      "escape_style": "rfc4180",
      "line_ending": "lf",
      "quote_policy": "all",
      "excel_injection_protection": "strip_formula",
      "trim_whitespace": "both",
      "null_representation": null,
      "add_bom": false,
      "max_rows": 0,
      "has_header": null
    },
    "structure_stats_before": {
      "rows": 5,
      "columns_min": 2,
      "columns_max": 4,
      "columns_mode": 3,
      "fixed_issues_count": 0,
      "unfixed_issues_count": 2,
      "delimiter_detected": ",",
      "has_header": null
    }
  }
}
```

---

## Base64 入力仕様

本 API は **生の CSV テキストではなく、Base64 文字列** を受け取ります。

理由：

- エディタやブラウザ経由のコピー＆ペーストによる改行・文字コードの崩れを防ぐ  
- JSON 経由で送信してもエスケープの問題が起きない  
- 将来的にバイナリ CSV / 圧縮などへ拡張しやすい  

### 例：Linux / WSL での Base64 生成

```bash
cat input.csv | base64 -w0 > b64.txt
```

その後、`b64.txt` の中身を `csv_b64` に貼り付けます。

---

## Python 使用例

```python
import base64
import requests

# CSV ファイルを読み込み、Base64 化
with open("input.csv", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("ascii")

payload = {
    "mode": "sanitize",
    "csv_b64": b64,
    "target_profile": "excel"
}

res = requests.post("http://localhost:8000/csv/v0/escape", json=payload)
data = res.json()

print("Sanitized CSV:")
print(data["result"]["csv_text"])
print("Issues:", data["result"]["issues"])
```

---

Maintainer: APIron-lab  
GitHub: https://github.com/APIron-lab/CSV-Escape-Sanitize

