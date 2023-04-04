import json
import re
import struct
import warnings
from io import BytesIO
from pathlib import Path
from luaparser import ast

import asqlite
import numpy as np
from PIL import Image

from src.types import TileData, Bot, LevelData


class Database:
    conn: asqlite.Connection
    bot: Bot
    tiles: dict[str, TileData] = {}
    palettes: dict[str, np.ndarray] = {}
    overlays: dict[str, np.ndarray] = {}
    worlds: dict[str, dict[str, LevelData]] = {}
    level_names: dict[str, str] = {}

    def __init__(self, bot):
        self.bot = bot

    async def connect(self, db: str):
        self.conn = await asqlite.connect(db)
        await self.create_tables()
        await self.load()

    async def load(self):
        await self.load_tiles(flush=True)
        await self.load_palettes()
        await self.load_overlays()

    async def load_tiles(self, *, flush: bool = False):
        if flush: self.tiles = {}
        async with self.conn.cursor() as cur:
            await cur.execute("SELECT * FROM tiles")
            for (name, colors, raw_sprites, raw_slep_sprites, painted, rotate, layer) in await cur.fetchall():
                colors = [[int(n) for n in color.split(",")] for color in colors.split(" ")]
                painted = [
                    [int(n) for n in paint.split(",")] if "," in paint else bool(int(paint))
                    for paint in painted.split(" ")
                ] if painted is not None else [True for _ in range(len(colors))]
                sprites = []
                with BytesIO(raw_sprites) as buf:
                    while len(next_loc := buf.read(4)):
                        seek_length, = struct.unpack("<L", next_loc)
                        image_data = buf.read(seek_length)
                        with BytesIO(image_data) as image_buf:
                            with Image.open(image_buf) as im:
                                sprites.append(np.array(im.convert("RGBA"), dtype=np.uint8))
                if not len(sprites):
                    warnings.warn(f"Tile {name} is invalid")
                    continue
                slep_sprites = None
                if raw_slep_sprites is not None:
                    slep_sprites = []
                    with BytesIO(raw_slep_sprites) as buf:
                        while len(next_loc := buf.read(4)):
                            seek_length, = struct.unpack("<L", next_loc)
                            image_data = buf.read(seek_length)
                            with BytesIO(image_data) as image_buf:
                                with Image.open(image_buf) as im:
                                    slep_sprites.append(np.array(im.convert("RGBA"), dtype=np.uint8))
                self.tiles[name] = TileData(colors, sprites, slep_sprites, painted, rotate, layer)

    async def load_palettes(self):
        self.palettes = {}
        for pal in Path("data/bab/assets/palettes").glob("*.png"):
            with Image.open(pal) as im:
                self.palettes[pal.stem] = np.array(im.convert("RGBA"), dtype=np.uint8)

    async def load_overlays(self):
        self.overlays = {}
        for ov in Path("data/bab/assets/sprites/overlay").glob("*.png"):
            with Image.open(ov) as im:
                self.overlays[ov.stem] = np.array(im.convert("RGBA"), dtype=np.uint8).astype(float) / 255

    async def load_worlds(self):
        self.worlds = {}
        self.level_names = {}
        for world in Path("data/bab/officialworlds/").glob("*/"):
            world_name = world.stem
            self.worlds[world_name] = {}
            for level in world.glob("**/*.bab"):
                with open(level, "r") as f:
                    raw_level_data = json.load(f)
                    level_data = LevelData.from_json(raw_level_data, self.bot)
                    if level_data is not None:
                        self.worlds[world_name][str(level)[len(str(world))+1:]] = level_data
                        self.level_names[level_data.name] = level_data




    async def close(self):
        await self.conn.close()

    async def create_tables(self):
        async with self.conn.cursor() as cur:
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                name TEXT PRIMARY KEY ASC NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT "0,3",
                sprite BLOB NOT NULL,
                sleep_sprite BLOB,
                painted TEXT,
                rotate BOOLEAN,
                z_index INTEGER
            ) WITHOUT ROWID;
            """)
