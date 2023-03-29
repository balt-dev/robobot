import asyncio
import sys
from datetime import datetime

from pathlib import Path

import discord
from discord.ext import commands

import auth
import config
from src.db import Database
from src.types import Bot

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.started = datetime.utcnow()
        self.db = Database(self)
        super().__init__(*args, **kwargs)

        async def gather_cogs():
            cogs = [
                ".".join(Path(p).stem for p in path.parts)
                for path in Path(".").glob("src/cogs/*.py")
                if not path.stem.startswith("__")
            ]
            await asyncio.gather(*(self.load_extension(cog, package="bot") for cog in cogs))

        asyncio.run(gather_cogs())

    async def close(self, code: int = 0) -> None:
        await self.change_presence(status=discord.Status.offline)
        await self.db.close()
        await super().close()
        sys.exit(code)

    async def on_ready(self) -> None:
        # await self.tree.sync()
        print("Connecting...")
        path = Path("./bot.db").resolve()
        await self.db.connect(path)
        print(f"Logged in as {self.user}!")
        await self.change_presence(status=discord.Status.online)

bot = Bot(
    # Prefixes
    [],
    activity=discord.Game(name=config.activity),
    description=config.description,
    # Never mention roles, @everyone or @here
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
    intents=discord.Intents(),
    # Disable the member cache
    member_cache_flags=discord.MemberCacheFlags.none(),
    # Disable the message cache
    max_messages=None,
    # Don't chunk guilds
    chunk_guilds_at_startup=False,
)

discord.utils.setup_logging()

try:
    bot.run(auth.token, log_handler=None)
finally:
    asyncio.run(bot.close())
