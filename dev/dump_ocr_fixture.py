# -*- coding: utf-8 -*-
"""把真实扫描页的「检测框 + 识别文本 + CTC 比例 + 裁图灰度」导成夹具。

为什么要导夹具：安卓端的字框几何是 Kotlin 写的（CharLayout / readPageInner），
本机没有安卓设备时跑不了 OCR。这里用桌面端同一套模型（同一份 PP-OCRv4）把
一页的真实输出导出来，再让 JVM 单元测试用**产品代码**算出字框，
最后回填到页面上画出来逐像素核对。夹具只是输入，几何仍然只有一份实现。

用法：python dev/dump_ocr_fixture.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz                     # noqa: E402
import pdfmask_ocr as O         # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "ocr")
DPI = 180


def lum_of(rgb):
    rgb = rgb.astype(np.float32)
    return (rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114)


def render(pdf, page_no, rotate_deg=0.0, zoom=DPI / 72.0):
    doc = fitz.open(pdf)
    page = doc[page_no]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    rgb = np.ascontiguousarray(rgb[:, :, :3])
    if rotate_deg:
        from PIL import Image
        im = Image.fromarray(rgb).rotate(rotate_deg, resample=Image.BICUBIC,
                                        fillcolor=(255, 255, 255))
        rgb = np.asarray(im)
    return rgb


def dump(pdf, page_no, tag, rotate_deg=0.0):
    eng = O.OcrEngine.get()
    full = render(pdf, page_no, rotate_deg)
    h, w = full.shape[:2]
    gray = lum_of(full)

    skew = O.estimate_skew(gray)
    if abs(skew) < O.SKEW_MIN:
        skew = 0.0
    aligned = full
    if skew:
        from PIL import Image
        aligned = np.ascontiguousarray(np.asarray(
            Image.fromarray(full).rotate(skew, resample=Image.BICUBIC, fillcolor=(255, 255, 255))))

    if O.has_gradient(aligned):
        work = O.normalize_contrast(O.flatten_illumination(aligned))
    else:
        work = O.normalize_contrast(aligned)
    if work is None:
        work = aligned

    bh, bw = aligned.shape[:2]
    scale = min(1.0, O.DET_LIMIT / float(max(bh, bw)))
    small = (O._resize_rgb(work, int(round(bw * scale)), int(round(bh * scale)))
             if scale < 1.0 else work)
    boxes = eng._detect(small)
    inv = 1.0 / scale

    items = []
    crops, meta = [], []
    for x0, y0, x1, y1, sc, raw_y0, raw_y1 in boxes:
        X0 = max(0, int(x0 * inv)); Y0 = max(0, int(y0 * inv))
        X1 = min(bw, int(x1 * inv) + 1); Y1 = min(bh, int(y1 * inv) + 1)
        if X1 - X0 < 4 or Y1 - Y0 < 4:
            continue
        bhx = Y1 - Y0
        pad_x = max(2, int(round(bhx * O.PAD_RATIO)))
        pad_y = max(2, int(round(bhx * 0.20)))
        cx0 = max(0, X0 - pad_x); cy0 = max(0, Y0 - pad_y)
        cx1 = min(bw, X1 + pad_x); cy1 = min(bh, Y1 + pad_y)
        crops.append(np.ascontiguousarray(work[cy0:cy1, cx0:cx1]))
        meta.append(dict(X0=X0, Y0=Y0, X1=X1, Y1=Y1,
                         raw_y0=max(0, raw_y0 * inv), raw_y1=min(bh, raw_y1 * inv),
                         cx0=cx0, cy0=cy0, cx1=cx1, cy1=cy1))
    recs = eng._rec_batch(crops)

    for k, (meta_k, (text, chars)) in enumerate(zip(meta, recs)):
        if not text.strip():
            continue
        crop = crops[k]
        chh, ch = crop.shape[:2]      # numpy 是 (高, 宽)
        items.append(dict(
            **meta_k,
            text=text,
            spans=[[round(c[1], 5), round(c[2], 5)] for c in chars],
            crop=dict(w=ch, h=chh, bin="%s_%02d.bin" % (tag, k)),
            contentLeft=float(meta_k["X0"] - meta_k["cx0"]),
            contentRight=float(meta_k["X1"] - meta_k["cx0"]),
            hintTop=float(meta_k["raw_y0"] - meta_k["cy0"]),
            hintBottom=float(meta_k["raw_y1"] - meta_k["cy0"]),
        ))
        g = lum_of(crop).round().clip(0, 255).astype(np.uint8)
        g.tofile(os.path.join(OUT, "%s_%02d.bin" % (tag, k)))

    os.makedirs(OUT, exist_ok=True)
    data = dict(pdf=os.path.basename(pdf), page=page_no, tag=tag,
                bw=bw, bh=bh, pageW=w, pageH=h, skew=skew, items=items)
    with open(os.path.join(OUT, tag + ".json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("%-16s page %d  skew=%.2f  boxes=%d  chars=%d"
          % (tag, page_no + 1, skew, len(items), sum(len(i["text"]) for i in items)))


def main():
    os.makedirs(OUT, exist_ok=True)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hard4 = os.path.join(root, "test", "hard4", "刁难文档4_扫描件.pdf")
    waybill = os.path.join(root, "test", "刁难文档25_多人多页.pdf")
    if os.path.exists(hard4):
        for p, tag in [(3, "hard4_p4"), (4, "hard4_p5")]:
            dump(hard4, p, tag)
        # 同一页人为转 1.2 度，走一遍「歪页」的全部流程
        dump(hard4, 4, "hard4_p5_skew", rotate_deg=1.2)
    if os.path.exists(waybill):
        dump(waybill, 0, "waybill_p1")


if __name__ == "__main__":
    main()
