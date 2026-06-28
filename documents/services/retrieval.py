from pgvector.django import CosineDistance
from documents.models import DocumentChunk
from documents.services.embeddings import embed_query


def retrieve_chunks(query: str, tenant_id: int, top_k: int = 5,
                    max_distance: float = 0.65) -> list[str]:
    """
    Find the most relevant chunks for a query — WITHIN ONE TENANT only.
    Steps:
      1. Turn the user's question into a vector.
      2. Search ONLY this tenant's chunks (the isolation step).
      3. Sort by closeness (smaller cosine distance = more similar).
      4. Drop anything too far away (irrelevant).
      5. Return the top_k closest chunks' text.
    """

    # 1. Turn the question into a vector ("person looking for a bus stop")
    query_vector = embed_query(query)

    # 2-4. Search, scoped to this tenant
    results = (
        DocumentChunk.objects
        .filter(tenant_id=tenant_id)                              # THE ISOLATION LINE
        .annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lt=max_distance)                        # drop irrelevant
        .order_by("distance")                                     # closest first
        [:top_k]                                                  # keep top K
    )

    # 5. Return just the text of each chunk
    return [r.content for r in results]