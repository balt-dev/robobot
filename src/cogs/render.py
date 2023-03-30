import math
from io import BytesIO

import numpy as np
from PIL import Image

from src.types import Bot, Tile, RenderingContext


class Renderer:
    def __init__(self, bot: Bot):
        self.bot = bot

    def blend(self, src, dst, mode):
        print(f"{src.shape=}, {dst.shape=}")
        out_a = (src[..., 3] + dst[..., 3] * (1 - src[..., 3] / 255)).astype(np.uint8)
        a, b = src[..., :3].astype(float) / 255, dst[..., :3].astype(float) / 255
        if mode == "normal":
            c = b
        # TODO: implement more blending modes
        else:
            raise AssertionError(f"wat is blenn mod `{mode}`??")
        dst_alpha = dst[..., 3].astype(float) / 255
        dst_alpha = dst_alpha[:, :, np.newaxis]
        c = ((1 - dst_alpha) * a + dst_alpha * c)
        c[out_a == 0] = 0
        return np.dstack((np.clip(c * 255, 0, 255).astype(np.uint8), out_a[..., np.newaxis]))

    async def render(self, tiles: list[Tile], buf: BytesIO, ctx: RenderingContext) -> None:
        left, top, width, height = 0, 0, 0, 0
        for tile in tiles:
            h, w = np.max([sprite.shape[:2] for sprite in tile.sprites], axis=0)
            print(f"{tile.name=}, {w=}, {h=}")
            tile.x *= ctx.spacing
            tile.y *= ctx.spacing
            left = max(left, w // 2 - tile.x)
            top = max(top, h // 2 - tile.y)
            width = max(width, left + tile.x + w // 2, w)
            height = max(height, top + tile.y + h // 2, h)
        image = np.zeros((width, height, 4), dtype=np.uint8)
        for tile in sorted(tiles, key=lambda til: til.z):
            tile.x += left
            tile.y += top
            for sprite in tile.sprites:
                h, w = sprite.shape[:2]
                image_slice = slice(tile.y - h//2, tile.y + h//2), slice(tile.x - w//2, tile.x + w//2)
                image[image_slice] = self.blend(image[image_slice], sprite, "normal")
        Image.fromarray(image).save(buf, format="PNG")
        buf.seek(0)

async def setup(bot: Bot):
    bot.renderer = Renderer(bot)
