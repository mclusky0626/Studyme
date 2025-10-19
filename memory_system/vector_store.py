import chromadb
from chromadb.types import Where
from typing import List, Dict, Any

from memory_system.schemas import MemoryChunk

# 데이터베이스 파일이 저장될 경로
DB_PATH = "./data/chroma_db"
COLLECTION_NAME = "memory_collection"


class VectorStore:
    """
    벡터 데이터베이스(ChromaDB)와의 상호작용을 관리하는 클래스입니다.
    메모리 추가, 검색 등의 기능을 추상화하여 제공합니다.
    """

    def __init__(self):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

    def _chunk_to_metadata(self, chunk: MemoryChunk) -> Dict[str, Any]:
        """MemoryChunk 객체를 ChromaDB의 메타데이터 형식(dict)으로 변환합니다."""
        metadata = chunk.model_dump()
        metadata['timestamp'] = chunk.timestamp.isoformat()

        # --- ✨ 여기가 수정된 부분입니다 ✨ ---
        # ChromaDB는 metadata 값으로 None을 허용하지 않으므로, None을 빈 문자열로 변환합니다.
        if metadata.get('entities') is None:
            metadata['entities'] = ""
        # --- ✨ 수정 끝 ✨ ---

        return metadata

    def add_memory(self, chunk: MemoryChunk, embedding: List[float]):
        """
        하나의 기억 조각(chunk)과 그에 해당하는 임베딩 벡터를 DB에 추가합니다.
        """
        self.collection.add(
            ids=[chunk.id],
            embeddings=[embedding],
            metadatas=[self._chunk_to_metadata(chunk)],
            documents=[chunk.content]
        )
        print(f"✅ 기억이 추가되었습니다: (ID: {chunk.id})")

    def search_memories(
            self,
            query_embedding: List[float],
            n_results: int = 5,
            filter_where: Where | None = None
    ) -> List[MemoryChunk]:
        """
        주어진 쿼리 임베딩과 가장 유사한 기억들을 검색합니다.
        """
        query_args = {
            'query_embeddings': [query_embedding],
            'n_results': n_results
        }

        if filter_where:
            query_args['where'] = filter_where

        query_result = self.collection.query(**query_args)

        retrieved_metadatas = query_result.get('metadatas', [[]])[0]
        return [MemoryChunk(**meta) for meta in retrieved_metadatas]

    def get_important_memories(self, user_id: int | None = None) -> List[MemoryChunk]:
        """
        (현재 사용 안 함) 'is_important' 플래그가 True인 모든 중요 기억을 가져옵니다.
        """
        where_filter: Where = {"is_important": True}
        if user_id:
            where_filter = {"$and": [{"is_important": True}, {"user_id": user_id}]}

        results = self.collection.get(where=where_filter, limit=100)  # get에는 limit 사용

        retrieved_metadatas = results.get('metadatas', [])
        return [MemoryChunk(**meta) for meta in retrieved_metadatas]