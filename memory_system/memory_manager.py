import os
import google.generativeai as genai
from typing import List

from memory_system.schemas import MemoryChunk
from memory_system.vector_store import VectorStore
from memory_system.summarizer import summarizer
from memory_system.tokenizer import tokenizer

# Gemini API 설정 (임베딩 생성을 위해)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class MemoryManager:
    """
    기억 저장, 검색, 요약 등 모든 메모리 관련 작업을 총괄하는 컨트롤러 클래스.
    HypaMemoryV3와 SupaMemory의 아이디어를 통합합니다.
    """

    def __init__(self, embedding_model_name: str = "models/embedding-001"):
        self.vector_store = VectorStore()
        self.summarizer = summarizer
        self.tokenizer = tokenizer
        self.embedding_model_name = embedding_model_name

    async def _get_embedding_async(self, text: str) -> List[float]:
        """주어진 텍스트의 임베딩 벡터를 비동기적으로 생성합니다."""
        try:
            result = await genai.embed_content_async(
                model=self.embedding_model_name,
                content=text,
                task_type="RETRIEVAL_DOCUMENT"  # 검색 목적의 임베딩
            )
            return result['embedding']
        except Exception as e:
            print(f"임베딩 생성 중 오류 발생: {e}")
            return []

    async def add_new_memory(self, chunk: MemoryChunk):
        """
        새로운 기억 조각을 받아 임베딩을 생성하고 벡터 DB에 저장합니다.
        """
        embedding = await self._get_embedding_async(chunk.content)
        if embedding:
            self.vector_store.add_memory(chunk, embedding)

    async def retrieve_relevant_memories(
            self,
            current_text: str,
            user_id: int,
            n_similarity: int = 3,
            n_recent: int = 2  # 최근 기억은 아직 구현 전, 향후 추가
    ) -> List[MemoryChunk]:
        """
        현재 대화 내용과 가장 관련성 높은 기억들을 검색하여 반환합니다.
        HypaMemoryV3의 핵심 검색 로직입니다.

        1. 중요 기억을 가져옵니다.
        2. 현재 대화와 유사한 기억을 검색합니다.
        3. (향후) 최근 대화 기록을 추가합니다.
        4. 중복을 제거하고 최종 리스트를 반환합니다.
        """
        query_embedding = await self._get_embedding_async(current_text)
        if not query_embedding:
            return []

        # 1. 이 사용자와 관련된 중요 기억 모두 가져오기
        important_memories = self.vector_store.get_important_memories(user_id=user_id)

        # 2. 현재 대화와 유사한 기억 n개 검색 (같은 사용자 우선)
        similar_memories = self.vector_store.search_memories(
            query_embedding,
            n_results=n_similarity,
            filter_where={"user_id": user_id}
        )

        # 만약 사용자 특정 메모리가 부족하면, 전체에서 검색
        if len(similar_memories) < n_similarity:
            general_similar_memories = self.vector_store.search_memories(
                query_embedding,
                n_results=n_similarity - len(similar_memories)
            )
            similar_memories.extend(general_similar_memories)

        # 3. 모든 기억을 합치고 중복 제거
        all_memories = important_memories + similar_memories

        # id를 기준으로 중복 제거 (set을 사용하여 순서 유지)
        seen_ids = set()
        unique_memories = []
        for mem in all_memories:
            if mem.id not in seen_ids:
                unique_memories.append(mem)
                seen_ids.add(mem.id)

        # 최신순으로 정렬
        unique_memories.sort(key=lambda m: m.timestamp, reverse=True)

        return unique_memories

    def build_context_from_memories(self, memories: List[MemoryChunk], max_tokens: int = 1500) -> str:
        """
        검색된 기억 조각 리스트를 LLM에 전달할 하나의 컨텍스트 문자열로 조립합니다.
        토큰 제한을 관리합니다.
        """
        context_str = "기억 저장소에서 현재 대화와 관련이 높은 과거 정보를 찾았어. 응답에 참고해:\n\n"
        current_tokens = self.tokenizer.count_tokens(context_str)

        # 최신 기억부터 순서대로 추가
        for mem in memories:
            memory_line = f"- [{mem.timestamp.strftime('%Y-%m-%d')}, {mem.author_name}]: {mem.content}\n"
            line_tokens = self.tokenizer.count_tokens(memory_line)

            if current_tokens + line_tokens > max_tokens:
                break  # 토큰 제한 초과 시 중단

            context_str += memory_line
            current_tokens += line_tokens

        return context_str if len(context_str.splitlines()) > 2 else ""


# 사용 편의를 위해 싱글턴 인스턴스 생성
memory_manager = MemoryManager()