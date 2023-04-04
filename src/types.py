import base64
import copy
import dataclasses
import re
import warnings
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from re import Pattern
from typing import Callable, Literal, Any, Self
import json

import asqlite
import numpy as np
from discord.ext import commands
import luaparser.ast as lua

from src import constants
from src.utils import cast


@dataclass
class TileData:
    colors: list[list[int, int] | list[int, int, int]]
    sprites: list[np.ndarray] = field(repr=False)
    slep_sprites: list[np.ndarray] | None = field(default=None, repr=False)
    painted: list[bool | list[int, int] | list[int, int, int]] | None = None
    rotate: bool = True
    layer: int | None = None


class Database:
    conn: asqlite.Connection
    bot: None
    tiles: dict[str, TileData]
    palettes: dict[str, np.ndarray]
    overlays: dict[str, np.ndarray]
    worlds: dict[str, dict[str, "LevelData"]]
    level_names: dict[str, tuple[str, str]]

    def __init__(self, bot): ...

    async def connect(self, db: str) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def create_tables(self) -> None: ...

    async def load_tiles(self, *, flush: bool = False) -> None: ...

    async def load_palettes(self) -> None: ...

    async def load_overlays(self) -> None: ...

    async def load_worlds(self) -> None: ...



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


class VariantList(list):
    def find(self, name: str) -> Variant | None:
        for variant in self:
            variant: Variant
            if variant.__name__.lower().startswith(name.lower()):
                return variant
        return None


class Bot(commands.Bot):
    started: datetime
    db: Database
    renderer: None
    variants: VariantList

    def __init__(self, *args, **kwargs) -> None: ...

    async def close(self, code: int = 0) -> None: ...

    async def on_ready(self) -> None: ...


@dataclass()
class TileSkeleton:
    name: str
    variants: list[Variant]
    x: int
    y: int
    z: int | None = None
    color: tuple[int, int] | None = None

    @classmethod
    def parse(cls, string: str, position: tuple[int, int], possible_variants: list, color: tuple[int, int] = None, layer: int = None):
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
        return cls(name, parsed_variants, *position, layer, color)

    def __iter__(self):
        # Made for level saving, doesn't need to work elsewhere
        for key in dir(self):
            if not key.startswith("__") and key not in ("z", "variants"):
                yield key, getattr(self, key)


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
            skel.z if skel.z is not None else tile_data.layer if tile_data.layer is not None else 0 ,
            [skel.color for _ in tile_data.painted] if skel.color is not None else tile_data.colors,
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

    @staticmethod
    async def build_tiles(raw_tiles: list, ctx, bot) -> list:
        tiles = []
        for skel in raw_tiles:
            if skel is not None:
                skel.name = re.sub(r"\\(.)", r"\1", skel.name)
                if ctx.rul:
                    if skel.name.startswith("til_"):
                        skel.name = skel.name[4:]
                    else:
                        skel.name = f"txt_{skel.name}"
                assert skel.name in bot.db.tiles, f"wat is `{skel.name}`????"
                tile = await Tile.build(skel, bot.db.tiles[skel.name])
                tile.palette = ctx.palette
                tiles.append(tile)
        return tiles


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
    bg: tuple[int, int, int, int] = (0, 0, 0, 0)
    width: int = 0
    height: int = 0
    rul: bool = False


@dataclass
class LevelData:
    width: int = None
    height: int = None
    name: str = None
    palette: str = None
    background: str | None = None
    author: str = None
    tiles: list[TileSkeleton] = None

    def __iter__(self):
        out = copy.deepcopy(self.__dict__)
        out["tiles"] = []
        for tile in self.tiles:
            t = copy.deepcopy(tile)
            if hasattr(t, "variants"):
                if len(t.variants):
                    var = t.variants[0]
                    t.rotation = var.args[0] // 45
                del t.variants
                d = t.__dict__
                del d["z"]
                out["tiles"].append(d)
        for key, value in out.items():
            yield key, value

    @classmethod
    def from_json(cls, obj: dict[str, Any], bot: Bot) -> Self:
        # bot is passed because it's the easiest way to get it here
        try:
            out = cls(
                width=obj["width"],
                height=obj["height"],
                name=obj["name"],
                palette=obj["palette"],
                background=obj["background_sprite"] if obj.get("background_sprite", None) else None,
                author=obj["author"]
            )

            # Parse Lua code to a map

            lua_code = zlib.decompress(base64.b64decode(obj["map"])).decode("utf-8")
            lua_ast = lua.parse(lua_code)

            for node in lua_ast.body.body[0].body.body:
                if isinstance(node, lua.Return):
                    return_node = node
                    break
            else:
                raise AssertionError("Could not find return statement")

            for node in lua.walk(lua_ast):
                node: lua.Node
                if isinstance(node, lua.LocalAssign):
                    node: lua.LocalAssign
                    if node.targets[0].id == return_node.values[0].id:
                        map_data: lua.Node = node.values[0]
                        break
            else:
                raise AssertionError("Could not find assignment")

            def to_python(value) -> Any:
                if isinstance(value, lua.String):
                    return value.s
                elif isinstance(value, lua.Name):
                    return value.id
                elif isinstance(value, lua.Table):
                    if len(value.fields) and all(isinstance(f.key, lua.Number) for f in value.fields):
                        nums = [f.key.n for f in value.fields]
                        if nums[0] == 1 and nums == list(range(min(nums), max(nums)+1)):
                            return [to_python(f.value) for f in value.fields]
                    return {to_python(f.key): to_python(f.value) for f in value.fields}
                elif isinstance(value, lua.Number):
                    return value.n
                elif isinstance(value, lua.Nil):
                    return None
                else:
                    raise AssertionError(f"Could not convert {value} to a python object")

            map_data: list[dict[str, Any]] = to_python(map_data)
            out.tiles = []
            for tile in map_data:
                out.tiles.append(
                    TileSkeleton(
                        tile["tile"],
                        [bot.variants.find("rotate")((tile["dir"] - 1) * 45)] if bot.db.tiles[tile["tile"]].rotate else [],
                        tile["x"],
                        tile["y"],
                        None,
                        tile.get("color", None)
                    )
                )

            return out

        except KeyError:
            o = obj.copy()
            if "map" in o:
                del o["map"]
            warnings.warn(f"Could not parse:\n{o}")

            return None