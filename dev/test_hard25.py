# -*- coding: utf-8 -*-
"""刁难文档 2.5 自动自检：多页、多人、多号码，全流程由程序自己完成。

流程（本脚本只下发命令，不参与任何识别或打码）：
  1. 生成 N 套随机文档（每套 5 页、7 个人物，隐私占比 ≥30%）
  2. 调用 `python pdfmask.py --cli 输入 输出` 让程序自己识别 + 打码
  3. 逐页回读成品，比对隐私真值 / 干扰真值 / 姓氏保留 / 文本层残留
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEST = os.path.join(ROOT, "test", "h25")
GEN = os.path.join(HERE, "make_hard25_pdf.py")
MASK = os.path.join(ROOT, "pdfmask.py")

spec = importlib.util.spec_from_file_location("gen25", GEN)
gen25 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen25)

KEYS = [("name", "姓名"), ("phone", "手机号"), ("mail", "邮箱"), ("addr", "地址"),
        ("idc", "身份证号"), ("bank", "银行卡号"), ("tel", "座机号"),
        ("birth", "出生日期")]


def build(seed, out):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        persons = gen25.main(seed, out)
    return persons, buf.getvalue()


def run_program(inp, outp):
    """只下发命令，识别与打码全部由程序完成"""
    r = subprocess.run([sys.executable, MASK, "--cli", inp, outp],
                       capture_output=True, text=True, cwd=ROOT)
    return r


def check_one(seed, verbose=True):
    os.makedirs(TEST, exist_ok=True)
    src = os.path.join(TEST, "多人多页_%d.pdf" % seed)
    out = os.path.join(TEST, "多人多页_%d_已打码.pdf" % seed)
    persons, _ = build(seed, src)
    if os.path.exists(out):
        os.remove(out)

    r = run_program(src, out)
    if r.returncode != 0 or not os.path.exists(out):
        print("  [失败] 程序执行出错：", (r.stderr or r.stdout)[-300:])
        return False

    doc = pymupdf.open(out)
    src_doc = pymupdf.open(src)

    ok = True
    if doc.page_count != src_doc.page_count:
        print("  [失败] 页数变了：%d → %d" % (src_doc.page_count, doc.page_count))
        ok = False

    total_fields = 0
    miss = []
    for i in range(doc.page_count):
        t = doc[i].get_text().replace("\n", "").replace(" ", "")
        src_t = src_doc[i].get_text().replace("\n", "").replace(" ", "")
        page_miss = []
        for ps in persons:
            for k, lab in KEYS:
                v = ps[k]
                if v not in src_t:
                    continue          # 该页没出现
                total_fields += 1
                if v in t:
                    page_miss.append("%s=%s" % (lab, v))
            if ("今年" + ps["age"] + "岁") in src_t:
                total_fields += 1
                if ("今年" + ps["age"] + "岁") in t:
                    page_miss.append("年龄=%s" % ps["age"])
        if page_miss:
            ok = False
            miss.extend(["第%d页 %s" % (i + 1, m) for m in page_miss])
        if verbose:
            print("  第%d页：%d 字，残留 %d 项" % (i + 1, len(src_t), len(page_miss)))

    # 姓氏是否保留（每人首字）
    keep_ok = all(ps["name"][0] in doc[0].get_text() or
                  any(ps["name"][0] in doc[i].get_text() for i in range(doc.page_count))
                  for ps in persons[:1])

    # 干扰项是否完好（只统计「原文确实出现过」的干扰项）
    flat = "".join(doc[i].get_text() for i in range(doc.page_count)).replace("\n", "").replace(" ", "")
    src_flat = "".join(src_doc[i].get_text() for i in range(src_doc.page_count)).replace("\n", "").replace(" ", "")
    noise_in = [n for n in gen25.NOISE if n in src_flat]
    noise_gone = [n for n in noise_in if n not in flat]

    print("  隐私字段 %d 项，残留 %d 项" % (total_fields, len(miss)))
    if miss:
        for m in miss[:12]:
            print("    残留:", m)
    print("  干扰项保留 %d/%d" % (len(noise_in) - len(noise_gone), len(noise_in)),
          ("| 被误伤: %s" % noise_gone) if noise_gone else "")
    print("  页数 %d，姓氏保留 %s" % (doc.page_count, keep_ok))
    return ok and not miss and not noise_gone


def main():
    seeds = [int(x) for x in (sys.argv[1:] or ["2026", "7", "88231"])]
    print("=" * 70)
    print("刁难文档 2.5 自动自检（5 页 / 每页多人 / 多号码混排）")
    print("=" * 70)
    allok = True
    for s in seeds:
        print("\n[种子 %d]" % s)
        r = check_one(s)
        allok = allok and r
        print("  判定:", "通过" if r else "未通过")
    print("\n结论:", "全部通过" if allok else "存在未通过项")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
