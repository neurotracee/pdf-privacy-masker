#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 app.ico 里最大的那张图导出成 PNG，给 AppImage 当图标用。

Linux 的 .desktop / AppImage 只认 PNG（或 SVG），不认 Windows 的 .ico。
仓库里只维护一份 app.ico，这里在构建时转出来，避免两套图标各改各的。
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "app.ico")
OUT_DIR = os.path.join(ROOT, "build", "appimage")
OUT = os.path.join(OUT_DIR, "pdfmask.png")


def main():
    if not os.path.exists(SRC):
        print("找不到 %s" % SRC)
        return 1
    im = Image.open(SRC)
    sizes = sorted(getattr(im, "ico", None).sizes() if hasattr(im, "ico") else [],
                   key=lambda s: s[0] * s[1])
    if sizes:
        im = Image.open(SRC)
        im.size = sizes[-1]
        im.load()
    im = im.convert("RGBA")
    os.makedirs(OUT_DIR, exist_ok=True)
    im.save(OUT, "PNG")
    print("图标 -> %s（%dx%d）" % (OUT, im.width, im.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
