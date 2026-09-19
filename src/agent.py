from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "I could not find relevant information in the knowledge base."

        context = "\n\n".join(
            f"[{index}] Source: {result['metadata'].get('source_url', result['metadata'].get('source', result['metadata'].get('doc_id', 'unknown')))}\n{result['content']}"
            for index, result in enumerate(results, start=1)
        )
        prompt = (
            "Answer the question using only the retrieved context. Cite the supporting "
            "chunk number(s) in square brackets. If the context does not contain the "
            "answer, say that you do not know.\n\n"
            f"Retrieved context:\n{context or '(No relevant context was retrieved.)'}\n\n"
            f"Question: {question}\nAnswer:"
        )
        return self.llm_fn(prompt)
