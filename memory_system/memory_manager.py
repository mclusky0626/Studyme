import os
import google.generativeai as genai
from typing import List

from memory_system.schemas import MemoryChunk
from memory_system.vector_store import VectorStore
from memory_system.tokenizer import tokenizer
# 새로 추가된 프롬프트 임포트
from prompts.fact_extraction import FACT_EXTRACTION_PROMPT
from prompts.entity_extraction import ENTITY_EXTRACTION_PROMPT

# Gemini API 설정 (임베딩 생성을 위해)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class MemoryManager:
    """
    기억 저장, 검색, 요약 등 모든 메모리 관련 작업을 총괄하는 컨트롤러 클래스.
    '기억-엔티티 연결' 전략을 사용하여 지식 네트워크를 구축합니다.
    """

    def __init__(self, embedding_model_name: str = "models/embedding-001"):
        self.vector_store = VectorStore()
        self.tokenizer = tokenizer
        self.embedding_model_name = embedding_model_name
        # 사실 및 엔티티 추출을 위한 모델 인스턴스
        self.fact_extraction_model = genai.GenerativeModel("gemini-2.5-flash")

    async def _get_embedding_async(self, text: str) -> List[float]:
        """주어진 텍스트의 임베딩 벡터를 비동기적으로 생성합니다."""
        try:
            result = await genai.embed_content_async(
                model=self.embedding_model_name,
                content=text,
                task_type="RETRIEVAL_DOCUMENT"
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

    def build_context_from_memories(self, memories: List[MemoryChunk], max_tokens: int = 1500) -> str:
        """
        검색된 기억 조각 리스트를 LLM에 전달할 하나의 컨텍스트 문자열로 조립합니다.
        """
        if not memories:
            return ""

        context_str = "--- [과거 기억]\n"
        current_tokens = self.tokenizer.count_tokens(context_str)

        for mem in memories:
            memory_line = f"- [{mem.timestamp.strftime('%Y-%m-%d')}, {mem.author_name}]: {mem.content}\n"
            line_tokens = self.tokenizer.count_tokens(memory_line)

            if current_tokens + line_tokens > max_tokens:
                break

            context_str += memory_line
            current_tokens += line_tokens

        return context_str

    async def _extract_entities_from_text(self, text: str, author_name: str) -> List[str]:
        """주어진 텍스트에서 엔티티를 추출하는 내부 헬퍼 함수"""
        prompt = ENTITY_EXTRACTION_PROMPT.format(fact_text=text, author_name=author_name)
        try:
            response = await self.fact_extraction_model.generate_content_async(prompt)
            entities_text = response.text.strip()
            if "없음" in entities_text or not entities_text:
                return []
            # 쉼표와 공백을 기준으로 분리하고, 각 항목의 양쪽 공백을 제거
            return [e.strip() for e in entities_text.split(',') if e.strip()]
        except Exception as e:
            print(f"엔티티 추출 중 오류 발생: {e}")
            return []

    async def process_and_store_automatic_memory(
            self, user_chunk: MemoryChunk, user_query: str, bot_response: str
    ):
        fact_prompt = FACT_EXTRACTION_PROMPT.format(
            author_name=user_chunk.author_name, user_query=user_query, bot_response=bot_response
        )
        try:
            response = await self.fact_extraction_model.generate_content_async(fact_prompt)
            extracted_facts_text = response.text.strip()
            if "정보 없음" in extracted_facts_text or not extracted_facts_text: return

            facts = [fact.strip() for fact in extracted_facts_text.split('\n') if fact.strip()]
            for fact in facts:
                entities_list = await self._extract_entities_from_text(fact, user_chunk.author_name)

                # 리스트를 특수 형식의 문자열로 변환
                entities_str = f",{','.join(entities_list)}," if entities_list else None

                print(f"--- [엔티티 태깅 결과] --- 사실: '{fact}', 변환된 문자열: {entities_str}")

                new_fact_chunk = MemoryChunk(
                    user_id=user_chunk.user_id,
                    author_name=user_chunk.author_name,
                    channel_id=user_chunk.channel_id,
                    content=fact,
                    is_important=False,
                    entities=entities_str  # 변환된 문자열을 저장
                )
                await self.add_new_memory(new_fact_chunk)
        except Exception as e:
            print(f"❌ 자동 기억 처리 중 오류 발생: {e}")

        # --- ✨ retrieve_relevant_memories 수정 (핵심 변경) ✨ ---

    async def retrieve_relevant_memories(
            self, current_text: str, user_id: int, n_results: int = 20
    ) -> List[MemoryChunk]:

        # 1단계: 질문에서 핵심 엔티티 추출
        query_entities = await self._extract_entities_from_text(current_text, "사용자")
        print(f"--- [쿼리 엔티티 추출] --- {query_entities}")

        # 모든 기억을 일단 가져옴 (DB가 작을 때 효과적인 방식, 나중에는 최적화 필요)
        # 실제 운영 시에는 이 부분을 .get()의 limit을 늘리거나, 더 정교한 쿼리로 바꿔야 함
        all_db_memories_dict = self.vector_store.collection.get()
        all_db_memories = [MemoryChunk(**meta) for meta in all_db_memories_dict.get('metatas', [])]

        # 2단계: 직접 엔티티 검색
        direct_matches: List[MemoryChunk] = []
        if query_entities:
            for mem in all_db_memories:
                if mem.entities and any(f",{entity}," in mem.entities for entity in query_entities):
                    direct_matches.append(mem)

        # 3단계: 연관 엔티티 확장
        related_entities = set(query_entities)
        for mem in direct_matches:
            # 기억 내용 자체에서도 엔티티를 다시 추출하여 관련성을 확장
            content_entities = await self._extract_entities_from_text(mem.content, mem.author_name)
            for entity in content_entities:
                related_entities.add(entity)
            # author_name도 중요한 연관 엔티티
            related_entities.add(mem.author_name)

        print(f"--- [연관 엔티티 확장] --- {related_entities}")

        # 4단계: 확장 검색
        expanded_matches: List[MemoryChunk] = []
        if related_entities:
            for mem in all_db_memories:
                # 기억 내용이나 엔티티 태그에 연관 엔티티가 하나라도 포함되면 추가
                if any(entity in mem.content for entity in related_entities) or \
                        (mem.entities and any(f",{entity}," in mem.entities for entity in related_entities)):
                    expanded_matches.append(mem)

        # 5단계: 의미 유사도 검색 추가 (보너스 점수)
        embedding = await self._get_embedding_async(current_text)
        semantic_matches = []
        if embedding:
            semantic_matches = self.vector_store.search_memories(embedding, n_results=n_results)

        # 6단계: 모든 결과를 합치고 중복 제거
        final_matches = direct_matches + expanded_matches + semantic_matches
        seen_ids = set()
        unique_memories = []
        for mem in final_matches:
            if mem.id not in seen_ids:
                unique_memories.append(mem)
                seen_ids.add(mem.id)

        print(f"--- [기억 검색 결과] --- 총 {len(unique_memories)}개의 고유한 기억 반환")
        return unique_memories[:n_results]

    # 싱글턴 인스턴스 생성
memory_manager = MemoryManager()