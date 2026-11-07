# -*- coding: utf-8 -*-
"""刁难文档 2.0 对比测试：隐私真值召回 + 干扰信息误报"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pdfmask  # noqa: E402
import make_hard2_pdf as T  # noqa: E402

from _testpaths import out
SRC = out("刁难文档2_纯段落.pdf")

doc, fs = pdfmask.detect_document(SRC)
src_text = "".join(p.get_text() for p in doc)
src_flat = src_text.replace("\n", "").replace(" ", "")

print("=" * 74)
print("刁难文档 2.0 对比测试（一整段叙述，零字段标签，隐私与干扰混排）")
print("=" * 74)
print("命中的打码项共 %d 处\n" % len(fs))

print("【一】隐私信息召回（共 %d 项）" % len(T.TRUTH))
hit_n = miss = 0
missed = []
for kind, val in T.TRUTH:
    got = [f for f in fs if val in f["text"] or f["text"] in val]
    if got:
        hit_n += 1
        note = got[0].get("note", "")
        print("  [命中] %-6s %-28s %s" % (kind, val, note))
    else:
        miss += 1
        missed.append((kind, val))
        print("  [漏检] %-6s %-28s" % (kind, val))
print("\n  召回: %d/%d = %.1f%%" % (hit_n, len(T.TRUTH), hit_n * 100.0 / len(T.TRUTH)))

print("\n【二】干扰信息误报（共 %d 项，均不应被打码）" % len(T.NOISE))
fp = 0
for val in T.NOISE:
    bad = [f for f in fs if val and (val in f["text"] or f["text"] == val)]
    if bad:
        fp += 1
        print("  [误打] %-22s -> %s %r" % (val, bad[0]["type"], bad[0]["text"]))
    else:
        print("  [正常] %-22s" % val)
print("\n  误报: %d/%d" % (fp, len(T.NOISE)))

print("\n【三】打码后文本层残留检查")
DST = out("刁难文档2_打码后.pdf")
pdfmask.cli(SRC, DST, verbose=False)
import pymupdf  # noqa: E402

out = pymupdf.open(DST)
otext = "".join(p.get_text() for p in out).replace("\n", "").replace(" ", "")
leak = [v for _, v in T.TRUTH if v in otext]
print("  隐私残留:", "无" if not leak else leak)
kept = [v for v in T.NOISE if v in otext]
print("  干扰保留: %d/%d" % (len(kept), len(T.NOISE)))
print("  姓氏「苏」是否保留:", "苏" in otext)

print("\n【四】结论")
print("  隐私召回 %d/%d，误报 %d 处，漏检项：" % (hit_n, len(T.TRUTH), fp))
for kind, val in missed:
    print("    - %s：%s" % (kind, val))

ok = (miss == 0 and fp == 0 and not leak and len(kept) == len(T.NOISE))
print("\n  判定:", "通过" if ok else "未通过")
sys.exit(0 if ok else 1)
