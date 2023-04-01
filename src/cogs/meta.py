import asyncio
import re
from io import BytesIO
from pathlib import Path
from typing import Literal

import discord
from PIL import Image
from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src import constants
from src.types import Bot, TileSkeleton, RenderingContext, Tile
from src.utils import respond

palettes = []


class Paginated(discord.ui.View):
    def __init__(self, interaction: Interaction, *pages: discord.Embed):
        self.pages = pages
        self.index = 0
        super().__init__()

    async def update_page(self, interaction: Interaction):
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
    async def left_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.pages)
        await self.update_page(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
    async def right_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.pages)
        await self.update_page(interaction)


class MetaCog(commands.Cog, name="Meta"):
    def __init__(self, bot: Bot):
        global palettes
        self.bot = bot
        palettes = list(bot.db.palettes.keys())

    @app_commands.command()
    async def palette(self, interaction: Interaction, name: str, x: int | None = None, y: int | None = None):
        assert name in self.bot.db.palettes, f"idk where `{name}` is ask ur gps"
        assert not (x is None) ^ (y is None), "cant get a colr with oly 1 indx!!"
        palette = self.bot.db.palettes[name]
        if x is None:
            with BytesIO() as buf:
                Image.fromarray(palette.repeat(constants.TILE_SIZE, axis=0).repeat(constants.TILE_SIZE, axis=1)).save(buf, format="PNG")
                buf.seek(0)
                await respond(interaction, content=None, file=discord.File(buf, filename=f"{name}.png"), ephemeral=True)
        else:
            try:
                r, g, b, a = palette[y, x]
            except KeyError:
                raise AssertionError("thers not a colr thre!!")
            rgba = int(r << 24 | g << 16 | b << 8 | a)  # np.int64 -> int
            embed = discord.Embed(
                color=discord.Color(rgba >> 8),
                title=f"{x}, {y}: #{hex(rgba)[2:].upper():06}"
            )
            embed.set_footer(text=name)
            await respond(interaction, content=None, embed=embed, ephemeral=True)

    # Name can't be a Choice[str] because there's a 25-option limit
    @palette.autocomplete("name")
    async def palette_autocomplete(self, interaction: Interaction, current: str):
        new_pals = [pal for pal in palettes if pal.startswith(current)]
        return [Choice(name=name, value=name) for name in new_pals[:25]]

    @app_commands.command()
    async def about(self, interaction: Interaction, ephemeral: bool = True):
        embed = discord.Embed(
            title="About",
            color=discord.Color(0xE62169),  # I'm kinda immature :P
            description="""**robobot is jank** - a ground-up rewrite of ROBOT IS CHILL, specialized for bab be u
This was all made in the span of 5 days, and honestly slightly rushed. I worked on this right up until midnight.
This bot will probably stay up for as long as people care, so if you like it, use it!
Also, this was partially made to test how RIC would feel with slash commands.
Tell me what you think!

_Happy April Fool's Day, -balt_"""
        )
        await respond(interaction, content=None, embed=embed, ephemeral=ephemeral)

    @app_commands.command()
    async def variants(self, interaction: Interaction, variant: str | None = None):
        embeds = []
        names = [variant.__name__.removesuffix("Variant") for variant in self.bot.variants]
        for v in self.bot.variants:
            embeds.append(discord.Embed(
                title=v.__name__.removesuffix("Variant"),
                color=discord.Color(0xE62169),
                description=f"> `{', '.join(v.aliases)}`\n{v.description}"
            ))
        if variant is not None:
            assert variant in names, f"whar is varinnt `{variant}`??"
            return await respond(interaction, content=None, embed=embeds[names.index(variant)], ephemeral=True)
        else:
            return await respond(interaction, content=None, view=Paginated(interaction, *embeds), embed=embeds[0], ephemeral=True)

    @variants.autocomplete("variant")
    async def autocomplete_variant(self, interaction: Interaction, current: str):
        names = [variant.__name__.removesuffix("Variant") for variant in self.bot.variants]
        names = [name for name in names if name.lower().startswith(current.lower())]
        return [Choice(name=name, value=name) for name in names[:25]]


async def setup(bot: Bot):
    await bot.add_cog(MetaCog(bot))
