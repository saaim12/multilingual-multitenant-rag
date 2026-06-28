import os
from google import genai
from documents.models import Tenant
from documents.services.retrieval import retrieve_chunks

# The LLM that writes answers (generation). Embeddings are local (e5),
# but generation still uses Gemini.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def rag_query(user_query: str, tenant_id: int) -> dict:
    """
    Full RAG flow for one tenant:
      1. Retrieve this tenant's most relevant chunks.
      2. If nothing relevant, return "I don't know" (no hallucinating).
      3. Build a prompt that forces the LLM to answer ONLY from those chunks.
      4. Call Gemini to write the answer.
      5. Return the answer + the chunks it used.
    """

    # 1. Retrieve — note tenant_id is passed through (isolation preserved)
    chunks = retrieve_chunks(user_query, tenant_id=tenant_id)

    # 2. Nothing relevant found → honest refusal
    # the distance filter in retrieval? If everything was too far away, chunks is empty. Rather than asking the LLM to answer with no context (where it would guess), we short-circuit and honestly say we don't know. This is the anti-hallucination safety net.
    if not chunks:
        return {"answer": "I don't know based on the available documents.",
                "context": []}

    # 3. Glue the chunks into one context block, then build a grounded prompt
    context = "\n\n---\n\n".join(chunks)

    prompt = f"""You are a helpful assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know based on the available documents."
Answer in the same language as the question.

Context:
{context}

Question: {user_query}

Answer:"""

    # 4. Call Gemini to generate the answer
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    # 5. Return the answer plus the chunks used (handy for debugging/trust)
    return {"answer": response.text, "context": chunks}