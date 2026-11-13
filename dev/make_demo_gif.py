# -*- coding: utf-8 -*-
"""把「打码前 / 打码后」两张截图合成一段左右推开的动图。

README 首屏原来只有一张静态对比图，访客要点开才知道「到底做了什么」。这段动图
用库里现成的两张真实截图拼出来——不画界面、不伪造效果：起手是全明文，一条竖线
从左推到右，推过去的地方就是打码后的样子。

用法：
    python dev/make_demo_gif.py

产物：docs/img/demo-wipe.gif

参数都在下面几个常量里，改宽度/帧数/停留时间直接改。
"""

import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
IMG = os.path.join(ROOT, "docs", "img")

SRC_BEFORE = os.path.join(IMG, "对比_打码前.png")
SRC_AFTER = os.path.join(IMG, "对比_打码后.png")
OUT = os.path.join(IMG, "demo-wipe.gif")

WIDTH = 700          # 输出宽度（README 里 700 足够清楚，文件也不大）
PAD = 10             # 裁切后留一点白边，别让文字贴边
WIPE_STEPS = 18      # 推开的帧数（帧多了文件大，18 帧已经够顺）
HOLD_BEFORE = 900    # 起始停留（毫秒）
HOLD_AFTER = 1600    # 结束停留（毫秒）
STEP_MS = 55         # 每一帧的时长
LINE = (60, 66, 76)  # 分隔线颜色
PALETTE_COLORS = 96  # 调色板颜色数，越小文件越小


def content_bbox(im, thresh=248, pad=PAD):
    """返回「有内容」区域的坐标（在原图坐标系里）。

    注意别写成 `trim(im).getbbox()`——裁完再取 bbox 拿到的是裁完那张图的坐标，
    套回原图就会错位，右侧内容会被切掉一截。
    """
    mask = im.convert("L").point(lambda v: 255 if v < thresh else 0)
    box = mask.getbbox()
    if not box:
        return (0, 0, im.width, im.height)
    l, t, r, b = box
    return (max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad))


def union_bbox(a, b):
    ax0, ay0, ax1, ay1 = content_bbox(a)
    bx0, by0, bx1, by1 = content_bbox(b)
    return (min(ax0, bx0), min(ay0, by0), max(ax1, bx1), max(ay1, by1))


def main():
    for p in (SRC_BEFORE, SRC_AFTER):
        if not os.path.exists(p):
            print("缺少素材：%s" % p)
            return 1

    before = Image.open(SRC_BEFORE).convert("RGB")
    after = Image.open(SRC_AFTER).convert("RGB")
    if before.size != after.size:
        # 两张图必须严格对齐，否则推开的瞬间会看到内容跳位
        print("两张截图尺寸不一致：%s vs %s" % (before.size, after.size))
        return 1

    # 两张图都参与决定裁切范围：文字在哪、马赛克在哪，都别裁掉
    box = union_bbox(before, after)
    before_c = before.crop(box)
    after_c = after.crop(box)

    # 等比缩放到固定宽度
    h = round(before_c.height * WIDTH / before_c.width)
    h -= h % 2
    before_s = before_c.resize((WIDTH, h), Image.LANCZOS)
    after_s = after_c.resize((WIDTH, h), Image.LANCZOS)

    frames = []
    durations = []

    def push(x):
        """画一帧：x 左侧用 before，右侧用 after，交界处一条竖线。"""
        f = before_s.copy()
        if x > 0:
            f.paste(after_s.crop((0, 0, x, h)), (0, 0))
        d = ImageDraw.Draw(f)
        if 0 < x < WIDTH:
            d.line([(x, 0), (x, h)], fill=LINE, width=3)
        return f.convert("P", palette=Image.ADAPTIVE, colors=PALETTE_COLORS)

    frames.append(push(0))
    durations.append(HOLD_BEFORE)
    for i in range(1, WIPE_STEPS + 1):
        frames.append(push(round(WIDTH * i / WIPE_STEPS)))
        durations.append(STEP_MS)
    frames.append(push(WIDTH))
    durations.append(HOLD_AFTER)

    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    size = os.path.getsize(OUT)
    print("已生成 %s（%d 帧，%.1f KB，%dx%d）" % (OUT, len(frames), size / 1024.0, WIDTH, h))
    if size > 3 * 1024 * 1024:
        print("提示：动图超过 3MB 了，Gitee 那边加载会慢，考虑调小 WIDTH 或 PALETTE_COLORS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
