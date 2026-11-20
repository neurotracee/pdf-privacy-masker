# -*- coding: utf-8 -*-
"""出英文版的「打码前后」素材：页面图 + 左右对比图 + 推开动图。

中文版那套（docs/img/对比_打码前.png、comparison.png、demo-wipe.gif）是中文文档，
英文 README 里直接套用会让人看到满屏中文。这里用同一套识别/打码代码，跑一份
**英文表单**，产出对称的三份文件：

    docs/img/对比_打码前_en.png
    docs/img/对比_打码后_en.png
    docs/img/comparison-en.png
    docs/img/demo-wipe-en.gif

用法：
    python dev/make_doc_demo_en.py

注意：英文样例文档是脚本现画的（dev/fixtures/en_sample.pdf），不是伪造效果——
打码那一半是真的走 pdfmask.detect + pdfmask.redact 得来的。
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

import pdfengine  # noqa: E402
import pdfmask    # noqa: E402
from PIL import Image  # noqa: E402

FIX = os.path.join(ROOT, "dev", "fixtures")
IMG = os.path.join(ROOT, "docs", "img")
SAMPLE = os.path.join(FIX, "en_sample.pdf")
MASKED = os.path.join(FIX, "en_sample_masked.pdf")

BEFORE = os.path.join(IMG, "对比_打码前_en.png")
AFTER = os.path.join(IMG, "对比_打码后_en.png")
COMPARE = os.path.join(IMG, "comparison-en.png")

ZOOM = 1.7          # 与中文版素材的清晰度对齐（1012×1432 左右）
GAP = 40            # 对比图两页之间的空档
BG = (255, 255, 255)

ROWS = [
    ("Full name", "Jonathan Reyes"),
    ("Date of birth", "12 May 1990"),
    ("Job title", "Senior Analyst"),
    ("Department", "Corporate Finance"),
    ("Hire date", "15 March 2023"),
    ("Phone", "13800138000"),
    ("Mobile", "+86 139 0013 9000"),
    ("Work phone", "010 8888 6666"),
    ("Email", "j.reyes@example.com"),
    ("Backup email", "jonathan.reyes@mail.com"),
    ("Bank card", "6222 0212 3456 7890 128"),
    ("Payroll account", "6222 0234 5678 9016"),
    ("Address", "Room 1203, Building 5, 88 Jianguo Road"),
    ("Emergency contact", "Linda Reyes  13900139000"),
]


def build_sample():
    """画一份英文员工信息表，字段分布与中文样例一致（标签在左、值在右）。"""
    doc = pdfengine.new_doc()
    p = doc.new_page(width=595, height=842)
    p.insert_text((60, 80), "EMPLOYEE INFORMATION FORM", fontsize=18, fontname="helv")
    p.insert_text((60, 102), "Reference: HR-2026-0315", fontsize=9, fontname="helv")
    p.draw_line((60, 118), (535, 118))
    y = 156
    for label, value in ROWS:
        p.insert_text((60, y), label + ":", fontsize=11, fontname="helv")
        p.insert_text((240, y), value, fontsize=11, fontname="helv")
        p.draw_line((60, y + 8), (535, y + 8))
        y += 34
    p.insert_text((60, 720), "I confirm the above information is true and complete.",
                  fontsize=9, fontname="helv")
    p.insert_text((60, 752), "Signature: ______________        Date: 03 / 15 / 2026",
                  fontsize=9, fontname="helv")
    os.makedirs(FIX, exist_ok=True)
    doc.save(SAMPLE)
    return SAMPLE


def page_png(path, out):
    doc = pdfengine.open_doc(path)
    pix = pdfengine.render_page(doc[0], zoom=ZOOM)
    img = Image.open(__import__("io").BytesIO(pix.tobytes("png"))).convert("RGB")
    img.save(out, "PNG", optimize=True)
    return img


def make_pair():
    build_sample()
    findings = pdfmask.detect(pdfengine.open_doc(SAMPLE), use_ocr=False)
    names = sorted({f["type"] for f in findings})
    print("  识别到 %d 处：%s" % (len(findings), ", ".join(names)))
    if not findings:
        raise SystemExit("英文样例没识别出任何内容，拒绝出图")

    doc = pdfengine.open_doc(SAMPLE)
    pdfmask.redact(doc, findings)
    doc.save(MASKED)

    before = page_png(SAMPLE, BEFORE)
    after = page_png(MASKED, AFTER)
    print("  -> docs/img/%s / %s" % (os.path.basename(BEFORE), os.path.basename(AFTER)))
    return before, after


def make_compare(before, after):
    """左右并排，和中文版对比图一个观感：白底、等高、中间一条空档。"""
    h = min(before.height, after.height)
    cv = Image.new("RGB", (before.width + after.width + GAP, h), BG)
    cv.paste(before.crop((0, 0, before.width, h)), (0, 0))
    cv.paste(after.crop((0, 0, after.width, h)), (before.width + GAP, 0))
    cv.save(COMPARE, "PNG", optimize=True)
    print("  -> docs/img/comparison-en.png (%dx%d, %.0f KB)"
          % (cv.width, cv.height, os.path.getsize(COMPARE) / 1024.0))


def make_gif():
    sys.path.insert(0, HERE)
    import make_demo_gif as G
    G.SRC_BEFORE, G.SRC_AFTER = BEFORE, AFTER
    G.OUT = os.path.join(IMG, "demo-wipe-en.gif")
    return G.main()


def main():
    before, after = make_pair()
    make_compare(before, after)
    make_gif()
    return 0


if __name__ == "__main__":
    sys.exit(main())
