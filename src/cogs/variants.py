import inspect
import types
import typing
from re import Pattern
from typing import Literal

import cv2
import numpy as np
from discord.ext.commands import Cog

from src.types import Bot, Variant, VariantList, ProcessedTile, Tile


# This is a whole ton of metaclass shenanigans.

class VariantCog(Cog):
    def __init__(self, bot: Bot):
        bot.variants: VariantList[Variant] = VariantList()
        self.bot = bot

    async def call(self, var_self, tile):
        return await var_self.__class__.func(tile, *var_self.args)

    def get_pattern(self, annotations: list[type]):
        type_patterns: dict[type, str] = {
            int: r"(-?\d+)",
            float: r"(-?\d*\.?\d+)",
            str: r"(.+?)",
            bool: r"(true|false)"
        }
        out = []
        delimiter = "/"
        optional = False
        for i, annotation in enumerate(annotations):
            if isinstance(annotation, types.UnionType):
                patterns = []
                for cls in typing.get_args(annotation):
                    if cls is types.NoneType:
                        if not optional:
                            optional = True
                            out = ["/".join(out)]
                            delimiter = "/?"
                        continue
                    patterns.append(rf"(?:{self.get_pattern([cls])})")
                out.append(f"(?:{'|'.join(patterns)}){'?' if optional else ''}")
            else:
                out.append(type_patterns.get(annotation, ""))
        return delimiter.join(out)

    def add_variant(self, variant_type: Literal["tile", "sprite", "post"], *aliases: str):
        def inner(func):
            signature = inspect.signature(func)
            params: tuple[inspect.Parameter] = tuple(param for param in signature.parameters.values() if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD)
            signature: list[type] = [param.annotation for param in params]
            names: list[str] = [func.__name__, *aliases]
            syntax = rf"(?:{'|'.join(names)})" + self.get_pattern(signature)
            assert func.__doc__ is not None, f"wher doc for {func.__name__}?!?!1?/?"
            var_class = type(
                f"{func.__name__.replace('_','').title()}Variant",
                (Variant,),
                {
                    "description": func.__doc__,
                    "syntax": syntax,
                    "signature": signature,
                    "call": lambda var_self, tile: self.call(var_self, tile),
                    "func": func,
                    "type": variant_type,
                    "aliases": names
                }
            )
            self.bot.variants.append(var_class)
            return func
        return inner


async def setup(bot: Bot):
    cog = VariantCog(bot)

    @cog.add_variant("tile", "")
    async def color(tile, /, r_x: int, g_y: int, b: int | None = None, index: int | None = None):
        """Applies a color to a tile, or a color layer of one.
        `(x: int, y: int, _, index: int) / (r: int, g: int, b: int, index: int)`"""
        if index is not None:
            assert index in range(len(tile.colors)), f"til `{tile.name}` dont hav `{index}` many colr layrs!!"
            tile.colors[index] = tuple(v for v in (r_x, g_y, b) if v is not None)
        else:
            for i in range(len(tile.colors)):
                tile.colors[i] = tuple(v for v in (r_x, g_y, b) if v is not None)

    @cog.add_variant("tile", "o!")
    async def overlay(tile, /, name: str, index: int | None = None, force: bool | None = None):
        """Applies an overlay to a tile, or a color layer of one.
        `(name: str, index: Optional[int], force: Optional[bool] = False)`"""
        assert name in bot.db.overlays, f"not seein ovrlay `{name}` anywher...."
        if force is None: force = False
        if index is not None:
            assert index in range(len(tile.colors)), f"til `{tile.name}` dont hav `{index}` many colr layrs!!"
            tile.colors[index] = name
        else:
            for i in range(len(tile.colors)):
                if tile.painted[i] or force:
                    if isinstance(tile.painted[i], bool) or force:
                        tile.colors[i] = name
                    else:
                        tile.colors[i] = tile.painted[i]

    @cog.add_variant("post", "rot")
    async def rotate(tile, /, angle: float):
        """Rotates a tile.
        `(angle: float)`"""
        tile: ProcessedTile
        tile.rotation = angle

    @cog.add_variant("sprite")
    async def flip(tile, /, axis: str):
        """Flips a tile along an axis.
        `(axis: ("x","y"))`"""
        assert axis in ('x', 'y'), f"bad varint proprtie `{axis}`!!"
        slice_dict = {"x": (slice(None), slice(None, None, -1)), "y": (slice(None, None, -1))}
        tile: Tile
        for i, sprite in enumerate(tile.sprites):
            tile.sprites[i] = sprite[slice_dict[axis]]


    @cog.add_variant("post")
    async def scale(tile, /, x: float, y: float | None = None):
        """Scales a tile.
        `(scale: float) / (x: float, y: float)`"""
        tile: ProcessedTile
        if y is None:
            y = x
        tile.scale[0] = x
        tile.scale[1] = y

    @cog.add_variant("post", "disp")
    async def displace(tile, /, x: float, y: float):
        """Offsets a tile by a set amount of tiles.
        `(x: float, y: float)`"""
        tile.x += x
        tile.y += y

    @cog.add_variant("post")
    async def bump(tile, /, z_index: float):
        """Sets a tile's depth. The lower, the more tiles will be drawn over it.
        `(z: float)`"""
        tile.z = z_index

    @cog.add_variant("sprite")
    async def blank(tile, /):
        """Sets a tile to completely blank and removes all but one color layer."""
        mask = np.zeros(np.amax([sprite.shape[:2] for sprite in tile.sprites], axis=0), dtype=bool)
        for sprite in tile.sprites:
            bounds = (
                slice(int((mask.shape[0] - sprite.shape[0]) // 2), int(((mask.shape[0] + sprite.shape[0]) // 2))),
                slice(int((mask.shape[1] - sprite.shape[1]) // 2), int(((mask.shape[1] + sprite.shape[1]) // 2)))
            )
            mask[bounds] |= sprite[..., 3] > 0
        tile.sprites = [np.dstack((mask, mask, mask, mask)).astype(np.uint8) * 255]

    @cog.add_variant("sprite")
    async def outline(tile, /, edges: bool | None = None):
        """Outlines the tile.
        `(edges: Optional[bool] = True)`"""
        if edges is None: edges = True
        mask = np.zeros(np.amax([sprite.shape[:2] for sprite in tile.sprites], axis=0), dtype=bool)
        for sprite in tile.sprites:
            bounds = (
                slice(int((mask.shape[0] - sprite.shape[0]) // 2), int(((mask.shape[0] + sprite.shape[0]) // 2))),
                slice(int((mask.shape[1] - sprite.shape[1]) // 2), int(((mask.shape[1] + sprite.shape[1]) // 2)))
            )
            mask[bounds] |= sprite[..., 3] > 0
        edges = int(edges)
        kernel = np.array((
            (edges, 1, edges),
            (    1, 0, 1    ),
            (edges, 1, edges)
        ), dtype=float)
        for i, sprite in enumerate(tile.sprites):
            filtered_sprite = cv2.filter2D(src=sprite, ddepth=-1, kernel=kernel)
            filtered_sprite = np.clip(filtered_sprite, 0, 255)
            filtered_sprite[mask, 3] = 0
            tile.sprites[i] = filtered_sprite

    @cog.add_variant("tile", "p!")
    async def palette(tile, /, pal: str):
        """Sets the palette of a tile.
        `(pal: str)`"""
        assert pal in bot.db.palettes, f"not seein palet `{pal}` anywher...."
        tile.palette = pal

    @cog.add_variant("tile", "s")
    async def slep(tile, /):
        """Makes the tile fall asleep, if it can."""
        tile.slep = True

    @cog.add_variant("sprite")
    async def crop(tile, /, x: int, y: int, u: int, v: int):
        """Crops the tile to a box.
        `(x: int, y: int, u: int, v: int)`"""
        for i, sprite in enumerate(tile.sprites):
            try:
                tile.sprites[i] = sprite[y:v, x:u]
            except IndexError:
                raise AssertionError(f"bad varint proprtie `{x, y, u, v}`!!")



    await bot.add_cog(cog)
