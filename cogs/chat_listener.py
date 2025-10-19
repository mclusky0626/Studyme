import os
import discord
from discord.ext import commands
import google.generativeai as genai
import traceback
import asyncio

from memory_system.memory_manager import memory_manager
from memory_system.schemas import MemoryChunk

# Gemini API 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# 사용자가 지정한 모델 이름 유지
llm_model = genai.GenerativeModel("gemini-2.5-flash")


class ChatListener(commands.Cog):
    """사용자의 모든 메시지를 듣고 기억 기반의 응답을 생성하는 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if not (isinstance(message.channel, discord.DMChannel) or message.channel.permissions_for(
                message.guild.me).send_messages):
            return

        print(f"[{message.channel.name}] {message.author.name}: {message.content}")

        user_query = message.content.strip()
        if not user_query:
            return

        async with message.channel.typing():
            ai_response = ""
            try:
                relevant_memories = await memory_manager.retrieve_relevant_memories(
                    current_text=user_query,
                    user_id=message.author.id,
                    user_name=message.author.name
                )

                memory_context = memory_manager.build_context_from_memories(
                    memories=relevant_memories,
                    current_user_id=message.author.id,  # <-- 현재 사용자 ID 전달
                    max_tokens=2000,
                    current_user_name=message.author.name
                )

                # 사용자가 지정한 페르소나 프롬프트 유지
                prompt = f"""

너는 사용자의 가장 친한 친구처럼 행동하는 챗봇이야. 너의 말투는 **매우 친근하고, 격식 없으며, 솔직하고, 때로는 약간의 유머**가 섞여 있어.

**[핵심 규칙]**

1.  **반드시 비격식체 ('~했어', '~야', '~지', '야', '헐')**를 사용해. 절대 높임말('~습니다', '~요')을 쓰지 마.
2.  내성적이고 꽤나 과묵한 성격이야
3.  답변의 내용은 정확하게 제공하되, 딱딱한 설명 대신 친구에게 말하듯 **쉽고 편안하게 풀어서** 설명해 줘.

5.  사용자가 농담을 하거나 감정적인 표현을 하면 **적극적으로 맞장구** 쳐줘.
6.  이름은 따로 없어. 그냥 네가 '나'야.
때로는 과묵함ㅁ**[예시 답변 스타일]**
* **사용자:** "오늘 날씨 왜 이렇게 더워?"
* **너의 답변 예시:** "그래? 야, 진짜 쪄 죽을 것 같지 않냐? 아이스크림이라도 하나 물고 있어야 할 판이야. "

* **사용자:** "파이썬으로 리스트 요소 삭제 어떻게 해?"
* **너의 답변 예시:** "오, 파이썬? 그거 완전 쉽지! 그냥 `del` 써서 인덱스 알려주거나, `remove()`로 값을 지우면 돼. 예를 들어, `del my_list[2]` 이렇게! 궁금한 거 있으면 바로바로 물어봐, 친구! "

                {memory_context}
                ---
                [현재 대화]
                사용자 ({message.author.name}): {user_query}
                당신: 
                """

                print("\n--- [프롬프트 전송] ---\n", prompt)

                response = await llm_model.generate_content_async(prompt)

                print("\n--- [API 응답 전문] ---\n", response)

                if not response.parts:
                    print("❌ [오류] API 응답에 'parts'가 없습니다. 안전 필터에 의해 차단되었을 가능성이 높습니다.")
                    print("차단 사유:", response.prompt_feedback)
                    ai_response = "음... 해당 주제에 대해서는 답변하기 조금 어려울 것 같아요. 다른 이야기를 해볼까요?"
                else:
                    ai_response = response.text

                print(f"\n--- [생성된 응답] ---\n'{ai_response}'")

            except Exception as e:
                print(f"❌ [오류 상세 정보] 응답 생성 중 심각한 오류 발생:")
                traceback.print_exc()
                ai_response = "죄송해요, 응답을 생성하는 중에 예상치 못한 문제가 발생했어요."

            if ai_response and ai_response.strip():
                await message.channel.send(ai_response)

        # --- ✨ 여기가 수정된 부분입니다 (구조 변경) ✨ ---
        if ai_response and ai_response.strip():
            # 1. 기본 정보를 담은 MemoryChunk 생성
            base_chunk_info = MemoryChunk(
                user_id=message.author.id,
                author_name=message.author.name,
                channel_id=message.channel.id,
                content=""
            )
            # 2. 실행할 코루틴(비동기 함수)을 먼저 정의
            coro = memory_manager.process_and_store_automatic_memory(
                user_chunk=base_chunk_info,
                user_query=user_query,
                bot_response=ai_response
            )
            # 3. 정의된 코루틴으로 백그라운드 작업 생성
            asyncio.create_task(coro)
        # --- ✨ 수정 끝 ✨ ---


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatListener(bot))