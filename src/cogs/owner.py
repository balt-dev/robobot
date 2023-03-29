import asyncio
import json
import os
import re
import shutil
import struct
import time
import traceback
import warnings
from contextlib import redirect_stdout, redirect_stderr
from functools import reduce
from io import BytesIO, StringIO
from pathlib import Path
import ast


import discord
from discord.ext import commands

from discord import app_commands, Interaction, ui
from discord.app_commands import Choice, Group, AppCommandError
from discord.ext.commands import ExtensionNotLoaded

from src.types import Bot, TileData
from src.utils import *

# Imports for /owner py, in case they're needed
from PIL import Image
import numpy as np

import ast


class OwnerCog(commands.GroupCog, group_name="owner", group_description="Owner-only commands."):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def interaction_check(self, interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)

    @app_commands.command()
    async def reload(self, interaction: Interaction):

        async def try_reload(cog):
            try:
                return await self.bot.reload_extension(cog, package="bot")
            except ExtensionNotLoaded:
                return await self.bot.load_extension(cog, package="bot")

        async def gather_cogs():
            cogs = [
                ".".join(Path(p).stem for p in path.parts)
                for path in Path(".").glob("src/cogs/*.py")
                if not path.stem.startswith("__")
            ]
            await asyncio.gather(*(try_reload(cog) for cog in cogs))

        await gather_cogs()
        await respond(interaction, "cogs been spunn!", ephemeral=True)

    load_group = Group(name="load", description="lod thinggs!!!")

    @load_group.command()
    async def tiles(self, interaction: Interaction, flush: bool = False):
        tiles_loaded = 0
        await interaction.response.defer(ephemeral=True, thinking=True)
        if flush:
            async with self.bot.db.conn.cursor() as cur:
                await cur.execute("DELETE FROM tiles")
            start = time.perf_counter()
            for path in Path("data/bab/assets/tiles").glob("*/*.json"):
                with open(path, "r") as f:
                    tiles = json.load(f)
                for tile in tiles:
                    # Create a linked list of sprites
                    with BytesIO() as buf:
                        for i, sprite_path in enumerate(tile["sprite"]):
                            sprite_path: str
                            try:
                                with open((Path("data/bab/assets/sprites") / sprite_path).with_suffix(".png"), "rb") as f:
                                    f.seek(0, os.SEEK_END)
                                    buf.write(struct.pack("<L", f.tell()))
                                    f.seek(0)
                                    buf.write(f.read())
                            except FileNotFoundError:
                                warnings.warn(f"Can't find sprite {sprite_path}")
                        sprites = buf.getvalue()
                    col = " ".join(",".join(str(n) for n in col) for col in tile["color"])
                    painted = " ".join([
                        (str(int(paint)) if type(paint) is bool else ",".join(str(n) for n in paint))
                        for paint in tile["painted"]
                    ]) if "painted" in tile else None
                    async with self.bot.db.conn.cursor() as cur:
                        await cur.execute("""
                            INSERT OR REPLACE INTO tiles VALUES (?, ?, ?, ?)
                        """, tile["name"], col, sprites, painted)
                    tiles_loaded += 1
                    if time.perf_counter() - start >= 1:
                        start = time.perf_counter()
                        await respond(interaction, f"`{tiles_loaded}` tils loded", ephemeral=True, edit=True)
        await self.bot.db.load_tiles(flush=flush)
        return await respond(interaction, f"tils loded!!", ephemeral=True, edit=True)

    @load_group.command()
    async def palettes(self, interaction: Interaction):
        shutil.copytree("data/bab/assets/palettes", "data/palettes", dirs_exist_ok=True)
        return await respond(interaction, "copid pallets", ephemeral=True)

    @app_commands.command()
    async def sync(self, interaction: Interaction, everywhere: bool = False):
        await self.bot.tree.sync(guild=None if everywhere else interaction.guild)
        await respond(interaction, "cyncd", ephemeral=True)

    @app_commands.command()
    async def kill(self, interaction: Interaction):
        await respond(interaction, "A", ephemeral=True)
        await self.bot.close(0)

    @app_commands.command()
    async def restart(self, interaction: Interaction):
        await respond(interaction, "brb", ephemeral=True)
        await self.bot.close(1)

    @app_commands.command()
    async def py(self, interaction: Interaction):
        class PyModal(ui.Modal, title="Python"):
            query = ui.TextInput(label="Program", style=discord.TextStyle.paragraph)

            async def on_submit(modal, intr: Interaction) -> None:
                buf = StringIO()
                query = re.sub(r"```(?:py(?:thon)?)?", "", modal.query.value)
                with redirect_stdout(buf):
                    with redirect_stderr(buf):
                        try:
                            exec(query, globals(), {"bot": self.bot, "interaction": intr, "run": lambda f: self.bot.loop.create_task(f)})
                        except Exception:
                            traceback.print_exc()
                await respond(intr, f"```py\n{buf.getvalue()[:1989]}\n```", ephemeral=True)
        return await interaction.response.send_modal(PyModal())

async def setup(bot: Bot):
    await bot.add_cog(OwnerCog(bot))
