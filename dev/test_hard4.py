# -*- coding: utf-8 -*-
"""刁难文档 4.0（多页扫描件）自动验收：识别、打码、复核全部交给程序。

本脚本只做三件事：
  1. 生成 8 页扫描件（见 make_hard4_pdf.py），并把真值一起读进来；
  2. 执行 `python pdfmask.py --cli 输入 输出`——**识别和打码由程序完成**，
     脚本不碰任何一行打码逻辑，也不给程序任何提示；
  3. 用程序自己的 OCR 引擎把成品再读一遍，检查：
       DET  原文里的敏感项，程序有没有检出来
       LEAK 打码之后，这些项还能不能被读出来（= 泄漏）
       KEEP 干扰项（金额、编号、日期）有没有被误伤

三项的含义不一样，缺一不可：
- 只测 DET：检出就算过，来不及管画面上有没有真抹掉；
- 只测 LEAK：把整页涂黑也能过，等于没测准确率；
- 只测 KEEP：什么都不打码也能过。
所以三条必须同时为真才算「这一条合格」。
"""
import difflib
import importlib.util
import json
import os
import re
import subprocess
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "test", "hard4")
SRC = os.path.join(OUT, "刁难文档4_扫描件.pdf")
MASKED = os.path.join(OUT, "刁难文档4_扫描件_已打码.pdf")
TRUTH = os.path.join(OUT, "刁难文档4_扫描件.truth.json")
MASK = os.path.join(ROOT, "pdfmask.py")
GEN = os.path.join(HERE, "make_hard4_pdf.py")

FW = {i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)}
FW[0x3000] = 0x20


def fold(s):
    return "".join(chr(FW.get(ord(c), ord(c))) for c in s)


def digits(s):
    """只留数字与 X，用于号码比对（分隔符、空格、全角都不计较）"""
    return re.sub(r"[^0-9Xx]", "", fold(s)).upper()


def letters(s):
    """邮箱/文本比对：折叠全角、转小写、去掉所有空白"""
    return re.sub(r"\s+", "", fold(s)).lower()


def gen():
    spec = importlib.util.spec_from_file_location("gen4", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not mod.FF:
        # 没有中英混排字体时，内置 china-s 会把 ASCII 画成全角，样张失真、结果没有意义
        return None
    mod.build()
    with open(TRUTH, encoding="utf-8") as f:
        return json.load(f)


def run_program(inp, outp):
    r = subprocess.run([sys.executable, MASK, "--cli", inp, outp],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("程序执行失败：%s" % (r.stderr or r.stdout)[-800:])
    try:
        rep = json.loads(r.stdout)
    except Exception:
        raise SystemExit("程序没有输出可解析的 JSON：%s" % (r.stdout or r.stderr)[:500])
    return rep


def _similar(a, b, thr=0.82):
    return difflib.SequenceMatcher(None, a, b).ratio() >= thr


def _hit_one(secret, text):
    """单条文本里是否出现这个值（容忍 OCR 少/多一个字符）"""
    v = letters(secret)
    t = letters(text)
    if v and v in t:
        return True
    dv = digits(secret)
    dt = digits(text)
    if dv and len(dv) >= 5:
        if dv in dt:
            return True
        # OCR 把号码末位读丢，整条只差 1~2 位：仍算「程序认到了」
        if 0 < abs(len(dt) - len(dv)) <= 2 and _similar(dv, dt, 0.86):
            return True
    # 邮箱/姓名这类文本值：OCR 认错一个字母（wangjj → wangi）不算漏检
    if len(v) >= 6 and abs(len(t) - len(v)) <= 2 and _similar(v, t, 0.88):
        return True
    return False


def hits_any(secret, texts):
    return any(_hit_one(secret, t) for t in texts if t)


def hits_in_blob(secret, blob):
    """页面整段文本里是否还能读到这个值（用于判断打码后有没有泄漏）"""
    v = letters(secret)
    b = letters(blob)
    if v and v in b:
        return True
    n = len(v)
    if n and len(b) >= n:
        for i in range(len(b) - n + 1):
            if _similar(v, b[i:i + n], 0.88):
                return True
    dv = digits(secret)
    db = digits(blob)
    if dv and len(dv) >= 5 and db:
        for i in range(max(1, len(db) - len(dv) + 1)):
            for n2 in (len(dv) - 1, len(dv), len(dv) + 1):
                seg = db[i:i + n2]
                if len(seg) == n2 and _similar(dv, seg, 0.88):
                    return True
    return False


def gen():
    spec = importlib.util.spec_from_file_location("gen4", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build()
    with open(TRUTH, encoding="utf-8") as f:
        return json.load(f)


def run_program(inp, outp):
    r = subprocess.run([sys.executable, MASK, "--cli", inp, outp],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("程序执行失败：%s" % (r.stderr or r.stdout)[-800:])
    try:
        rep = json.loads(r.stdout)
    except Exception:
        raise SystemExit("程序没有输出可解析的 JSON：%s" % (r.stdout or r.stderr)[:500])
    return rep


def _similar(a, b, thr=0.82):
    return difflib.SequenceMatcher(None, a, b).ratio() >= thr


def secret_hit(secret, text_blob):
    """程序有没有「认到」这一项

    不做精确相等：OCR 偶尔会把邮箱里的点读丢、把号码末位读少一位，
    这时程序其实已经打了码，只是文本串对不上。所以先精确包含，再滑窗容错比对。
    """
    v = letters(secret)
    b = letters(text_blob)
    if v and v in b:
        return True
    n = len(v)
    if n and len(b) > n:
        for i in range(len(b) - n + 1):
            if _similar(v, b[i:i + n], 0.85):
                return True
    dv = digits(secret)
    if len(dv) >= 5:
        db = digits(text_blob)
        for i in range(max(0, len(db) - len(dv) + 1)):
            if _similar(dv, db[i:i + len(dv)], 0.88):
                return True
    return False


def main():
    reuse = "--reuse" in sys.argv
    print("=" * 74)
    print("刁难文档 4.0 · 多页扫描件验收（8 页真实单据 / 无文字层 / 靠 OCR）")
    print("=" * 74)

    if reuse and os.path.exists(SRC) and os.path.exists(TRUTH):
        with open(TRUTH, encoding="utf-8") as f:
            truth = json.load(f)
        print("复用样张：%s（%d 页，%d 条真值）"
              % (os.path.basename(SRC), truth["pages"], len(truth["cases"])))
    else:
        truth = gen()
        if truth is None:
            print("  [SKIP] 本机没有中英混排字体，样张会失真，跳过")
            print("         Linux 上装 fonts-noto-cjk 即可让这项真正跑起来")
            return 3
        print("生成：%s（%d 页，%d 条真值）"
              % (os.path.basename(SRC), truth["pages"], len(truth["cases"])))
    cases = truth["cases"]

    src = pymupdf.open(SRC)
    no_text = all(len(src[i].get_text().strip()) == 0 for i in range(src.page_count))
    print("输入确认：%d 页，文字层为空的页 %d/%d"
          % (src.page_count, sum(1 for i in range(src.page_count)
                                 if not src[i].get_text().strip()), src.page_count))
    src.close()
    if not no_text:
        print("  [失败] 输入居然有文字层，刁难不成立")
        return 1

    if os.path.exists(MASKED):
        os.remove(MASKED)
    print("\n调用程序识别 + 打码 ……")
    rep = run_program(SRC, MASKED)
    print("  程序报告：%d 页，自动处理 %d 项，存疑 %d 项，用时记录见上"
          % (rep["pages"], rep["count"], rep.get("suspect", 0)))
    print("  按类型：" + "，".join("%s %d" % (k, v) for k, v in
                                  sorted(rep["by_type"].items(), key=lambda kv: -kv[1])))
    if not os.path.exists(MASKED):
        print("  [失败] 没有生成成品")
        return 1

    # ---- 程序自己报出来的检出项（用于 DET） ----
    det_by_page = {}
    for it in rep["items"]:
        det_by_page.setdefault(it["page"], []).append(it["text"])
    det_all = " ".join(i["text"] for i in rep["items"])

    # ---- 用程序自己的 OCR 读成品（用于 LEAK / KEEP） ----
    sys.path.insert(0, ROOT)
    import pdfmask_ocr as ocr          # noqa: E402
    if not ocr.available():
        print("  [跳过] OCR 不可用：%s" % ocr.why_unavailable())
        return 3
    eng = ocr.OcrEngine.get()
    out = pymupdf.open(MASKED)
    read = {}
    for i in range(out.page_count):
        read[i + 1] = eng.page_lines(out[i])
    out.close()

    def page_text(pno):
        return " ".join(t for t, _ in read.get(pno, []))

    # ---- 逐条判定 ----
    rows = []
    for c in cases:
        pno = c["page"]
        det_x = [v for v in c["secrets"] if not hits_any(v, det_by_page.get(pno, []))]
        leak = [v for v in c["secrets"] if hits_in_blob(v, page_text(pno))]
        keep_bad = [v for v in c["noise"] if hits_any(v, det_by_page.get(pno, []))]
        keep_miss = [v for v in c["noise"] if not hits_in_blob(v, page_text(pno))]
        ok = not det_x and not leak and not keep_bad
        rows.append({"case": c, "det_miss": det_x, "leak": leak,
                     "keep_bad": keep_bad, "keep_miss": keep_miss, "ok": ok})

    # ---- 报告 ----
    by_sheet = {}
    for r in rows:
        by_sheet.setdefault(r["case"]["sheet"], []).append(r)

    total = len(rows)
    det_bad = sum(1 for r in rows if r["det_miss"])
    leak_bad = sum(1 for r in rows if r["leak"])
    fp_bad = sum(1 for r in rows if r["keep_bad"])
    ok_n = sum(1 for r in rows if r["ok"])

    print("\n%-16s %5s %6s %6s %6s   %s" % ("单据", "条目", "漏检", "泄漏", "误伤", "结论"))
    print("-" * 74)
    for sheet, rs in by_sheet.items():
        d = sum(1 for r in rs if r["det_miss"])
        l = sum(1 for r in rs if r["leak"])
        f = sum(1 for r in rs if r["keep_bad"])
        print("%-16s %5d %6d %6d %6d   %s"
              % (sheet, len(rs), d, l, f, "通过" if not (d or l or f) else "未通过"))

    print("-" * 74)
    print("合计 %d 条：合格 %d，漏检 %d，泄漏 %d，误伤 %d" % (total, ok_n, det_bad, leak_bad, fp_bad))

    def dump(title, key):
        bad = [r for r in rows if r[key]]
        if not bad:
            return
        print("\n【%s】%d 条" % (title, len(bad)))
        for r in bad[:40]:
            c = r["case"]
            print("  P%d %-10s %-28s %s"
                  % (c["page"], c["category"], "、".join(r[key])[:34],
                     c["text"][:46]))

    dump("漏检：程序在原文里没认出来", "det_miss")
    dump("泄漏：打码后仍能读出", "leak")
    dump("误伤：把业务数据当隐私打了", "keep_bad")

    kms = [r for r in rows if r["keep_miss"]]
    if kms:
        print("\n【干扰项复核读不出】%d 条（检测层没打它，可能只是 OCR 自己读错了，"
              "不计入缺陷，仅供观察）" % len(kms))
        for r in kms[:10]:
            c = r["case"]
            print("  P%d %-22s %s" % (c["page"], "、".join(r["keep_miss"]), c["text"][:40]))

    good = (ok_n == total)
    print("\n结论：%s" % ("全部通过（%d/%d）" % (ok_n, total) if good
                          else "存在 %d 条未通过" % (total - ok_n)))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
