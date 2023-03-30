import re
from dataclasses import dataclass
from datetime import datetime

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

    def __init__(self, bot): ...

    async def connect(self, db: str) -> None: ...

    async def load_tiles(self, *, flush: bool = False) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def create_tables(self) -> None: ...



class Bot(commands.Bot):
    started: datetime
    db: Database
    renderer: None

    def __init__(self, *args, **kwargs) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def on_ready(self) -> None: ...


@dataclass
class TileSkeleton:
    name: str
    variants: list[str]
    x: int
    y: int
    z: int

    @classmethod
    def parse(cls, string: str, position: tuple[int, int], z_index: int):
        name, *variants = re.split(r"(?<!\\):", string)
        if not len(name) or name == "-": return None
        return cls(name, variants, *position, z_index)


@dataclass
class Tile:
    name: str
    variants: list[str]
    x: int
    y: int
    z: int
    colors: list[list[int, int] | list[int, int, int] | str]
    painted: list[list[int, int] | list[int, int, int] | bool]
    sprites: list[np.ndarray]
    rotation: float = 0

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

@dataclass
class RenderingContext:
    spacing: int = constants.TILE_SIZE


#class Test: ...