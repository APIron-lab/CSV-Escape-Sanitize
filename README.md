# CSV Escape & Sanitize API (v0.2)

High‑integrity CSV escaping, sanitization, and analysis API designed for real‑world data workflows, spreadsheet pipelines, ETL systems, and LLM preprocessing.

[![CI](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml/badge.svg)](https://github.com/APIron-lab/CSV-Escape-Sanitize/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize/graph/badge.svg?token=WCRL7ZQbIE)](https://codecov.io/gh/APIron-lab/CSV-Escape-Sanitize)

---

## 🌐 Overview

CSV Escape & Sanitize API provides **robust CSV processing** with three unified capabilities:

### 1. Escape  
Output stable, compliant CSV according to one of several **profiles** (Excel, RFC4180 for DB, AI‑safety).  
Automatic quoting, injection protection, BOM control, and line ending normalization.

### 2. Sanitize  
Repair malformed CSV:

- Fix mismatched column counts  
- Remove empty rows  
- Pad short rows  
- Collapse extra columns into the last field  
- Output a fully valid CSV that downstream systems can ingest safely  

### 3. Analyze  
Parse CSV and detect structural issues **without modifying** the content.

All inputs are Base64‑encoded CSV text to prevent encoding damage.

---

## 🔑 Key Capabilities

- Base64 input (protects from copy/paste corruption)  
- RFC4180 compliant escaping  
- Excel injection protection (`=`, `+`, `-`, `@` prefixes)  
- Three output profiles optimized for Excel, Databases, and AI models  
- Automatic delimiter detection  
- BOM insertion/removal  
- Detailed issue reporting (`ROW_PADDED`, `ROW_TRUNCATED`, `EMPTY_ROW_REMOVED`, …)  
- `result + meta` response following APIron Unified Specification  

---

## 📡 RapidAPI Availability

Coming soon to RapidAPI with:

- One‑click endpoint testing  
- Usage metering and subscription plans  
- Auto‑generated code samples  
- API‑key authentication  

---

## 🚀 Endpoint

### `POST /csv/v0/escape`

Although the endpoint name is `escape`, it supports:  
`mode = "escape" | "sanitize" | "analyze"`.

---

## 📦 Profiles

| Profile | Target Use | Quote Policy | Excel Injection | Line Ending | Notes |
|--------|-------------|--------------|------------------|-------------|-------|
| **excel** | Spreadsheet applications | minimal | prefix_quote | CRLF | Best for Excel/Sheets |
| **db_rfc4180** | ETL / Database import | all | none | CRLF | Strict RFC4180 compliance |
| **ai_safety** | LLM ingestion | all | strip_formula | LF | Prevents formula attacks |

---

## 🛠 Modes Overview

### Escape Mode
Produces clean, well‑formed CSV with quoting, delimiter handling, formula‑injection prevention, and BOM control.

### Analyze Mode
Detects structure without modifying:

- Column counts per row  
- Delimiter  
- BOM presence  
- Header likelihood  
- Structural irregularities  

### Sanitize Mode
Repairs CSV into a consistent columnar structure.

#### Example

**Input**
```
col1,col2,col3
1,2,3
4,5
6,7,8,9
,
```

**Output**
```
"col1","col2","col3"
"1","2","3"
"4","5",""
"6","7","8,9"
"","",""
```

---

## 📤 Response Structure

```json
{
  "result": {
    "csv_text": "string",
    "issues": [],
    "stats": {
      "rows": 0,
      "columns_min": 0,
      "columns_max": 0,
      "columns_mode": 0
    }
  },
  "meta": {
    "version": "0.2.0",
    "profile": "excel",
    "mode_used": "sanitize",
    "effective_config": {},
    "structure_stats_before": {},
    "sanitized": true
  }
}
```

---

## 🧪 Python Example

```python
import base64, requests

text = "a,b,c
1,2
3,4,5,6
"
b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")

payload = {
    "mode": "sanitize",
    "csv_b64": b64,
    "target_profile": "ai_safety"
}

res = requests.post("http://localhost:8000/csv/v0/escape", json=payload)
print(res.json())
```

---

# 🇯🇵 日本語版 README

## 概要

CSV Escape & Sanitize API は、**現実の CSV が抱える問題**  
（列ズレ・空行・Excel での破損・AI への入力不整合）を安全に修復し、  
統一仕様の CSV として出力する API です。

### 特徴

- Base64 入力でテキスト破損を防止  
- RFC4180 準拠のエスケープ  
- Excel で壊れない CSV 出力  
- AI モデル向け安全フォーマット  
- 列数不整合を自動修復（Sanitize）  
- 空行除去・列パディング・複数列の結合など  

---

## 利用シーン（Use Cases）

### 1. LLM 前処理（AI Input Hygiene）
モデル入力前の CSV 整形として最適。

### 2. Excel 出力（壊れない CSV）
Excel Injection 対策済み。

### 3. データベースインポート
RFC4180 モードで ETL パイプラインが安定。

### 4. ノーコードツール（Airtable / Notion 等）への入力
列ズレを自動修復し、失敗を防ぐ。

### 5. 契約書・台帳・ログなど、現場の CSV 実データ
フォーマットが揃っていなくても安全に修復可能。

---

Maintainer: APIron Lab  
GitHub: https://github.com/APIron-lab/CSV-Escape-Sanitize
