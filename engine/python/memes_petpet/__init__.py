"""petpet 移植的 7 个表情。

来源: MemeCrafters/nonebot-plugin-petpet
  - 素材 resources/images/<key>/*.png (已复制到本包 images/)
  - 实现 nonebot_plugin_petpet/functions.py 同名函数

这两个表情集不在 MemeCrafters/meme-generator(282 主仓)里,
但 petpet 自己带实现。原函数体只依赖 pil_utils.BuildImage,没有 Nonebot
专属 API,所以直接包成 add_meme 挂进我们的 Python 引擎。
"""
from pathlib import Path
from typing import List

from PIL.Image import Image as IMG
from pil_utils import BuildImage

from meme_generator import add_meme
from meme_generator.utils import save_gif

ASSETS = Path(__file__).parent / "images"


def load_image(rel: str) -> BuildImage:
    return BuildImage.open(ASSETS / rel)


def make_jpg_or_gif(img: BuildImage, func) -> bytes:
    """静态输入出 jpg；GIF 输入按帧逐帧处理。"""
    image = img.image
    if not getattr(image, "is_animated", False):
        return func(img).save_jpg().getvalue()
    frames = []
    for f in range(getattr(image, "n_frames", 1)):
        image.seek(f)
        frames.append(func(BuildImage(image.copy())).image)
    return save_gif(frames, 0.1).getvalue()


TEXT_TOO_LONG = "文字太长了哦，改短点再试吧~"


def _whyatme(images, texts, args):
    img = images[0].convert("RGBA").resize((265, 265), keep_ratio=True)
    frame = load_image("whyatme/0.png")
    frame.paste(img, (42, 13), below=True)
    return frame.save_jpg()


def _anyasuki(images, texts, args):
    frame = load_image("anyasuki/0.png")
    want = (texts[0] if texts else "") or "阿尼亚喜欢这个"
    try:
        frame.draw_text(
            (5, frame.height - 60, frame.width - 5, frame.height - 10),
            want,
            max_fontsize=40,
            fill="white",
            stroke_fill="black",
            stroke_ratio=0.06,
        )
    except ValueError:
        return TEXT_TOO_LONG

    def make(img: BuildImage) -> BuildImage:
        return frame.copy().paste(
            img.resize((305, 235), keep_ratio=True), (106, 72), below=True
        )

    return make_jpg_or_gif(images[0], make)


def _thinkwhat(images, texts, args):
    frame = load_image("thinkwhat/0.png")

    def make(img: BuildImage) -> BuildImage:
        return frame.copy().paste(
            img.resize((534, 493), keep_ratio=True), (530, 0), below=True
        )

    return make_jpg_or_gif(images[0], make)


def _walnutpad(images, texts, args):
    frame = load_image("walnutpad/0.png")

    def make(img: BuildImage) -> BuildImage:
        return frame.copy().paste(
            img.resize((540, 360), keep_ratio=True), (368, 65), below=True
        )

    return make_jpg_or_gif(images[0], make)


def _tankuku_holdsign(images, texts, args):
    img = images[0].convert("RGBA").resize((300, 230), keep_ratio=True)
    params = (
        (((0, 46), (320, 0), (350, 214), (38, 260)), (68, 91)),
        (((18, 0), (328, 28), (298, 227), (0, 197)), (184, 77)),
        (((15, 0), (294, 28), (278, 216), (0, 188)), (194, 65)),
        (((14, 0), (279, 27), (262, 205), (0, 178)), (203, 55)),
        (((14, 0), (270, 25), (252, 195), (0, 170)), (209, 49)),
        (((15, 0), (260, 25), (242, 186), (0, 164)), (215, 41)),
        (((10, 0), (245, 21), (230, 180), (0, 157)), (223, 35)),
        (((13, 0), (230, 21), (218, 168), (0, 147)), (231, 25)),
        (((13, 0), (220, 23), (210, 167), (0, 140)), (238, 21)),
        (((27, 0), (226, 46), (196, 182), (0, 135)), (254, 13)),
        (((27, 0), (226, 46), (196, 182), (0, 135)), (254, 13)),
        (((27, 0), (226, 46), (196, 182), (0, 135)), (254, 13)),
        (((0, 35), (200, 0), (224, 133), (25, 169)), (175, 9)),
        (((0, 35), (200, 0), (224, 133), (25, 169)), (195, 17)),
        (((0, 35), (200, 0), (224, 133), (25, 169)), (195, 17)),
    )
    frames: List[IMG] = []
    for i in range(15):
        points, pos = params[i]
        frame = load_image(f"tankuku_holdsign/{i}.png")
        frame.paste(img.perspective(points), pos, below=True)
        frames.append(frame.image)
    return save_gif(frames, 0.2)


def _avatar_formula(images, texts, args):
    frame = load_image("avatar_formula/0.png")
    img_c = images[0].convert("RGBA").circle().resize((72, 72))
    img_tp = images[0].convert("RGBA").circle().resize((51, 51))
    frame.paste(img_tp, (948, 247))
    locs = [
        (143, 32), (155, 148), (334, 149), (275, 266), (486, 266),
        (258, 383), (439, 382), (343, 539), (577, 487), (296, 717),
        (535, 717), (64, 896), (340, 896), (578, 897), (210, 1038),
        (644, 1039), (64, 1192), (460, 1192), (698, 1192), (1036, 141),
        (1217, 141), (1243, 263), (1140, 378), (1321, 378), (929, 531),
        (1325, 531), (1592, 531), (1007, 687), (1390, 687), (1631, 686),
        (1036, 840), (1209, 839), (1447, 839), (1141, 1018), (1309, 1019),
        (1546, 1019), (1037, 1197), (1317, 1198), (1555, 1197),
    ]
    for x, y in locs:
        frame.paste(img_c, (x, y))
    return frame.save_jpg()


def _mywife(images, texts, args):
    img = images[0].convert("RGBA").resize_width(400)
    img_w, img_h = img.size
    frame = BuildImage.new("RGBA", (650, img_h + 500), "white")
    frame.paste(img, (int(325 - img_w / 2), 105), alpha=True)

    frame.draw_text(
        (27, 12, 27 + 596, 12 + 79),
        "如果你的老婆长这样",
        max_fontsize=70, min_fontsize=30,
        allow_wrap=True, lines_align="center",
    )
    frame.draw_text(
        (27, img_h + 120, 27 + 593, img_h + 120 + 135),
        "那么这就不是你的老婆\n这是我的老婆",
        max_fontsize=70, min_fontsize=30, allow_wrap=True,
    )
    frame.draw_text(
        (27, img_h + 295, 27 + 374, img_h + 295 + 135),
        "滚去找你\n自己的老婆去",
        max_fontsize=70, min_fontsize=30,
        allow_wrap=True, lines_align="center",
    )

    img_point = load_image("mywife/1.png").resize_width(200)
    frame.paste(img_point, (421, img_h + 270))
    return frame.save_jpg()


# 注册（add_meme 是普通函数，不是装饰器）
add_meme(
    "whyatme", _whyatme,
    min_images=1, max_images=1,
    keywords=["为什么艾特我", "为啥艾特我", "whyatme"],
)
add_meme(
    "anyasuki", _anyasuki,
    min_images=1, max_images=1,
    min_texts=0, max_texts=1,
    default_texts=["阿尼亚喜欢这个"],
    keywords=["阿尼亚喜欢", "阿尼亚", "anyasuki"],
)
add_meme(
    "thinkwhat", _thinkwhat,
    min_images=1, max_images=1,
    keywords=["想什么", "在想什么", "thinkwhat"],
)
add_meme(
    "walnutpad", _walnutpad,
    min_images=1, max_images=1,
    keywords=["核桃垫", "键盘侠", "walnutpad"],
)
add_meme(
    "tankuku_holdsign", _tankuku_holdsign,
    min_images=1, max_images=1,
    keywords=["坦克举牌", "举牌", "tankuku"],
)
add_meme(
    "avatar_formula", _avatar_formula,
    min_images=1, max_images=1,
    keywords=["头像公式", "头像分布", "avatar_formula"],
)
add_meme(
    "mywife", _mywife,
    min_images=1, max_images=1,
    keywords=["我老婆", "这是我的老婆", "mywife"],
)