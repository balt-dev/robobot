import asyncio
import glob
import types
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import discord
from discord.ext import commands

from src.db import Database

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

    async def close(self) -> None:
        await self.change_presence(status=discord.Status.offline)
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        print("Connecting...")
        path = Path("./bot.db").resolve()
        print(path)
        await self.db.connect(path)
        print(f"Logged in as {self.user}!")
        await self.change_presence(status=discord.Status.online)