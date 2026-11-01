# -*- coding: utf-8 -*-
"""刁难文档 3.0 验收：纯段落、零标签、5 页 20 人。

本脚本只负责「生成文档 → 下命令 → 回读结果」，识别与打码全部由 pdfmask 自己完成。
检查项：
  1. 每人 8 项隐私 + 年龄，逐项召回（姓名同时按 2/3/4 字分组统计）
  2. 打码后文本层残留是否为 0
  3. 干扰项（会议日期、合同号、车牌、快递单、金额…）是否原样保留
  4. 姓氏是否保留（只遮名字）
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
TEST = os.path.join(ROOT, "test", "h30")
GEN = os.path.join(HERE, "make_hard3_pdf.py")
MASK = os.path.join(ROOT, "pdfmask.py")

sys.path.insert(0, ROOT)
import pdfmask  # noqa: E402

spec = importlib.util.spec_from_file_location("gen30", GEN)
gen30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen30)

FIELDS = [("name", "姓名"), ("phone", "手机号"), ("idc", "身份证号"), ("bank", "银行卡号"),
          ("mail", "邮箱"), ("addr", "地址"), ("birth", "出生日期"), ("gender", "性别"),
          ("age", "年龄"), ("tel", "座机号")]
TYPE_OF = {"idc": "idcard", "bank": "bankcard", "mail": "email", "addr": "address"}


def norm(s):
    return s.replace(" ", "").replace("\n", "")


def build(seed, out):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        persons = gen30.main(seed, out)
    return persons


def run_program(inp, outp):
    return subprocess.run([sys.executable, MASK, "--cli", inp, outp],
                          capture_output=True, text=True, cwd=ROOT)


def check_one(seed, verbose=True):
    os.makedirs(TEST, exist_ok=True)
    src = os.path.join(TEST, "纯段落_%d.pdf" % seed)
    out = os.path.join(TEST, "纯段落_%d_已打码.pdf" % seed)
    persons = build(seed, src)
    if os.path.exists(out):
        os.remove(out)

    # ---- 一、程序自己的检测结果（逐项对比） ----
    src_doc = pymupdf.open(src)
    findings = pdfmask.detect(src_doc)
    got = {}
    for f in findings:
        got.setdefault(f["type"], []).append(norm(f["text"]))

    miss = []
    for i, ps in enumerate(persons, 1):
        for k, label in FIELDS:
            v = ps[k] if k != "age" else ps["age"]
            t = TYPE_OF.get(k, k)
            hit = any(v == g or (k == "addr" and v in g) for g in got.get(t, []))
            if not hit:
                miss.append((i, ps["name"], label, v))

    if verbose:
        print("\n【一】逐项召回")
        for i, ps in enumerate(persons, 1):
            row = []
            for k, label in FIELDS:
                v = ps[k] if k != "age" else ps["age"]
                t = TYPE_OF.get(k, k)
                ok = any(v == g or (k == "addr" and v in g) for g in got.get(t, []))
                row.append("·" if ok else "✗")
            print("  %2d. %-6s(%d字) %s" % (i, ps["name"], len(ps["name"]), " ".join(row)))
        print("  字段顺序: " + " ".join(l for _, l in FIELDS))

        print("\n【二】姓名按字数分组")
        for ln, label in ((2, "两字名"), (3, "三字名"), (4, "复姓四字")):
            sub = [p for p in persons if len(p["name"]) == ln]
            if not sub:
                continue
            hit = sum(1 for p in sub if any(p["name"] == g for g in got.get("name", [])))
            print("  %s: %d/%d" % (label, hit, len(sub)))

    # ---- 二、程序自己打码，回读残留 ----
    r = run_program(src, out)
    if r.returncode != 0 or not os.path.exists(out):
        print("  [失败] 程序执行出错：", (r.stderr or r.stdout)[-400:])
        return False, persons, miss

    masked = pymupdf.open(out)
    pages = [norm(pg.get_text()) for pg in masked]
    whole = "".join(pages)

    residual = []
    for i, ps in enumerate(persons, 1):
        for k in ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth"):
            if norm(ps[k]) in whole:
                residual.append((i, ps["name"], k, ps[k]))
        if norm(ps["age"] + "岁") in whole:
            residual.append((i, ps["name"], "age", ps["age"]))

    src_flat = norm("".join(pg.get_text() for pg in src_doc))
    noise_in = [n for n in gen30.NOISE + gen30.TIMES if norm(n) in src_flat]
    noise_gone = [n for n in noise_in if norm(n) not in whole]

    sur_ok = 0
    for ps in persons:
        nm = ps["name"]
        keep = 2 if (len(nm) >= 3 and nm[:2] in pdfmask.COMPOUND_SURNAME) else 1
        if nm[:keep] in whole:
            sur_ok += 1

    if verbose:
        print("\n【三】打码后的文本层")
        for i, t in enumerate(pages, 1):
            n = sum(1 for ps in persons
                    if norm(ps["idc"]) in t or norm(ps["bank"]) in t or norm(ps["phone"]) in t)
            print("  第%d页：%d 字，残留号码组 %d" % (i, len(t), n))
        print("  隐私字段 %d 项，残留 %d 项" % (len(persons) * 9, len(residual)))
        for x in residual[:12]:
            print("    残留: 第%d人 %s %s=%s" % x)
        print("  干扰项保留 %d/%d" % (len(noise_in) - len(noise_gone), len(noise_in)),
              ("| 被误伤: %s" % noise_gone) if noise_gone else "")
        print("  姓氏保留 %d/%d" % (sur_ok, len(persons)))
        if miss:
            print("  漏检明细：")
            for x in miss[:12]:
                print("    第%d人 %s 的 %s 未识别 -> %s" % x)

    ok = (not residual) and (not miss) and (not noise_gone) and sur_ok == len(persons)
    return ok, persons, miss


def main():
    seeds = [int(x) for x in (sys.argv[1:] or ["2026", "7", "88231", "5150"])]
    print("=" * 72)
    print("刁难文档 3.0 自检 —— 纯段落、零标签、5 页 20 人、无表格")
    print("=" * 72)
    allok = True
    for s in seeds:
        print("\n[种子 %d]" % s)
        ok, persons, miss = check_one(s)
        allok = allok and ok
        print("  判定:", "通过" if ok else "未通过")
    print("\n结论:", "全部通过" if allok else "存在未通过项")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
