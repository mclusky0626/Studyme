import os
import google.generativeai as genai
from typing import List
import re
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

    def build_context_from_memories(
            self, memories: List[MemoryChunk], current_user_id: int, current_user_name: str, max_tokens: int = 2000
    ) -> str:
        if not memories: return ""
        context_str = "--- [과거 기억]\n"

        for mem in memories:
            if mem.user_id == current_user_id:
                if current_user_name in mem.content:
                    prefix = f"[과거의 당신({mem.author_name})]"
                else:
                    prefix = "[과거의 당신]"
            else:
                prefix = f"[{mem.author_name}]"

            memory_line = f"- {prefix}: {mem.content}\n"
            context_str += memory_line

        # 올바른 tiktoken 사용법으로 수정
        # self.tokenizer 안에 있는 self.encoding 객체를 사용해야 함
        encoded_tokens = self.tokenizer.encoding.encode(context_str)
        if len(encoded_tokens) > max_tokens:
            # 토큰 리스트를 자른 뒤, 다시 디코딩하여 문자열로 변환
            context_str = self.tokenizer.encoding.decode(encoded_tokens[:max_tokens])

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
            self, current_text: str, user_id: int, user_name: str, n_results: int = 15
    ) -> List[MemoryChunk]:

        query_entities = await self._extract_entities_from_text(current_text, user_name)

        # 1단계: 자기 인식 - 1인칭 대명사가 있으면 사용자 이름을 검색 키워드에 추가
        if re.search(r'\b(나|내|내가)\b', current_text):
            query_entities.append(user_name)
            print(f"--- [자기 인식] --- 현재 사용자 '{user_name}'를 검색 키워드에 추가")

        print(f"--- [최종 검색 키워드] --- {list(set(query_entities))}")

        # 2단계: 타겟 검색 - 현재 사용자가 생성한 기억을 먼저 가져옴
        embedding = await self._get_embedding_async(current_text)
        self_memories = []
        if embedding:
            self_memories = self.vector_store.search_memories(
                embedding,
                n_results=n_results * 2,  # 넉넉하게
                filter_where={"author_name": user_name}  # user_id 대신 author_name으로 필터링
            )

        # 3단계: 네트워크 확장 검색 - 전체 DB에서 의미가 비슷한 기억을 추가로 가져옴
        general_memories = []
        if embedding:
            general_memories = self.vector_store.search_memories(embedding, n_results=n_results * 2)

        candidate_memories = self_memories + general_memories

        # 4단계: 증거 기반 점수 시스템
        scored_memories = []
        for mem in candidate_memories:
            score = 0.0
            # 최우선 증거 (+1000점): 자기 자신의 기억
            if mem.author_name == user_name:
                score += 1000

            # 강력한 증거 (+100점): 내용에 키워드가 포함
            if query_entities and any(entity in mem.content for entity in query_entities):
                score += 100

            # 보조 증거 (+50점): 엔티티 태그에 키워드가 포함
            if query_entities and mem.entities and any(f",{entity}," in mem.entities for entity in query_entities):
                score += 50

            # 최신성 점수
            score += mem.timestamp.timestamp() / 1e10

            if score > 0:
                scored_memories.append((score, mem))

        # 점수가 높은 순으로 정렬
        scored_memories.sort(key=lambda x: x[0], reverse=True)

        final_results = []
        seen_ids = set()
        print("--- [우선순위화된 기억 목록] ---")
        for score, mem in scored_memories:
            if mem.id not in seen_ids:
                print(f"  - (Score: {score:.2f}) Memory: [{mem.author_name}] {mem.content}")
                final_results.append(mem)
                seen_ids.add(mem.id)

        print(f"--- [기억 검색 결과] --- 총 {len(final_results)}개의 고유한 기억 반환")
        return final_results[:n_results]

    # 싱글턴 인스턴스 생성
memory_manager = MemoryManager()