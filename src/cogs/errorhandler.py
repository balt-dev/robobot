import traceback

import discord
from discord import Interaction, app_commands
from discord.app_commands import AppCommandError
from discord.ext import commands

import time

from ..types import Bot

import config
from ..utils import *


class ErrorCog(commands.Cog, name='Error'):
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
            interaction: Interaction,
            err: AppCommandError
    ):
        try:
            if isinstance(err, app_commands.CommandInvokeError):
                err = err.original
            if isinstance(err, app_commands.CheckFailure):
                return await error(interaction, "! y u tryin to run this?? u not ballt!!")
            if isinstance(err, AssertionError):
                return await error(interaction, f"uh oh!!!! {err.args[0]}")

            tb = "\n`".join(traceback.format_exception(err))
            await error(interaction, f"""```py
    {tb}```""")
        except discord.errors.InteractionResponded:
            # Probably already handled earlier
            traceback.print_exception(err)


async def setup(bot: Bot):
    await bot.add_cog(ErrorCog(bot))
