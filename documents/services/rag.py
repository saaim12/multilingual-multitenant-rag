import os
import time
import logging
from google import genai
from documents.services.retrieval import retrieve_chunks
from documents.services.prompts import build_prompt

logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_RETRY_DELAYS = [1, 3]  # seconds before attempt 2 and 3


def rag_query(user_query: str, tenant_id: int, template: str = "qa") -> dict:
    """
    Full RAG flow for one tenant:
      1. Retrieve this tenant's most relevant chunks (tenant-isolated).
      2. If nothing relevant, return honest refusal (no hallucination).
      3. Build a prompt using the selected template.
      4. Call Gemini to generate the answer (with retry on 429).
      5. Return answer + source chunks.
    """
    chunks = retrieve_chunks(user_query, tenant_id=tenant_id)

    if not chunks:
        return {"answer": "I don't know based on the available documents.", "context": []}

    context_text = "\n\n---\n\n".join(c["content"] for c in chunks)
    prompt = build_prompt(template, context_text, user_query)

    last_error = None
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return {"answer": response.text, "context": chunks}
        except Exception as exc:
            err_str = str(exc)
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                last_error = exc
                logger.warning("Gemini rate limit hit (attempt %d): %s", attempt + 1, err_str)
                continue
            raise

    logger.error("Gemini rate limit exceeded after all retries: %s", last_error)
    return {
        "error": "Generation rate limit exceeded. Please try again in a moment.",
        "context": [],
    }
