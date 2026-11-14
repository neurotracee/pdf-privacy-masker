# -*- coding: utf-8 -*-
"""OCR 冒烟测试：造一份「只有图片、没有文字层」的表单，看能不能认出来并给出坐标。

用法：
    python dev/test_ocr.py            # 用内置样张
    python dev/test_ocr.py <pdf>      # 用真实扫描件
"""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import pymupdf  # noqa: E402

import pdfmask_ocr as ocr  # noqa: E402

USED_FALLBACK = [False]      # 样张是否退回了内置 china-s（见 font_faithful）

LINES = [
    ("姓名", "张伟"),
    ("性别", "男"),
    ("出生日期", "1990年3月7日"),
    ("身份证号", "110101199003071234"),
    ("手机号码", "13800138000"),
    ("银行卡号", "6222020200112233445"),
    ("电子邮箱", "zhangwei1990@example.com"),
    ("家庭住址", "北京市朝阳区建国路88号院3号楼1201室"),
    ("工作单位", "北京某某科技有限公司"),
    ("会议日期", "2026年11月20日"),
    ("合同金额", "人民币 128000 元"),
]


def _pick_font(page):
    """优先用系统里真实的中英文字体，退化到 PyMuPDF 内置 CJK 字体

    内置 china-s 会把 ASCII 也渲染成全角字形，和真实扫描件差得远，
    用它测识别质量会失真（全角那条单独在 test_ocr_fold 里测）。
    """
    import glob
    for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyh.ttf",
                 "C:/Windows/Fonts/simhei.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.isfile(path):
            try:
                page.insert_font(fontname="F0", fontfile=path)
                return "F0"
            except Exception:
                pass
    for path in glob.glob("/usr/share/fonts/**/*CJK*.ttc", recursive=True):
        try:
            page.insert_font(fontname="F0", fontfile=path)
            return "F0"
        except Exception:
            pass
    USED_FALLBACK[0] = True
    return "china-s"


def font_faithful() -> bool:
    """样张是否用了真实的中英文混排字体

    退回内置 china-s 时，连 ASCII 都会被画成全角字形，和真实扫描件差得远，
    识别结果天然会失真（'zhangwei' 会读成 'lhangeil'）。这种情况下端到端
    测试应当跳过而不是判失败——错的是样张，不是程序。
    """
    return not USED_FALLBACK[0]


def build_form(path):
    """造一份带文字层的表单，再把它「拍成照片」变成纯图片 PDF"""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    font = _pick_font(page)
    y = 90
    for label, value in LINES:
        page.insert_text((70, y), "%s：" % label, fontname=font, fontsize=11)
        page.insert_text((170, y), value, fontname=font, fontsize=11)
        y += 34
    doc.save(path.replace(".png.pdf", "_text.pdf"))
    doc.close()

    # 渲染成图片 → 重建一份「没有文字层」的 PDF
    src = pymupdf.open(path.replace(".png.pdf", "_text.pdf"))
    pix = src[0].get_pixmap(matrix=pymupdf.Matrix(200 / 72.0, 200 / 72.0), alpha=False)
    img_pdf = pymupdf.open()
    p2 = img_pdf.new_page(width=595, height=842)
    p2.insert_image(p2.rect, pixmap=pix)
    img_pdf.save(path)
    img_pdf.close()
    src.close()
    return path


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        made = None
    else:
        path = os.path.join(tempfile.gettempdir(), "pdfmask_ocr_sample.png.pdf")
        made = build_form(path)

    if not ocr.available():
        print("[FAIL] OCR 不可用：", ocr.why_unavailable())
        return 1

    doc = pymupdf.open(path)
    page = doc[0]

    units = ocr.page_text_units(page)
    print("页面：字符 %d / 图片 %d / 覆盖 %.0f%%  需要 OCR=%s"
          % (units[0], units[1], units[2] * 100, ocr.needs_ocr(page)))

    t0 = time.time()
    eng = ocr.OcrEngine.get()
    t_load = time.time() - t0

    t0 = time.time()
    lines = eng.page_lines(page)
    t_run = time.time() - t0

    print("模型加载 %.2fs / 识别 %.2fs，共 %d 行" % (t_load, t_run, len(lines)))
    print("-" * 66)
    for text, entries in lines:
        print(text)

    # 精度检查：关键号码是否被完整认出
    joined = "".join(t for t, _ in lines).replace(" ", "")
    need = ["13800138000", "110101199003071234", "6222020200112233445"]
    print("-" * 66)
    ok = True
    for n in need:
        hit = n in joined
        ok = ok and hit
        print("  %-22s %s" % (n, "认出" if hit else "** 漏了 **"))

    # 坐标检查：第一个字与行框的关系是否合理
    for text, entries in lines[:2]:
        chars = [(c, r) for c, r in entries if r]
        if chars:
            print("  行「%s」首字 x0=%.1f 末字 x1=%.1f 行高=%.1f"
                  % (text[:10], chars[0][1][0], chars[-1][1][2],
                     chars[0][1][3] - chars[0][1][1]))

    doc.close()
    if made:
        for p in (made, made.replace(".png.pdf", "_text.pdf")):
            try:
                os.remove(p)
            except Exception:
                pass
    print("-" * 66)
    print("结论：", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
