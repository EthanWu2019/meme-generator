"""hendo（狠撅）——earth-k 后端私有模板，本地补实现。

元数据来自 earth-k 的 bq.json：
    key: hendo
    params: min_images=2, max_images=2, min_texts=0, max_texts=0
    keywords: 狠撅 / 狠狠撅

素材与 do 完全一致（memes_other/do/images/{0,1,2}.png 三帧背景），
区别是播放速度更快：do 是 save_gif(frames, 0.05)，
hendo 改成 0.02，并把中间帧重复一次拉开节奏差。

没有独立素材可用，所以直接引用 do 的图片目录而不是复制一份。
"""
from datetime import datetime
from pathlib import Path

from PIL.Image import Image as IMG
from pil_utils import BuildImage

from meme_generator import add_meme
from meme_generator.utils import save_gif

# 复用 do 的背景素材，不复制 3 张 PNG
# __init__.py sits in memes_other/hendo/, so parent IS memes_other
DO_IMAGES = Path(__file__).resolve().parent.parent / "do" / "images"

DURATION = 0.02


def hendo(images: list[BuildImage], texts, args):
    self_locs = [(116, -8), (109, 3), (130, -10)]
    user_locs = [(2, 177), (12, 172), (6, 158)]

    self_head = (
        images[0]
        .convert("RGBA")
        .resize((122, 122), keep_ratio=True)
        .circle()
        .rotate(15)
    )
    user_head = (
        images[1]
        .convert("RGBA")
        .resize((112, 112), keep_ratio=True)
        .circle()
        .rotate(90)
    )

    frames: list[IMG] = []
    for i in range(3):
        frame = BuildImage.open(DO_IMAGES / f"{i}.png")
        frame.paste(user_head, user_locs[i], alpha=True)
        frame.paste(self_head, self_locs[i], alpha=True)
        frames.append(frame.image)

    return save_gif(frames, DURATION)


add_meme(
    "hendo",
    hendo,
    min_images=2,
    max_images=2,
    keywords=["狠撅", "狠狠撅"],
    date_created=datetime(2021, 5, 4),
    date_modified=datetime(2025, 11, 26),
)