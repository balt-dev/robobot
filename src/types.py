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
    started: datetime
    db = Database

    def __init__(self, *args, **kwargs) -> None: ...

    async def close(self) -> None: ...

    async def on_ready(self) -> None: ...