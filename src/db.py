import re
import struct
import warnings
from io import BytesIO
from pathlib import Path

import asqlite
import numpy as np
from PIL import Image

from src.types import TileData, Bot


class Database:
    conn: asqlite.Connection
    bot: Bot
    tiles: dict[str, TileData] = {}
    palettes: dict[str, np.ndarray] = {}
    overlays: dict[str, np.ndarray] = {}

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
            for (name, colors, raw_sprites, painted) in await cur.fetchall():
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
                if len(sprites) != len(colors) or (painted is not None and len(sprites) != len(painted)):
                    warnings.warn(f"Tile {name} is invalid")
                    continue
                self.tiles[name] = TileData(colors, sprites, painted)

    async def load_palettes(self):
        self.palettes = {}
        for pal in Path("data/bab/assets/palettes").glob("*.png"):
            with Image.open(pal) as im:
                self.palettes[pal.stem] = np.array(im, dtype=np.uint8)

    async def load_overlays(self):
        self.overlays = {}
        for ov in Path("data/bab/assets/sprites/overlay").glob("*.png"):
            with Image.open(ov) as im:
                self.overlays[ov.stem] = np.array(im, dtype=np.uint8).astype(float) / 255

    async def close(self):
        await self.conn.close()

    async def create_tables(self):
        async with self.conn.cursor() as cur:
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                name TEXT PRIMARY KEY ASC NOT NULL UNIQUE,
                color TEXT NOT NULL DEFAULT "0,3",
                sprite BLOB NOT NULL,
                painted TEXT
            ) WITHOUT ROWID;
            """)
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                name TEXT NOT NULL,
                author TEXT,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                palette TEXT NOT NULL DEFAULT "default",
                background_sprite TEXT
            );
            """)
