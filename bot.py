import asyncio

from pathlib import Path

import discord
from discord.ext import commands

import auth
import config
from src.types import Bot

bot = Bot(
    # Prefixes
    [],
    # Other behavior parameters
    activity=discord.Game(name=config.activity),
    description=config.description,
    # Never mention roles, @everyone or @here
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
    # Only receive message and reaction events
    intents=discord.Intents(messages=True, reactions=True, message_content=True),
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
