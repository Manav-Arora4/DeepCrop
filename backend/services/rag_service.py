from pathlib import Path
from typing import List, Dict, Any
from backend.core.config import get_settings


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
        """Ingest all Markdown knowledge documents for a crop into ChromaDB."""
        k_path = Path(knowledge_dir)
        if not k_path.exists():
            return 0

        vectorstore = self._get_vectorstore(crop_id)
        if not force:
            count = vectorstore._collection.count()
            if count > 0:
                return count

        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        loader = DirectoryLoader(
            str(k_path),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        )
        docs = loader.load()
        if not docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
        chunks = splitter.split_documents(docs)

        # Inject crop_id into metadata
        for chunk in chunks:
            chunk.metadata["crop"] = crop_id

        vectorstore.add_documents(chunks)
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
                    "source": Path(doc.metadata.get("source", "knowledge")).name,
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
