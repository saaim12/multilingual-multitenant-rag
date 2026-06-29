from sentence_transformers import SentenceTransformer

# We use multilingual-e5-base:
#   - understands 100+ languages (Spanish, Portuguese, English, etc.)
#   - outputs 768-dimensional vectors (matches our DB column)
#   - runs LOCALLY on your machine — no API key, no quota, free

# The model is heavy to load (~1GB, takes a few seconds), so we load it
# ONCE and reuse it. This pattern is called a "singleton" — one shared instance.
_model = None

def _get_model():
    """Load the model on first use, then reuse the same instance."""
    global _model
    if _model is None:
        _model = SentenceTransformer("intfloat/multilingual-e5-base")
    return _model


def embed_document(text: str) -> list[float]:
    """
    Embed a DOCUMENT (something we store and search against).
    e5 requires the 'passage:' prefix for documents — it was trained this way.
    """
    vec = _get_model().encode(f"passage: {text}", normalize_embeddings=True)
    return vec.tolist()


def embed_query(text: str) -> list[float]:
    """
    Embed a QUERY (a user's question).
    e5 requires the 'query:' prefix for questions.
    """
    vec = _get_model().encode(f"query: {text}", normalize_embeddings=True)
    return vec.tolist()


def embed_documents_batch(texts: list[str]) -> list[list[float]]:
    """Batch-embed multiple documents in one model call (much faster than one by one)."""
    prefixed = [f"passage: {t}" for t in texts]
    vecs = _get_model().encode(prefixed, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vecs]


# embed_document → used when storing your data (ingestion). Every CSV row's text becomes a "bus stop" on the map and gets saved in the DB. You run this once when loading data.
# embed_query → used when someone asks a question (the API call). Their question becomes a "person" looking for nearby bus stops. You run this every time a query comes in.
# So:
# FunctionWhenHow oftenLabelembed_documentLoading data into DBOnce per documentpassage:embed_queryUser asks via APIEvery requestquery:
#query is for like API type shit