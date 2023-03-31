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


@dataclass
class TileData:
    colors: list[list[int, int] | list[int, int, int]]
    sprites: list[np.ndarray]
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
    name: str
    description: str
    signature: list[type]
    syntax: Pattern
    func: Callable
    type: Literal["tile", "sprite", "post"]

    @abstractmethod
    def apply(self):
        raise NotImplementedError

@dataclass
class TileSkeleton:
    name: str
    variants: list[Variant]
    x: int
    y: int
    z: int

    @classmethod
    def parse(cls, string: str, position: tuple[int, int], z_index: int, possible_variants: list[Variant]):
        name, *variants = re.split(r"(?<!\\):", string)
        assert "slab" not in name, "fuck slab hope she fuckign    dies or smtjh"
        if not len(name) or name == "-": return None
        variants: list[str]
        for variant in variants:
            do_break = False
            for possible_variant in possible_variants:
                if do_break: break
                print(possible_variant.syntax)
                if match := re.fullmatch(possible_variant.syntax, variant):
                    print(f"\t{match.groups()}")
                    do_break = True

        return cls(name, [], *position, z_index)


def to_tuple(val: Any) -> tuple:
    val = copy.deepcopy(val)
    try:
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
    sprites: list[np.ndarray]
    palette: str = "default"

    @classmethod
    # data is passed by reference
    def build(cls, skel: TileSkeleton, tile_data: TileData):
        return cls(
            skel.name,
            skel.variants,
            skel.x,
            skel.y,
            skel.z,
            tile_data.colors,
            tile_data.painted,
            tile_data.sprites
        )

    def __hash__(self):
        for i in range(len(self.sprites)):
            self.sprites[i].flags.writeable = False
        tile_hash = hash((
            self.name,
            tuple(variant for variant in self.variants if variant.type != "post"),
            self.x, self.y, self.z,
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
    sprite: np.ndarray
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

# class Test: ...
