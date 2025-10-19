import os
import discord
from discord.ext import commands
import google.generativeai as genai
import traceback

from memory_system.memory_manager import memory_manager
from memory_system.schemas import MemoryChunk

# Gemini API 설정
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- ✨ 여기가 수정된 부분입니다 ✨ ---
# 최신의 안정적인 모델 이름으로 변경
llm_model = genai.GenerativeModel("gemini-2.5-flash")


# --- ✨ 수정 끝 ✨ ---

class ChatListener(commands.Cog):
    """사용자의 모든 메시지를 듣고 기억 기반의 응답을 생성하는 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # (이하 코드는 이전 디버깅 버전과 동일하게 유지합니다)
        if message.author == self.bot.user or message.content.startswith("!"):
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
                    n_similarity=5
                )

                memory_context = memory_manager.build_context_from_memories(relevant_memories, max_tokens=2000)

                prompt = f"""
                당신은 사용자와 친근하게 대화하는 AI 챗봇 '기억의 조각'입니다. 
                당신은 대화 내용을 기억하고 개인적인 답변을 해줄 수 있습니다.
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

        if ai_response and ai_response.strip():
            new_memory_content = f"사용자 '{message.author.name}'가 '{user_query}'라고 말했고, 나는 '{ai_response}'라고 답했다."
            new_chunk = MemoryChunk(
                user_id=message.author.id,
                author_name=message.author.name,
                channel_id=message.channel.id,
                content=new_memory_content,
                is_important=False
            )
            await memory_manager.add_new_memory(new_chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatListener(bot))