# 📂 Scripts for Data Conversion

Utility scripts that turn the raw **MKQA multilingual dataset** into clean,
per-tenant Q&A files for the multilingual multi-tenant RAG engine.

This folder is a **one-time data-prep step**. It is not part of the running
application — it just produces the input files the RAG pipeline ingests.

---

## What it does

The raw MKQA dataset (`mkqa.jsonl`) is a single file containing 10,000 questions,
each translated into 26 languages with nested answer objects. That format can't be
ingested directly. These scripts reshape it into flat, per-tenant files.

```
data/mkqa.jsonl  ──►  script.py  ──►  tenant_datasets/
   (raw, nested,                         ├── csv/      → ingested by the app
    26 languages)                        ├── jsonl/    → ML-standard format
                                         └── parquet/  → analytics-standard format
```

Each output row has four columns: `name, category, question, answer`.

---

## Tenant design

Each tenant represents one fictional company that speaks one language. This split
is what later proves **multi-tenant data isolation** — Tenant A must never see
Tenant B's data.

| Output file              | Tenant (company)      | Language        |
|--------------------------|-----------------------|-----------------|
| `tenant_acme_es.*`       | Acme Translations     | Spanish (`es`)  |
| `tenant_globex_pt.*`     | Globex Localization   | Portuguese (`pt`) |
| `tenant_initech_en.*`    | Initech Docs          | English (`en`)  |

> Acme / Globex / Initech are classic placeholder company names used in tech
> examples. Rename them freely.

---

## Output formats (and why three of them)

The same data is written in three formats to match different real-world uses:

| Format   | Use case                                   | Notes                              |
|----------|--------------------------------------------|------------------------------------|
| **CSV**  | Ingested by the RAG pipeline               | Human-readable, spreadsheet-friendly |
| **JSONL**| ML / HuggingFace pipelines                 | One JSON object per line, streamable |
| **Parquet** | Analytics, data lakes, big-data tooling | Columnar, compressed (~half of CSV), typed; binary |

Only the **CSV** files are needed by the app. JSONL and Parquet are kept to show
modern data-format handling and for any future analytics use.

---

## Get the dataset

The raw MKQA dataset is **not included in this repo** (it's large, externally
licensed, and freely downloadable). Download it yourself before running:

- **Official source (Apple):** https://github.com/apple/ml-mkqa
- **Direct file:** https://github.com/apple/ml-mkqa/raw/main/dataset/mkqa.jsonl.gz
- **HuggingFace mirror:** https://huggingface.co/datasets/apple/mkqa

> The file ships gzipped (`mkqa.jsonl.gz`). Unzip it to `mkqa.jsonl` and place it
> in `Scripts for data conversion/data/` before running.

**Dataset:** MKQA — 10,000 questions aligned across 26 languages.
**Citation:** Longpre, Lu, Daiber. *MKQA: A Linguistically Diverse Benchmark for
Multilingual Open Domain Question Answering* (2020).

---

## How to run

From the **project root**:

```bash
# 1. Install the one extra dependency (Parquet support)
pip install pyarrow

# 2. Run the conversion (point it at the raw MKQA file)
python "Scripts for data conversion/script.py" "Scripts for data conversion/data/mkqa.jsonl"
```

Output appears in a `tenant_datasets/` folder with `csv/`, `jsonl/`, and
`parquet/` subfolders.

---

## Configuration

Open `script.py` and edit the top section:

- **`TENANTS`** — add or change tenants. To add French, add one line:
  `"tenant_someco_fr": ("SomeCo France", "fr"),`
- **`ROWS_PER_TENANT`** — rows per tenant (default `500`). Raise once local
  embedding speed is comfortable.

MKQA language codes include: `en, es, pt, fr, de, it, nl, ru, ja, ko, ar, zh_cn`,
and more.

---

## After running

1. Copy the CSV files from `tenant_datasets/csv/` into the app's `Files/` folder
   (or wherever your ingestion command reads from).
2. The raw `data/mkqa.jsonl` is no longer needed and can be deleted to save space.
3. Ingest each tenant file into the RAG system, scoped to its tenant.

---

## Notes

- Rows with no answer (MKQA "unanswerable" entries) are skipped automatically.
- The script reads the large raw file only once and buckets rows in memory, so it
  stays fast even on the full 10k-record dataset.
- This step is safe to re-run; it overwrites the output folder each time.
