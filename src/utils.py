from discord import Interaction


async def error(interaction: Interaction, *args, **kwargs):
    return await respond(interaction, *args, ephemeral=True, **kwargs)


async def respond(interaction: Interaction, content: str, *, edit: bool = False, **kwargs):
    if interaction.response.is_done():
        if edit:
            if "ephemeral" in kwargs: del kwargs["ephemeral"]
            return await (await interaction.original_response()).edit(**kwargs, content=content)
        return await interaction.followup.send(content, **kwargs)
    return await interaction.response.send_message(content, **kwargs)
