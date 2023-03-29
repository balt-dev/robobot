from discord.ext import commands

from discord import app_commands, Interaction
from discord.app_commands import Choice

from src.types import Bot


class GlobalCog(commands.Cog, name="Global"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command()
    async def til(self, interaction: Interaction, *, grid: str, rul: bool = False, ephemeral: bool = False):
        await self.render_tiles(interaction, grid, rule=rul)

    async def parse_tiles(self, grid: str, rule: bool = False):
        ...

    async def render_tiles(self, interaction: Interaction, grid: str, rule: bool = False, ephemeral: bool = False):
        # TODO: REMEMBER TO re.split(r"(?<!\\) ") INSTEAD OF .split(" ") AND SUCH
        # TODO: TILE RENDERING AND SPLITTING INTO A GRID
        await interaction.response.defer(thinking=True, ephemeral=True)
        tiles = await self.parse_tiles(grid, rule=rule)
        await interaction.followup.send(str(tiles))


async def setup(bot: Bot):
    await bot.add_cog(GlobalCog(bot))
