import asyncio
import json
import shutil
from functools import reduce
from pathlib import Path

from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice, Group, AppCommandError

from src.types import Bot
from src.utils import *


class OwnerCog(commands.GroupCog, group_name="owner", group_description="Owner-only commands."):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def interaction_check(self, interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)

    @app_commands.command()
    async def reload(self, interaction: Interaction):
        async def gather_cogs():
            cogs = [
                ".".join(Path(p).stem for p in path.parts)
                for path in Path(".").glob("src/cogs/*.py")
                if not path.stem.startswith("__")
            ]
            await asyncio.gather(*(self.bot.reload_extension(cog, package="bot") for cog in cogs))

        await gather_cogs()
        await interaction.response.send_message("Reloaded cogs.", ephemeral=True)

    load_group = Group(name="load", description="Loading various assets.")

    @load_group.command()
    async def tiles(self, interaction: Interaction, flush: bool = False):
        tiles_loaded = 0
        await interaction.response.defer(ephemeral=True, thinking=True)
        if flush:
            async with self.bot.db.conn.cursor() as cur:
                await cur.execute("DELETE FROM tiles")
        for path in Path("data/bab/assets/tiles").glob("*/*.json"):
            with open(path, "r") as f:
                tiles = json.load(f)
                for tile in tiles:
                    string_color = " ".join(",".join(str(part) for part in color) for color in tile["color"])
                    print(tile.get("painted", "Not painted"))
                    string_painted = "|".join(
                        str(int(part)) if type(part) == bool else str(part)
                        for part in tile["painted"]
                    ) if "painted" in tile else None
                    print(repr(string_painted))
                    async with self.bot.db.conn.cursor() as cur:
                        await cur.execute(
                            "INSERT OR IGNORE INTO tiles VALUES (?, ?, ?, ?, ?);",
                            tile["name"], string_color,
                            ",".join(tile["sprite"]),
                            tile.get("layer", None),
                            string_painted
                        )
                    tiles_loaded += 1
        return await interaction.followup.send(content=f"Done. Loaded `{tiles_loaded}` tiles.", ephemeral=True)

    @load_group.command()
    async def palettes(self, interaction: Interaction):
        shutil.copytree("data/bab/assets/palettes", "data/palettes", dirs_exist_ok=True)
        return await interaction.response.send_message("Copied palettes.", ephemeral=True)

    @app_commands.command()
    async def sync(self, interaction: Interaction, everywhere: bool = False):
        await self.bot.tree.sync(guild=None if everywhere else interaction.guild)
        await interaction.response.send_message("Synced.", ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(OwnerCog(bot))
