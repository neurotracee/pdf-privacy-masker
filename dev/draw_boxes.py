# -*- coding: utf-8 -*-
"""把 JUnit 算出来的字框回放到页面上，做逐像素核对（仅开发期验证用）。

数据来源：
  dev/fixtures/ocr/<tag>.json         桌面端同模型导出的检测/识别结果
  dev/fixtures/ocr/<tag>.boxes.json   安卓端 Kotlin 几何算出的字框（单测产物）

输出两张分开的图（叠在一起看不清谁是谁）：
  dev/fixtures/ocr/<tag>_new.png   只画新算法的逐字框（蓝 2px）
  dev/fixtures/ocr/<tag>_old.png   只画旧算法的逐字框（绿 2px）

用法：python dev/draw_boxes.py [tag ...]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz                     # noqa: E402
import pdfmask_ocr as O         # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "ocr")
ROOT = os.path.dirname(HERE)

SKEW_PAGES = {"hard4_p5_skew": ("刁难文档4_扫描件.pdf", 4, 1.2)}


def render(pdf, page_no, rotate_deg=0.0, zoom=180.0 / 72.0):
    doc = fitz.open(pdf)
    page = doc[page_no]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    im = Image.fromarray(np.ascontiguousarray(rgb[:, :, :3]))
    if rotate_deg:
        im = im.rotate(rotate_deg, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
    return im


def old_char_boxes(it):
    """旧算法：检测外扩框宽度 × CTC 比例，给一个按字高的最小宽度"""
    text = it["text"]
    spans = it["spans"]
    cx0, cy0 = it["cx0"], it["cy0"]
    x0 = it["X0"] - cx0
    x1 = it["X1"] + max(2, int(round((it["Y1"] - it["Y0"]) * 0.85)))
    x0 = x0 - max(2, int(round((it["Y1"] - it["Y0"]) * 0.85)))
    gy0 = it["raw_y0"] - cy0
    gy1 = it["raw_y1"] - cy0
    width = float(x1 - x0)
    glyph_h = max(1.0, gy1 - gy0)
    min_w = min(glyph_h * 0.9, width * 0.6)
    out = []
    for k in range(min(len(text), len(spans))):
        f0, f1 = spans[k]
        b0 = (spans[k - 1][1] + f0) / 2 if k else f0
        b1 = (f1 + spans[k + 1][0]) / 2 if k + 1 < len(spans) else f1
        if b1 <= b0:
            b0, b1 = f0, f1
        a0 = x0 + width * b0
        a1 = x0 + width * b1
        if a1 - a0 < min_w:
            mid = (a0 + a1) / 2
            a0 = mid - min_w / 2
            a1 = mid + min_w / 2
        out.append((cx0 + a0, cy0 + gy0, cx0 + a1, cy0 + gy1))
    return out


def draw(tag):
    fx = json.load(open(os.path.join(OUT, tag + ".json"), encoding="utf-8"))
    bx = json.load(open(os.path.join(OUT, tag + ".boxes.json"), encoding="utf-8"))
    pdf, page_no, deg = SKEW_PAGES.get(tag, (fx["pdf"], fx["page"], 0.0))
    path = os.path.join(ROOT, "test", "hard4", pdf)
    if not os.path.exists(path):
        path = os.path.join(ROOT, "test", pdf)
    base = render(path, page_no, deg).convert("RGB")
    cx, cy = base.width / 2.0, base.height / 2.0

    new = base.copy()
    d = ImageDraw.Draw(new)
    for it in bx["items"]:
        for (a, b, c, e) in it["chars"]:
            d.rectangle([a, b, c, e], outline=(20, 80, 235), width=2)
    new.save(os.path.join(OUT, tag + "_new.png"))

    old = base.copy()
    d = ImageDraw.Draw(old)
    for it in fx["items"]:
        for (a, b, c, e) in old_char_boxes(it):
            if fx["skew"]:
                a, b, c, e = O._unrotate_box(a, b, c, e, cx, cy, fx["skew"])
            d.rectangle([a, b, c, e], outline=(0, 150, 0), width=2)
    old.save(os.path.join(OUT, tag + "_old.png"))
    print("saved", tag)


if __name__ == "__main__":
    tags = sys.argv[1:] or [f[:-5] for f in os.listdir(OUT)
                            if f.endswith(".json") and not f.endswith(".boxes.json")]
    for t in sorted(tags):
        if os.path.exists(os.path.join(OUT, t + ".boxes.json")):
            draw(t)
