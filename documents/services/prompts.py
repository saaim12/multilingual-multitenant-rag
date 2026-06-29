TEMPLATES = {
    "qa": (
        "You are a helpful assistant. Answer the question using ONLY the context below.\n"
        "If the answer is not in the context, say \"I don't know based on the available documents.\"\n"
        "Answer in the same language as the question.\n\n"
        "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    ),
    "summarize": (
        "You are a document summarizer. Summarize the content below concisely.\n"
        "Use ONLY information present in the context. Do NOT add outside knowledge.\n"
        "If there is nothing relevant to summarize, say \"I don't know based on the available documents.\"\n"
        "Answer in the same language as the question.\n\n"
        "Context:\n{context}\n\nSummarize for: {query}\n\nSummary:"
    ),
    "translate": (
        "You are a translator. Translate the relevant content from the context to the language requested.\n"
        "Use ONLY text present in the context. Do NOT add information not in the context.\n"
        "If the translation cannot be completed from the context, say \"I don't know based on the available documents.\"\n\n"
        "Context:\n{context}\n\nTranslation request: {query}\n\nTranslation:"
    ),
    "glossary": (
        "You are a terminology expert. Define the term asked about using ONLY the exact\n"
        "terminology and definitions found in the context below.\n"
        "If the term is not defined in the context, say \"I don't know based on the available documents.\"\n"
        "Answer in the same language as the question.\n\n"
        "Context:\n{context}\n\nTerm to define: {query}\n\nDefinition:"
    ),
    "extract": (
        "You are a fact extractor. Extract the specific fact or piece of information requested\n"
        "from the context below. Use ONLY information from the context.\n"
        "If the fact is not present, say \"I don't know based on the available documents.\"\n"
        "Answer in the same language as the question.\n\n"
        "Context:\n{context}\n\nWhat to extract: {query}\n\nExtracted fact:"
    ),
    "explain": (
        "You are a teacher. Explain the concept asked about in simple, clear terms\n"
        "using ONLY the context below as your source. Do NOT add outside knowledge.\n"
        "If the concept is not covered in the context, say \"I don't know based on the available documents.\"\n"
        "Answer in the same language as the question.\n\n"
        "Context:\n{context}\n\nConcept to explain: {query}\n\nSimple explanation:"
    ),
}

VALID_TEMPLATES = list(TEMPLATES.keys())


def build_prompt(template_key: str, context: str, query: str) -> str:
    template = TEMPLATES.get(template_key, TEMPLATES["qa"])
    return template.format(context=context, query=query)
