import asyncio
import glob
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands

class Context(commands.Context):

    async def error(self, *args, **kwargs):
        await self.message.add_reaction("\u26a0\ufe0f")
        return await self.reply(*args, **kwargs)

    async def reply(self, *args, **kwargs):
        kwargs['reference'] = self.message
        return await super().send(*args, **kwargs)

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.started = datetime.utcnow()
        self.db = Database(self)
        super().init(*args, **kwargs)

        async def gather_cogs():
            cogs = [".".join(Path(p).stem for p in path.parts) for path in Path(".").glob("src/cogs/*.py")]
            await asyncio.gather(*(self.load_extension(cog, package="bot") for cog in cogs))

        asyncio.run(gather_cogs())

    async def get_context(self, message: discord.Message, **kwargs) -> Context:
        return await super().get_context(message, cls=Context)

    async def close(self) -> None:
        await self.change_presence(status=discord.Status.offline)
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        await self.db.connect(Path("./bot.db").resolve())
        print(f"Logged in as {self.user}!")
        await self.change_presence(status=discord.Status.online)
