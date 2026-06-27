"""
prepare_tenant_datasets.py

Reshapes the raw MKQA multilingual dataset (mkqa.jsonl) into per-tenant,
per-language Q&A files for a multilingual multi-tenant RAG system.

Each tenant = one company speaking one language:
    - Acme Translations   -> Spanish    (es)
    - Globex Localization  -> Portuguese (pt)
    - Initech Docs         -> English    (en)

Output: CSV (for ingestion) + JSONL + Parquet (industry-standard data formats).
Columns: name, category, question, answer

Usage:
    pip install pyarrow
    python prepare_tenant_datasets.py path/to/mkqa.jsonl
"""

import json
import csv
import os
import sys
import pyarrow as pa
import pyarrow.parquet as pq


# ---- Config: filename base -> (tenant display name, MKQA language code) ----
TENANTS = {
    "tenant_acme_es":    ("Acme Translations",   "es"),
    "tenant_globex_pt":  ("Globex Localization", "pt"),
    "tenant_initech_en": ("Initech Docs",        "en"),
}

ROWS_PER_TENANT = 500   # raise later once embedding is fast enough
OUTPUT_DIR = "tenant_datasets"


def category_for(answer_type: str) -> str:
    """Map MKQA's answer 'type' to a clean, human-readable category."""
    return {
        "entity":           "Entity",
        "long_answer":      "General",
        "number":           "Numeric",
        "number_with_unit": "Numeric",
        "date":             "Date",
        "short_phrase":     "General",
        "binary":           "Yes/No",
        "unanswerable":     "Unknown",
    }.get(answer_type, "General")


def load_rows_per_language(mkqa_path: str, languages: set) -> dict:
    """Read MKQA once; bucket valid (question, answer) rows by language."""
    buckets = {lang: [] for lang in languages}

    with open(mkqa_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            for lang in languages:
                question = (rec["queries"].get(lang) or "").strip()
                answers = rec["answers"].get(lang, [])
                if not question or not answers:
                    continue
                answer = (answers[0].get("text") or "").strip()
                if not answer:                       # skip empty/unanswerable
                    continue
                buckets[lang].append({
                    "category": category_for(answers[0].get("type", "")),
                    "question": question,
                    "answer": answer,
                })
    return buckets


def write_csv(path: str, rows: list):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "category", "question", "answer"])
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: str, rows: list):
    """JSONL = one JSON object per line. ML / HuggingFace standard."""
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_parquet(path: str, rows: list):
    """Parquet = columnar, compressed, typed. Analytics / data-lake standard."""
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python prepare_tenant_datasets.py path/to/mkqa.jsonl")
        sys.exit(1)

    mkqa_path = sys.argv[1]
    if not os.path.exists(mkqa_path):
        print(f"File not found: {mkqa_path}")
        sys.exit(1)

    # Make output subfolders
    for fmt in ("csv", "jsonl", "parquet"):
        os.makedirs(os.path.join(OUTPUT_DIR, fmt), exist_ok=True)

    languages = {lang for _, lang in TENANTS.values()}
    buckets = load_rows_per_language(mkqa_path, languages)

    for base, (tenant_name, lang) in TENANTS.items():
        rows = buckets[lang][:ROWS_PER_TENANT]
        for row in rows:
            row["name"] = tenant_name           # tag every row with its tenant

        # Reorder keys so 'name' comes first
        rows = [{"name": r["name"], "category": r["category"],
                 "question": r["question"], "answer": r["answer"]} for r in rows]

        write_csv(os.path.join(OUTPUT_DIR, "csv", f"{base}.csv"), rows)
        write_jsonl(os.path.join(OUTPUT_DIR, "jsonl", f"{base}.jsonl"), rows)
        write_parquet(os.path.join(OUTPUT_DIR, "parquet", f"{base}.parquet"), rows)

        print(f"{base}: {len(rows)} rows  (tenant='{tenant_name}', lang={lang})")

    print(f"\nDone. Files written to ./{OUTPUT_DIR}/{{csv,jsonl,parquet}}/")


if __name__ == "__main__":
    main()