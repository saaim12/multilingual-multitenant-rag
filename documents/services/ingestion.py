import csv
import os
from documents.models import Tenant, DocumentChunk
from documents.services.embeddings import embed_document


def ingest_csv(file_path: str, tenant_name: str) -> int:
    """
    Load one CSV into the database under a given tenant.

    Steps:
      1. Find or create the tenant (the company that owns this data).
      2. Read each CSV row (name, category, question, answer).
      3. Combine question + answer into one 'content' string.
      4. Turn content into a vector (embedding).
      5. Save it all as a DocumentChunk row tied to the tenant.
    """

#    Tenant.objects.get_or_create(name=tenant_name)
# This is the tenant magic. It checks: "does a tenant named 'Acme Translations' already exist?"
# If yes → use it.
# If no → create it.
    tenant, created = Tenant.objects.get_or_create(name=tenant_name)

    source = os.path.basename(file_path)  # e.g. "tenant_acme_es.csv"
    objects = []

    # 2. Read the CSV
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # reads rows as dicts: row["question"], etc.
        for row in reader:
            # 3. Combine question + answer into the searchable text
            content = f"Q: {row['question'].strip()}\nA: {row['answer'].strip()}"

            # 4. Turn that text into a vector (a "bus stop" on the meaning-map)
            embedding = embed_document(content)

            # 5. Build the DB row (not saved yet — collected for bulk insert)
            objects.append(DocumentChunk(
                tenant=tenant,
                source=source,
                category=row.get("category", "").strip(),
                content=content,# conetnt is both question and answer
                embedding=embedding,
                metadata={"name": row.get("name", "").strip()},
            ))

    # Save all rows at once (much faster than saving one by one)
    DocumentChunk.objects.bulk_create(objects)
    return len(objects)