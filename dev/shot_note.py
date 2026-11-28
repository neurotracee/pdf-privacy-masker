# -*- coding: utf-8 -*-
"""README / 文档配图统一的小字说明（右下角那行）。

为什么要有这个
--------------
这些图不是「拍一张屏幕」那么简单：界面本身是程序真实运行的截图，但外面的
浏览器窗口 / 手机外壳、渐变底、投影，全是代码叠上去的合成效果；图里那份
PDF 和上面的姓名电话，也是脚本生成的测试样例。不加说明的话，读者会以为
整张图都是原始截图，或者反过来以为是画出来的效果图。所以每张图下面都压一
行小字，把这三件事讲清楚，再加一句「具体以实际界面为准」。

用法
----
    # 由 dev/make_readme_shots.py 调用（画在渐变画布底部）
    from shot_note import stamp
    img = stamp(canvas, "zh")

    # 直接处理已有图片（底部不够高会自动延长，重复跑不会叠加）
    python dev/shot_note.py docs/img/android-interface-framed.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# 原图备份：重复处理时从这份重新来，避免小字一层叠一层
BACKUP = os.path.join(HERE, "_ui", "shot-note-orig")

FONT_CANDS = [
    r"C:\Windows\Fonts\msyh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
FONT_CANDS_EN = [
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

# 两行：第一行讲清「哪部分是截图、哪部分是代码加的、内容是 AI 生成的」，
# 第二行单独一句「具体以实际界面为准」，放最后最醒目的位置。
NOTE = {
    "zh": [
        "界面是程序真实运行时的截图；外层的浏览器/手机外壳、渐变底与投影是用代码叠上去的合成效果；"
        "图中文档与示例文字由 AI 辅助生成。",
        "具体以实际界面为准。",
    ],
    "en": [
        "The UI is a real screenshot of the running app; the browser/phone frame, gradient background and "
        "shadow are composited in code; the sample document and its wording are AI-assisted.",
        "The actual interface prevails.",
    ],
}

# 纯截图（没有套壳、没有合成底）用的版本：写清「这张没加工」，别让读者
# 反过来说「你没说哪些是原图」。
NOTE_RAW = {
    "zh": [
        "本图是程序真实运行时的截图，未做套壳或合成修饰；图中文档与示例文字由 AI 辅助生成。",
        "具体以实际界面为准。",
    ],
    "en": [
        "This is a real screenshot of the running app, with no frame or compositing added; "
        "the sample document and its wording are AI-assisted.",
        "The actual interface prevails.",
    ],
}

FINE = {"light": (112, 119, 134), "dark": (162, 170, 186)}


def _font(px, lang="zh"):
    cands = (FONT_CANDS_EN if lang == "en" else []) + FONT_CANDS
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, px)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(text, fn, maxw):
    """按像素宽度折行：中文按字断，英文单词不拆开。"""
    import re
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\.\-\+/:%]*|\s+|.", text)
    lines, cur = [], ""
    for t in tokens:
        trial = cur + t
        if fn.getlength(trial) <= maxw or not cur.strip():
            cur = trial
        else:
            lines.append(cur.rstrip())
            cur = "" if t.isspace() else t
    if cur.strip():
        lines.append(cur.strip())
    return lines


def stamp(img, lang="zh", credit=None, theme="light", kind="mixed",
          size=None, lh=None, left=None, top_pad=28, bottom_pad=58, fill=None,
          band=None):
    """在图片底部补一块同色区域，写几行小字（可选再跟一行 credit）。

    img 需为 RGBA。返回加高后的新图，原图不动。
    """
    # 字号跟着图宽走：2400 宽的主图用 26px，1000 宽的小图用 21px，
    # 不然小图上那行字会显得跟正文一样大，抢戏。
    size = size or max(17, min(26, int(img.width / 46)))
    lh = lh or int(size * 1.55)
    left = left if left is not None else max(46, int(img.width * 0.06))
    fn = _font(size, lang)
    body = NOTE_RAW if kind == "raw" else NOTE
    raw = list(body[lang]) + ([credit] if credit else [])
    maxw = max(200, img.width - left * 2)
    lines = []
    for t in raw:
        lines.extend(_wrap(t, fn, maxw))
    area = top_pad + lh * len(lines) + bottom_pad
    out = Image.new("RGBA", (img.width, img.height + area), (0, 0, 0, 0))
    out.paste(img, (0, 0))
    # 画布用的是渐变底，用最后一行像素往下延展就能接上；纯截图没有渐变，
    # 硬拉会拉出一条脏边，所以换个干净的底色当「说明条」。
    if band:
        out.paste(Image.new("RGBA", (img.width, area), tuple(band)), (0, img.height))
    else:
        bottom = img.crop((0, img.height - 1, img.width, img.height)).resize(
            (img.width, area), Image.BILINEAR)
        out.paste(bottom, (0, img.height))
    d = ImageDraw.Draw(out)
    col = fill or FINE.get(theme, FINE["light"])
    y = img.height + top_pad
    for ln in lines:
        d.text((left, y), ln, font=fn, fill=tuple(col) + (255,))
        y += lh
    return out


def stamp_file(path, lang="zh", theme="light", fill=None, kind="mixed"):
    """就地处理一张已有图片：先备份原图，重复跑不会叠加小字。"""
    os.makedirs(BACKUP, exist_ok=True)
    base = os.path.basename(path)
    bak = os.path.join(BACKUP, base)
    src = bak if os.path.exists(bak) else path
    if not os.path.exists(bak):
        with open(src, "rb") as fh:
            data = fh.read()
        with open(bak, "wb") as fh:
            fh.write(data)
    im = Image.open(src)
    fmt = (im.format or "PNG").upper()
    im = im.convert("RGBA")
    # 按画面明暗挑说明条的底色：浅色图配浅条 + 深字，深色图反过来
    lum = im.convert("L").resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    light = lum > 110
    band = (246, 247, 250, 255) if light else (24, 27, 34, 255)
    fill = fill or ((88, 95, 110) if light else (178, 186, 200))
    out = stamp(im, lang=lang, theme=theme, fill=fill, kind=kind, band=band)
    if fmt == "JPEG":
        out.convert("RGB").save(path, "JPEG", quality=92)
    else:
        out.save(path, "PNG", optimize=True)
    print("  小字已加：%s  (+%d px)" % (os.path.relpath(path, ROOT), out.height - im.height))
    return path


if __name__ == "__main__":
    themes = {"--dark": "dark"}
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    theme = next((themes[a] for a in sys.argv[1:] if a in themes), "light")
    lang = "en" if "--en" in sys.argv[1:] else "zh"
    kind = "raw" if "--raw" in sys.argv[1:] else "mixed"
    if not args:
        raise SystemExit(__doc__)
    for p in args:
        p = p if os.path.isabs(p) else os.path.join(ROOT, p)
        stamp_file(p, lang=lang, theme=theme, kind=kind)
