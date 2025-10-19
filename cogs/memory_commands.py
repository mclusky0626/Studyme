from discord.ext import commands
import discord

from memory_system.memory_manager import memory_manager
from memory_system.schemas import MemoryChunk


class MemoryCommands(commands.Cog):
    """기억을 수동으로 관리하기 위한 명령어들을 포함하는 Cog"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="기억해")
    async def remember_this(self, ctx: commands.Context, *, content: str):
        """
        사용자가 지정한 내용을 '중요한 기억'으로 저장합니다.
        사용법: !기억해 내 생일은 12월 25일이야
        """
        if not content:
            await ctx.reply("무엇을 기억해야 할지 알려주세요! (예: `!기억해 내 이름은 홍길동이야`)")
            return

        chunk = MemoryChunk(
            user_id=ctx.author.id,
            author_name=ctx.author.name,
            channel_id=ctx.channel.id,
            content=content,
            is_important=True  # 사용자가 직접 명령했으므로 중요함으로 표시
        )

        await memory_manager.add_new_memory(chunk)

        await ctx.reply(f"✅ 알겠습니다. '{content}' 라고 기억해 둘게요!")

    @commands.command(name="내기억")
    async def show_my_memories(self, ctx: commands.Context):
        """
        봇이 자신에 대해 기억하고 있는 중요한 내용들을 보여줍니다.
        """
        important_memories = memory_manager.vector_store.get_important_memories(user_id=ctx.author.id)

        if not important_memories:
            await ctx.reply("아직 당신에 대해 기억하고 있는 특별한 내용이 없어요.")
            return

        embed = discord.Embed(
            title=f"{ctx.author.name}님에 대한 중요 기억",
            color=discord.Color.blue()
        )

        # 최신순으로 정렬하여 표시
        important_memories.sort(key=lambda m: m.timestamp, reverse=True)

        for mem in important_memories[:10]:  # 최대 10개까지 표시
            embed.add_field(
                name=f"🗓️ {mem.timestamp.strftime('%Y-%m-%d')}",
                value=f"```{mem.content}```",
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryCommands(bot))