from pgvector.django import CosineDistance
from documents.models import DocumentChunk
from documents.services.embeddings import embed_query


def retrieve_chunks(query: str, tenant_id: int, top_k: int = 5,
                    max_distance: float = 0.85) -> list[dict]:
    """
    Find the most relevant chunks for a query — WITHIN ONE TENANT only.
    Returns a list of dicts with content, source, category, and distance
    so callers can surface source attribution to users.
    """
    query_vector = embed_query(query)

    results = (
        DocumentChunk.objects
        .filter(tenant_id=tenant_id)                              # THE ISOLATION LINE
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lt=max_distance)
        .order_by("distance")
        [:top_k]
    )

    return [
        {
            "content": r.content,
            "source": r.source,
            "category": r.category,
            "distance": round(float(r.distance), 4),
        }
        for r in results
    ]
