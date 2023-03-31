import inspect
from re import Pattern
from typing import Literal

from discord.ext.commands import Cog

from src.types import Bot, Variant


class VariantCog(Cog):
    variants: list[Variant] = []

    def __init__(self, bot: Bot):
        bot.variants = self.variants
        self.bot = bot

    def add_variant(self, variant_type: Literal["tile", "sprite", "post"]):
        def inner(func):
            signature = inspect.signature(func)
            params: tuple[inspect.Parameter] = tuple(param for param in signature.parameters.values() if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD)
            patterns = {
                int: r"(-?\d+)",
                float: r"(-?\d*\.?\d+)",
                str: r"(.+)"
            }
            syntax = func.__name__ + "/".join([patterns.get(param.annotation, "") for param in params])
            var_class = type(
                f"{func.__name__.replace('_','').title()}Variant",
                (Variant,),
                {
                    "description": func.__doc__,
                    "signature": [param.annotation for param in params],
                    "syntax": syntax,
                    "call": lambda tile, *args, **kwargs: func(tile, *args, **kwargs),
                    "type": variant_type
                }
            )
            self.bot.variants.append(var_class)
            return func
        return inner


async def setup(bot: Bot):
    cog = VariantCog(bot)

    @cog.add_variant("post")
    async def test(tile, /, foo: str, bar: int, baz: float):
        print(foo, bar, baz)

    await bot.add_cog(cog)
