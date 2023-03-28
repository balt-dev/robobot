from discord import Interaction


async def error(interaction: Interaction, *args, **kwargs):
    return await respond(interaction, *args, ephemeral=True, **kwargs)


async def respond(interaction: Interaction, *args, **kwargs):
    return await interaction.response.send_message(*args, **kwargs)
