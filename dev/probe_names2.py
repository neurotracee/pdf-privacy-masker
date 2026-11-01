# -*- coding: utf-8 -*-
"""姓名识别探针 2.0：随机造 200 个两字名 / 200 个三字名，套进 12 种叙述句式，
统计召回率，看「三字名」是不是系统性地比「两字名」差。"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymupdf
import pdfmask

F = "china-s"


def fake_entries(text):
    return [(ch, pymupdf.Rect(i * 10.0, 0, i * 10.0 + 10.0, 10.0)) for i, ch in enumerate(text)]


def check(text, nm):
    ent = fake_entries(text)
    fs = pdfmask._scan_line(text, ent, 0)
    idx = text.find(nm)
    keep = 2 if (len(nm) >= 3 and nm[:2] in pdfmask.COMPOUND_SURNAME) else 1
    x0 = idx * 10.0 + keep * 10.0 + 0.5
    x1 = idx * 10.0 + len(nm) * 10.0 - 0.5
    for f in fs:
        if f["type"] != "name":
            continue
        r = f["rect"]
        if r.x0 <= x0 and r.x1 >= x1:
            return True, [g["text"] for g in fs if g["type"] == "name"]
    return False, [g["text"] for g in fs if g["type"] == "name"]


# 句式模板：{N} 是人名占位
TEMPLATES = [
    "{N}今天上午到网点办理业务，带齐了全部材料。",
    "{N}说这件事还需要再确认一次。",
    "{N}负责本次合同的审核与盖章。",
    "经核实，{N}于2024年3月入职本公司。",
    "后来我们才知道，{N}当时并不在现场。",
    "技术部安排{N}跟进这个项目，期限两周。",
    "陪同前来的还有{N}，由她负责登记。",
    "客户{N}当场表示同意这个方案。",
    "{N}已经完成了资料整理工作，并于当天提交。",
    "这份材料是{N}整理的，签字也是他本人的。",
    "{N}向柜员出示了本人身份证复印件。",
    "会议决定由{N}牵头，组织后续跟进工作。",
    "{N}、王建国、李静三个人一起到了现场。",
    "同行的{N}在旁边核对清单，说有出入。",
    "{N}在核对清单时发现有两处信息不一致。",
    "{N}把登记表交到了窗口，然后离开。",
]


def main(seed=7):
    rnd = random.Random(seed)
    names2, names3 = [], []
    sur = list(pdfmask.SURNAME_1)
    giv = [c for c in pdfmask.GIVEN_CHARS]
    for _ in range(200):
        names2.append(rnd.choice(sur) + rnd.choice(giv))
    for _ in range(200):
        names3.append(rnd.choice(sur) + rnd.choice(giv) + rnd.choice(giv))

    stat = {2: [0, 0], 3: [0, 0]}
    fails = []
    for names, ln in ((names2, 2), (names3, 3)):
        for nm in names:
            tpl = rnd.choice(TEMPLATES)
            sent = tpl.replace("{N}", nm)
            ok, got = check(sent, nm)
            stat[ln][1] += 1
            stat[ln][0] += ok
            if not ok:
                fails.append((ln, nm, sent, got))
    for ln in (2, 3):
        print("%d 字名: %d/%d = %.1f%%" % (ln, stat[ln][0], stat[ln][1],
                                           stat[ln][0] * 100.0 / stat[ln][1]))
    print("\n漏识别 %d 例：" % len(fails))
    for ln, nm, sent, got in fails[:40]:
        print("  %s | %s | 识别到:%s" % (nm, sent, got))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
