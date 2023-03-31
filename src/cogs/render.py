import math
from io import BytesIO

import numpy as np
import cv2
from PIL import Image

from src.types import Bot, Tile, RenderingContext, ProcessedTile


class Renderer:
    def __init__(self, bot: Bot):
        self.bot = bot

    def blend(self, src, dst, mode):
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

    def recolor(
            self,
            sprite: np.ndarray,
            color: list[int, int] | list[int, int, int] | str,
            paint: bool | list[int, int] | list[int, int, int],
            palette: str = "default",
            force: bool = False
    ) -> np.ndarray:
        if isinstance(color, str):
            if (isinstance(paint, bool) and paint) or force:
                assert color in self.bot.db.overlays, f"what is overlayy `{color}`?? ?"
                overlay = self.bot.db.overlays[color]
                overlay = np.tile(overlay, (
                math.ceil(overlay.shape[0] / sprite.shape[0]), math.ceil(overlay.shape[1] / sprite.shape[1]), 1))
                overlay = overlay[:sprite.shape[0], :sprite.shape[1]]
                return np.multiply(sprite, overlay, casting="unsafe").astype(np.uint8)
            else:
                color = paint
        if len(color) < 3:
            assert palette in self.bot.db.palettes, f"idk where `{palette}` is ask ur gps"
            pal = self.bot.db.palettes[palette]
            color = pal[*color[::-1]]
        if len(color) < 4:
            color = *color, 0xFF
        color = np.array(color, dtype=float) / 255
        return np.multiply(sprite, color.reshape(1, 1, 4), casting="unsafe").astype(np.uint8)

    def process(self, tiles: list[Tile], ctx: RenderingContext) -> list[ProcessedTile]:
        processed_tile_list = []
        tile_cache = {}
        for tile in tiles:
            if (tile_hash := hash(tile)) in tile_cache:
                final_tile = tile_cache[tile_hash]
            else:
                sprites = tile.sprites
                w, h = 0, 0
                for i, sprite in enumerate(sprites):
                    # TODO: Process and remove sprite variants
                    sprites[i] = sprite
                    w = max(w, sprite.shape[1])
                    h = max(h, sprite.shape[0])
                out = np.zeros((h, w, 4), dtype=np.uint8)
                for i, sprite in enumerate(sprites):
                    sprite = self.recolor(sprite, tile.colors[i], tile.painted[i], tile.palette)
                    bounds = (
                        slice(int((h - sprite.shape[0]) // 2), int(((h + sprite.shape[0]) // 2))),
                        slice(int((w - sprite.shape[1]) // 2), int(((w + sprite.shape[1]) // 2)))
                    )
                    out[bounds] = self.blend(out[bounds], sprite, "normal")
                final_tile = ProcessedTile(
                    tile.name,
                    out,
                    tile.x,
                    tile.y,
                    tile.z,
                    tile.variants
                )
            # TODO: Process post variants
            processed_tile_list.append(final_tile)
        return processed_tile_list

    async def render(self, tiles: list[ProcessedTile], buf: BytesIO, ctx: RenderingContext) -> None:
        left, top, width, height = 0, 0, 0, 0
        for tile in tiles:
            tile: ProcessedTile
            h, w = tile.sprite.shape[:2]
            tile.scale[0] *= ctx.upscale
            tile.scale[1] *= ctx.upscale
            w *= tile.scale[0]
            h *= tile.scale[1]
            print(f"{tile.name=}, {w=}, {h=}")
            tile.x *= ctx.spacing * ctx.upscale
            tile.y *= ctx.spacing * ctx.upscale
            left = max(left, w / 2 - tile.x)
            top = max(top, h / 2 - tile.y)
            width = max(width, left + tile.x + w / 2)
            height = max(height, top + tile.y + h / 2)
        image = np.zeros((int(math.ceil(height)), int(math.ceil(width)), 4), dtype=np.uint8)
        for tile in sorted(tiles, key=lambda til: til.z):
            tile: ProcessedTile
            tile.x += left
            tile.y += top

            sprite = cv2.resize(tile.sprite, (0, 0), fx=int(tile.scale[0]), fy=int(tile.scale[0]),
                                interpolation=cv2.INTER_AREA)
            h, w = sprite.shape[:2]

            image_slice = slice(int(tile.y - h // 2), int(tile.y + h // 2)), \
                          slice(int(tile.x - w // 2), int(tile.x + w // 2))
            image[*image_slice] = self.blend(image[*image_slice], sprite, "normal")
        Image.fromarray(image).save(buf, format="PNG")
        buf.seek(0)


async def setup(bot: Bot):
    bot.renderer = Renderer(bot)
