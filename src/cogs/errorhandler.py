import traceback

from discord import Interaction
from discord.app_commands import AppCommandError
from discord.ext import commands

import time

from ..types import Bot

import config
from ..utils import *


class EventCog(commands.Cog, name='Events'):
    def __init__(self, bot: Bot):
        self.bot = bot

    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    def cog_unload(self):
        tree = self.bot.tree
        tree.on_error = self._old_tree_error

    async def on_app_command_error(
            self,
            i9n: Interaction,
            err: AppCommandError
    ):
        tb = "\n".join(traceback.format_exception_only(err))
        await error(i9n, f"""```py
{tb}```""")


async def setup(bot: Bot):
    await bot.add_cog(EventCog(bot))
