from discord import Interaction


async def error(i9n: Interaction, *args, **kwargs):
    return await respond(i9n, *args, ephemeral=True, **kwargs)


async def respond(i9n: Interaction, *args, **kwargs):
    return await i9n.response.send_message(*args, **kwargs)
