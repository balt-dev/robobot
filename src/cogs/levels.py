import dataclasses
import json
from io import BytesIO
from pathlib import Path

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from src.types import Bot, LevelData, RenderingContext, Tile
from src.utils import respond


class LevelCog(commands.Cog, name="Levels"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    async def lvl(
            self,
            interaction: Interaction,
            *,
            world: str = None,
            name: str = None,
            file: discord.Attachment = None,
            ephemeral: bool = False
    ):
        await interaction.response.defer(thinking=True, ephemeral=ephemeral)
        if file is not None:
            level = json.loads(await file.read())
        else:
            if name in self.bot.db.worlds:
                world, name = self.bot.db.level_names[name]
            else:
                assert world in self.bot.db.worlds, f"wher is `{world}`??"
                assert name in self.bot.db.worlds[world], f"wher is `{name}`??"
            with open(Path("data/bab/officialworlds") / world):
                pass
        level_data = LevelData.from_json(level, self.bot)
        assert level_data is not None, "ur lvl didnt pars!!"
        """
            spacing: int = constants.TILE_SIZE
    upscale: int = 2
    palette: str = "default"
    bg: tuple[int, int, int, int] = (0, 0, 0, 0)
    width: int = 0
    height: int = 0
    rul: bool = False
    """
        print({k: v for k, v in level_data})
        bg = self.bot.db.palettes[level_data.palette][4, 0]
        ctx = RenderingContext(
            upscale=1,
            palette=level_data.palette,
            bg=bg,
            width=level_data.width,
            height=level_data.height
        )
        tiles = await Tile.build_tiles(level_data.tiles, ctx, self.bot)
        tiles = await self.bot.renderer.process(tiles, ctx)
        with BytesIO() as buf:
            await self.bot.renderer.render(tiles, buf, ctx)
            await respond(interaction, content=f"""> _`{level_data.name}` by `{level_data.author}`_""", file=discord.File(buf, filename=f"{level_data.name}.png"))
        return


async def setup(bot: Bot):
    await bot.add_cog(LevelCog(bot))
