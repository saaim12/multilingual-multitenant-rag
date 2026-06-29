import csv
import logging
import os

from documents.models import DocumentChunk, Tenant
from documents.services.embeddings import embed_documents_batch

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"name", "category", "question", "answer"}


def ingest_csv(file_path: str, tenant_name: str, source_name: str = None) -> dict:
    """
    Load one CSV into the database under a given tenant.

    Returns a dict: {"created": int, "skipped": int}

    Idempotency: existing chunks for (tenant, source) are deleted first so
    re-uploading the same file replaces rather than duplicates data.

    Validation: rows missing required columns are skipped and counted.

    Batch embedding: all valid rows are embedded in one model call.
    """
    tenant, _ = Tenant.objects.get_or_create(name=tenant_name)
    source = source_name or os.path.basename(file_path)

    rows_data = []
    skipped = 0

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Validate header
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            raise ValueError(f"CSV is missing required columns: {missing}")

        for i, row in enumerate(reader, start=2):  # row 1 is header
            try:
                question = row["question"].strip()
                answer = row["answer"].strip()
                if not question or not answer:
                    raise ValueError("empty question or answer")
                rows_data.append({
                    "content": f"Q: {question}\nA: {answer}",
                    "category": row.get("category", "").strip(),
                    "name": row.get("name", "").strip(),
                })
            except Exception as exc:
                logger.warning("Skipping row %d in %s: %s", i, source, exc)
                skipped += 1

    if not rows_data:
        return {"created": 0, "skipped": skipped}

    # Idempotency: delete existing chunks for this (tenant, source) before inserting
    deleted, _ = DocumentChunk.objects.filter(tenant=tenant, source=source).delete()
    if deleted:
        logger.info("Replaced %d existing chunks for source '%s'", deleted, source)

    # Batch embed — one model call for all rows (much faster)
    texts = [r["content"] for r in rows_data]
    embeddings = embed_documents_batch(texts)

    objects = [
        DocumentChunk(
            tenant=tenant,
            source=source,
            category=r["category"],
            content=r["content"],
            embedding=emb,
            metadata={"name": r["name"]},
        )
        for r, emb in zip(rows_data, embeddings)
    ]

    DocumentChunk.objects.bulk_create(objects)
    return {"created": len(objects), "skipped": skipped}
