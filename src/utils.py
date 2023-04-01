import types
from typing import get_args, Any

from discord import Interaction


async def error(interaction: Interaction, *args, **kwargs):
    return await respond(interaction, *args, ephemeral=True, **kwargs)


async def respond(interaction: Interaction, content: str | None, *, edit: bool = False, **kwargs):
    if interaction.response.is_done():
        if edit:
            if "ephemeral" in kwargs: del kwargs["ephemeral"]
            return await (await interaction.original_response()).edit(**kwargs, content=content)
        return await interaction.followup.send(content, **kwargs)
    return await interaction.response.send_message(content, **kwargs)


def cast(t: type, value: Any):
    if isinstance(value, t):
        return value
    if isinstance(t, types.UnionType):
        for cls in get_args(t):
            try:
                return cast(cls, value)
            except (TypeError, ValueError):
                pass
        else:
            raise ValueError(f"Could not cast {value} to {t}")
    if isinstance(value, str) and t == bool:
        return value in ("1", "true", "True")
    return t(value)
