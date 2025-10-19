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
        metadata = chunk.model_dump()
        metadata['timestamp'] = chunk.timestamp.isoformat()
        return metadata

    def add_memory(self, chunk: MemoryChunk, embedding: List[float]):
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

        Args:
            query_embedding (List[float]): 검색의 기준이 될 임베딩 벡터.
            n_results (int): 반환할 결과의 수.
            filter_where (Where | None): 검색 결과를 필터링할 조건.

        Returns:
            List[MemoryChunk]: 검색된 기억 조각 객체의 리스트.
        """
        # --- ✨ 여기가 수정된 부분입니다 ✨ ---
        # 쿼리에 사용할 인자를 동적으로 구성합니다.
        query_args = {
            'query_embeddings': [query_embedding],
            'n_results': n_results
        }

        # filter_where 조건이 있을 때만 'where' 인자를 추가합니다.
        if filter_where:
            query_args['where'] = filter_where

        # 동적으로 만들어진 인자로 쿼리를 실행합니다.
        query_result = self.collection.query(**query_args)
        # --- ✨ 수정 끝 ✨ ---

        retrieved_metadatas = query_result.get('metadatas', [[]])[0]
        return [MemoryChunk(**meta) for meta in retrieved_metadatas]

    def get_important_memories(self, user_id: int | None = None) -> List[MemoryChunk]:
        where_filter: Where = {"is_important": True}
        if user_id:
            where_filter = {"$and": [{"is_important": True}, {"user_id": user_id}]}

        results = self.collection.get(where=where_filter)

        retrieved_metadatas = results.get('metadatas', [])
        return [MemoryChunk(**meta) for meta in retrieved_metadatas]