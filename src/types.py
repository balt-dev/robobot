import re
from dataclasses import dataclass
from datetime import datetime

import asqlite
import numpy as np
from discord.ext import commands


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

    def __init__(self, *args, **kwargs) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def on_ready(self) -> None: ...


@dataclass
class TileSkeleton:
    name: str
    variants: list[str]
    position: tuple[int, int]
    z_index: int

    @classmethod
    def parse(cls, string: str, position: tuple[int, int], z_index: int):
        name, *variants = re.split(r"(?<!\\):", string)
        if not len(name) or name == "-": return None
        return cls(name, variants, position, z_index)


@dataclass
class Tile:
    name: str
    variants: list[str]
    position: tuple[int, int]
    z_index: int
    colors: list[tuple[int, int] | tuple[int, int, int] | str]
    painted: list[tuple[int, int] | tuple[int, int, int] | bool]
    sprites: list[np.ndarray]
    rotation: float = 0

    @classmethod
    # data is passed by reference
    def build(cls, skel: TileSkeleton, data: dict[str, TileData]):
        assert skel.name in data, f"whatt is til `{skel.name}`?? i dunno!!!"
        tile_data = data[skel.name]
        return cls(
            skel.name,
            skel.variants,
            skel.position,
            skel.z_index,
            tile_data.colors,
            tile_data.painted,
            tile_data.sprites
        )
