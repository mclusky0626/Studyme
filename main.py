import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# .env 파일에서 환경 변수 로드
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class MnemosyneBot(commands.Bot):
    """Mnemosyne 봇의 메인 클래스"""

    def __init__(self):
        # 봇이 사용자의 메시지 내용을 읽을 수 있도록 intents 설정
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        """봇이 성공적으로 로그인했을 때 호출됩니다."""
        print(f'봇이 로그인했습니다: {self.user.name} (ID: {self.user.id})')
        print('------')
        print("이제 봇을 멘션하거나 DM을 보내 대화할 수 있습니다.")
        print("사용 가능한 명령어: !기억해, !내기억")

    async def setup_hook(self):
        """봇이 실행되기 전에 비동기적으로 필요한 설정을 로드합니다."""
        print("Cog 로드를 시작합니다...")
        cogs_to_load = [
            "cogs.chat_listener"

        ]
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                print(f"✅ '{cog}' Cog가 성공적으로 로드되었습니다.")
            except Exception as e:
                print(f"❌ '{cog}' Cog 로드 중 오류 발생: {e}")


async def main():
    """봇을 실행하기 위한 메인 비동기 함수"""
    bot = MnemosyneBot()
    await bot.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("봇을 종료합니다.")