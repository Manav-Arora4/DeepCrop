import re
from pathlib import Path
from typing import List, Dict, Any
from backend.core.config import get_settings


def split_knowledge(crop_id: str, knowledge_dir: Path) -> list:
    """
    Split each Markdown doc into one chunk per `## ` section, prefixed with the doc title so the
    chunk is self-describing. The `## Sources` section is not embedded; its references are stored
    in every chunk's metadata so answers can cite them.
    """
    from langchain_core.documents import Document

    chunks = []
    for path in sorted(knowledge_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), path.stem)
        parts = re.split(r"\n(?=## )", text)
        refs = ""
        sections = []
        for part in parts[1:]:
            heading = part.splitlines()[0][3:].strip()
            body = part.split("\n", 1)[1].strip() if "\n" in part else ""
            if heading.lower() == "sources":
                refs = "\n".join(l[2:].strip() for l in body.splitlines() if l.startswith("- "))
            else:
                sections.append((heading, body))
        rel = path.relative_to(knowledge_dir).as_posix()
        doc_id = rel[:-3]
        topic = rel.split("/")[0] if "/" in rel else path.stem
        disease = path.stem if rel.startswith("diseases/") else ""
        for i, (heading, body) in enumerate(sections):
            chunks.append(Document(
                page_content=f"{title} — {heading}\n\n{body}",
                metadata={
                    "crop": crop_id, "doc": doc_id, "title": title, "section": heading,
                    "topic": topic, "disease": disease, "references": refs,
                    "chunk_id": f"{doc_id}#{i}", "source": str(path),
                },
            ))
    return chunks


class RAGService:
    """
    Retrieval-Augmented Generation Service using ChromaDB and BAAI/bge-small-en-v1.5.
    Ingests and queries modular crop knowledge bases.
    """

    def __init__(self):
        self.settings = get_settings()
        self._embeddings = None
        self._vectorstores: Dict[str, Any] = {}

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def _get_vectorstore(self, crop_id: str):
        if crop_id in self._vectorstores:
            return self._vectorstores[crop_id]

        from langchain_chroma import Chroma
        embeddings = self._get_embeddings()
        collection_name = f"crophealth_{crop_id}"
        persist_dir = str(Path(self.settings.CHROMA_PERSIST_PATH) / crop_id)

        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )
        self._vectorstores[crop_id] = vectorstore
        return vectorstore

    async def ingest_crop_knowledge(self, crop_id: str, knowledge_dir: str | Path, force: bool = False) -> int:
        """Ingest a crop's Markdown knowledge base into ChromaDB, one chunk per `## ` section."""
        k_path = Path(knowledge_dir)
        if not k_path.exists():
            return 0

        vectorstore = self._get_vectorstore(crop_id)
        count = vectorstore._collection.count()
        if count > 0 and not force:
            return count
        if count > 0:
            vectorstore.delete(ids=vectorstore.get()["ids"])

        chunks = split_knowledge(crop_id, k_path)
        if not chunks:
            return 0
        vectorstore.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])
        return len(chunks)

    async def retrieve(self, crop_id: str, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Retrieve relevant agronomic knowledge passages."""
        try:
            vectorstore = self._get_vectorstore(crop_id)
            docs = vectorstore.similarity_search_with_relevance_scores(query, k=k)
            results = []
            for doc, score in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance": round(float(score), 3),
                    "source": doc.metadata.get("doc", Path(doc.metadata.get("source", "knowledge")).name),
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "references": [r for r in doc.metadata.get("references", "").split("\n") if r],
                })
            return results
        except Exception as e:
            print(f"[RAGService] Retrieval error for crop '{crop_id}': {e}")
            return []

    def get_collection_stats(self, crop_id: str) -> Dict[str, Any]:
        try:
            vectorstore = self._get_vectorstore(crop_id)
            count = vectorstore._collection.count()
            return {"exists": True, "document_count": count, "crop_id": crop_id}
        except Exception:
            return {"exists": False, "document_count": 0, "crop_id": crop_id}


_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
