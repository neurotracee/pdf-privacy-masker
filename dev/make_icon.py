# -*- coding: utf-8 -*-
"""生成应用图标 app.ico：盾牌 + 对勾，下方压一枚 PDF 字样"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "app.ico")

S = 512
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\impact.ttf",
]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c1, c2 = (47, 107, 255), (108, 74, 255)

    # 渐变圆角底
    base = Image.new("RGBA", (S, S))
    bd = ImageDraw.Draw(base)
    for y in range(S):
        bd.line([(0, y), (S, y)], fill=lerp(c1, c2, y / float(S)) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
    img.paste(base, (0, 0), mask)

    # 白色盾牌（整体上移，给下方 PDF 字样留位置）
    shield = [(256, 42), (384, 92), (384, 206), (256, 336), (128, 206), (128, 92)]
    d.polygon(shield, fill=(255, 255, 255, 255))
    inner = [(256, 86), (344, 118), (344, 208), (256, 292), (168, 208), (168, 118)]
    d.polygon(inner, fill=c1 + (255,))
    # 勾
    d.line([(202, 196), (240, 234), (314, 150)], fill=(255, 255, 255, 255),
           width=28, joint="curve")

    # 下方 PDF 字样（手动字距，三个字母更紧凑）
    txt = "PDF"
    font = load_font(142)
    gap = 4
    widths = []
    for ch in txt:
        bb = d.textbbox((0, 0), ch, font=font)
        widths.append(bb[2] - bb[0])
    total = sum(widths) + gap * (len(txt) - 1)
    x = (S - total) / 2.0
    bb = d.textbbox((0, 0), txt, font=font)
    asc, desc = bb[1], bb[3]
    target_top = 356
    y = target_top - asc
    for ch, w in zip(txt, widths):
        d.text((x, y), ch, font=font, fill=(255, 255, 255, 255))
        x += w + gap

    img = img.resize((256, 256), Image.LANCZOS)
    img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon:", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
