# -*- coding: utf-8 -*-
"""端到端：纯图片 PDF（无文字层）→ 自动识别 → 打码 → 再识别一次确认读不出来

这是「扫描件能不能自动打码」的硬验证：
1. 输入页没有任何文字层，识别只能靠 OCR；
2. 打码后重新渲染再跑一次 OCR，原始号码必须一个都读不出来；
3. 不该打码的内容（会议日期、合同金额）必须仍然可读。
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import pymupdf  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("t", os.path.join(HERE, "test_ocr.py"))
_sample = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_sample)

import pdfmask  # noqa: E402
import pdfmask_ocr as ocr  # noqa: E402

SENSITIVE = {
    "身份证号": "110101199003071234",
    "手机号码": "13800138000",
    "银行卡号": "6222020200112233445",
    "电子邮箱": "zhangwei1990@example.com",
    "出生日期": "1990年3月7日",
}
KEEP = ["2026年11月20日", "128000"]          # 会议日期、合同金额：不该被打码


def render_text(page, zoom=2.5):
    """把页面渲染成图，跑一次 OCR，返回拼起来的所有文字"""
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    import numpy as np
    from PIL import Image
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    tmp = pymupdf.open()
    p = tmp.new_page(width=page.rect.width, height=page.rect.height)
    p.insert_image(p.rect, pixmap=pix)
    eng = ocr.OcrEngine.get()
    lines = eng.page_lines(tmp[0])
    tmp.close()
    return "".join(t for t, _ in lines).replace(" ", "")


def main():
    tmp = tempfile.gettempdir()
    src = os.path.join(tmp, "pdfmask_e2e_in.png.pdf")
    out = os.path.join(tmp, "pdfmask_e2e_out.pdf")
    _sample.build_form(src)

    if not _sample.font_faithful():
        # 本机没有中英文混排字体时，样张里的 ASCII 会被画成全角字形，
        # 识别结果必然失真（错在样张，不在程序），所以跳过而不是判失败。
        print("本机没有可用的中英文混排字体（msyh / Noto CJK），样张会失真，跳过。")
        print("  Linux 上装一个即可：sudo apt-get install -y fonts-noto-cjk")
        return 3

    doc = pymupdf.open(src)
    print("输入页文字字符数 =", ocr.page_text_units(doc[0])[0], "（0 表示确实没有文字层）")
    assert ocr.page_text_units(doc[0])[0] == 0, "样张必须没有文字层"

    fs = pdfmask.detect(doc)
    print("识别出 %d 处敏感信息：" % len(fs))
    vals = " | ".join("%s=%s" % (f["type"], f.get("text") or f.get("value") or "") for f in fs)
    print(" ", vals[:300])

    joined = "".join(str(f.get("text") or "") for f in fs)
    print("-" * 66)
    ok = True
    for label, val in SENSITIVE.items():
        hit = any(val in str(f.get("text") or "") for f in fs)
        ok = ok and hit
        print("  识别 %-8s %-22s %s" % (label, val[:20], "找到" if hit else "** 漏了 **"))

    for keep in KEEP:
        bad = [f for f in fs if keep in str(f.get("text") or "")]
        if bad:
            ok = False
            print("  ** 误打码 **  %s" % keep)
    print("  误打码检查：%s" % ("无" if ok else "有问题"))

    pdfmask.redact(doc, fs)
    doc.save(out)
    doc.close()

    print("-" * 66)
    chk = pymupdf.open(out)
    left = render_text(chk[0])
    for label, val in SENSITIVE.items():
        leaked = val in left
        ok = ok and not leaked
        print("  打码后 %-8s %s" % (label, "** 还能读出 **" if leaked else "已读不出"))
    for keep in KEEP:
        alive = keep in left
        ok = ok and alive
        print("  打码后保留 %-14s %s" % (keep, "仍可读" if alive else "** 被抹掉了 **"))
    chk.close()

    for p in (src, src.replace(".png.pdf", "_text.pdf"), out):
        try:
            os.remove(p)
        except Exception:
            pass
    print("-" * 66)
    print("结论：", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
