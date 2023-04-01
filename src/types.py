import copy
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from re import Pattern
from typing import Callable, Literal, Any

import asqlite
import numpy as np
from discord.ext import commands

from src import constants
from src.utils import cast


@dataclass
class TileData:
    colors: list[list[int, int] | list[int, int, int]]
    sprites: list[np.ndarray]
    slep_sprites: list[np.ndarray] | None = None
    painted: list[bool | list[int, int] | list[int, int, int]] | None = None


class Database:
    conn: asqlite.Connection
    bot: None
    tiles: dict[str, TileData]
    palettes: dict[str, np.ndarray]
    overlays: dict[str, np.ndarray]

    def __init__(self, bot): ...

    async def connect(self, db: str) -> None: ...

    async def load_tiles(self, *, flush: bool = False) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def create_tables(self) -> None: ...

    async def load_palettes(self) -> None: ...

    async def load_overlays(self) -> None: ...


class Bot(commands.Bot):
    started: datetime
    db: Database
    renderer: None
    variants: list

    def __init__(self, *args, **kwargs) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def on_ready(self) -> None: ...


class Variant(ABC):
    description: str
    signature: list[type]
    syntax: Pattern
    func: Callable
    type: Literal["tile", "sprite", "post"]
    names: list[str]

    def __init__(self, *args: Any | None):
        self.args = args

    @abstractmethod
    def call(self, tile):
        raise NotImplementedError

    def __repr__(self):
        return f"{self.__class__.__name__}({','.join([f'{key}={value}' for key, value in self.__dict__.items()])})"


@dataclass
class TileSkeleton:
    name: str
    variants: list[Variant]
    x: int
    y: int
    z: int

    @classmethod
    def parse(cls, string: str, position: tuple[int, int], z_index: int, possible_variants: list, *, rule: bool = False):
        name, *variants = re.split(r"(?<!\\):", string)
        assert "slab" not in name, "fuck slab hope she fuckign    dies or smtjh"
        if not len(name) or name == "-": return None
        variants: list[str]
        parsed_variants: list[Variant] = []
        for variant in variants:
            # Tried to use a for-else here, but Python disagreed.
            found_variant = False
            for possible_variant in possible_variants:
                if match := re.fullmatch(possible_variant.syntax, variant):
                    parsed_variants.append(possible_variant(
                        *(cast(arg_type, arg) for arg_type, arg in zip(possible_variant.signature, match.groups()))))
                    found_variant = True
                    break
            assert found_variant, f"whar is varinnt `{variant}`??"
        return cls(name, parsed_variants, *position, z_index)


def to_tuple(val: Any) -> tuple:
    val = copy.deepcopy(val)
    try:
        if isinstance(val, str):
            raise TypeError
        for i, entry in enumerate(val):
            val[i] = to_tuple(val[i])
    except TypeError:
        return val
    return tuple(val)


@dataclass
class Tile:
    name: str
    variants: list[Variant]
    x: int
    y: int
    z: int
    colors: list[list[int, int] | list[int, int, int] | str]
    painted: list[list[int, int] | list[int, int, int] | bool]
    sprites: list[np.ndarray] = field(repr=False)
    palette: str = "default"
    slep: bool = False

    @classmethod
    # data is passed by reference
    async def build(cls, skel: TileSkeleton, tile_data: TileData):
        tile_data = copy.deepcopy(tile_data)
        tile = cls(
            skel.name,
            skel.variants,
            skel.x,
            skel.y,
            skel.z,
            tile_data.colors,
            tile_data.painted,
            tile_data.sprites
        )
        for i, variant in enumerate(skel.variants):
            if variant.type == "tile":
                await variant.call(tile)
                del skel.variants[i]
        if tile.slep and tile_data.slep_sprites is not None:
            tile.sprites = tile_data.slep_sprites
        return tile


    def __hash__(self):
        for i in range(len(self.sprites)):
            self.sprites[i].flags.writeable = False
        tile_hash = hash((
            self.name,
            tuple(variant for variant in self.variants if variant.type != "post"),
            to_tuple(self.colors),
            to_tuple(self.painted)
            # Sprites don't actually need to be hashed
        ))
        for i in range(len(self.sprites)):
            self.sprites[i].flags.writeable = True
        return tile_hash


@dataclass
class ProcessedTile:
    name: str
    sprite: np.ndarray = field(repr=False)
    x: int
    y: int
    z: int
    variants: list[Variant]
    scale: list[int, int] = field(default_factory=lambda: [1, 1])
    rotation: float = 0
    palette: str = "default"


@dataclass
class RenderingContext:
    spacing: int = constants.TILE_SIZE
    upscale: int = 2
    palette: str = "default"


class VariantList(list):
    def find(self, name: str) -> Variant | None:
        for variant in self:
            variant: Variant
            if variant.__class__.__name__.lower().startswith(name):
                return variant
        return None

