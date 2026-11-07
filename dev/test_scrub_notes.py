# -*- coding: utf-8 -*-
"""回归测试：注释（批注 / 便签）与书签标题里的隐私也必须被清掉。

正文打码用的是「抹除文本层 + 贴马赛克」，碰不到注释和书签这两类独立对象。
v1.4.3 起 redact() 末尾会再洗一遍，这里验证它确实生效。
"""

import os
import sys
import tempfile

# 默认写到临时目录，跑完不在仓库里留文件；需要留在指定位置时设 PDFMASK_TEST_DIR
os.environ.setdefault("PDFMASK_TEST_DIR", tempfile.mkdtemp(prefix="pdfmask-scrub-"))

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import pdfmask  # noqa: E402
from _testpaths import out  # noqa: E402

ID18 = "320582199207180019"
PHONE = "13812346780"
NAME = "陈嘉豪"
MAIL = "chenjiahao1992@163.com"

ok_all = True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""))


def build():
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 100), "姓名：%s" % NAME, fontname="china-s", fontsize=14)
    page.insert_text((60, 130), "手机：%s" % PHONE, fontname="china-s", fontsize=14)
    page.insert_text((60, 160), "身份证号：%s" % ID18, fontname="china-s", fontsize=14)
    page.insert_text((60, 190), "邮箱：%s" % MAIL, fontname="china-s", fontsize=14)
    page.insert_text((60, 240), "第二页正文（干净）", fontname="china-s", fontsize=14)

    # 1) 涉敏批注：内容里带手机号
    a1 = page.add_text_annot((100, 300), "回电 %s 即可" % PHONE)
    a1.set_info(title=NAME, content="回电 %s 即可" % PHONE)
    # 2) 涉敏便签：标题里带姓名、内容带身份证
    a2 = page.add_text_annot((100, 340), "身份证 %s" % ID18)
    a2.set_info(title=NAME, content="身份证 %s" % ID18)
    # 3) 干净的批注：不该被删
    a3 = page.add_text_annot((100, 380), "这里排版间距再调一下")
    a3.set_info(title="排版", content="这里排版间距再调一下")

    # 4) 书签：一条带手机号，一条干净
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((60, 100), "第三页", fontname="china-s", fontsize=14)
    doc.set_toc([[1, "第一章 联系人 %s" % PHONE, 1],
                 [1, "第二章 正常章节", 2]])
    path = out("scrub_notes_src.pdf")
    doc.save(path)
    doc.close()
    return path


def main():
    src = build()
    doc, findings = pdfmask.detect_document(src)
    pdfmask.redact(doc, findings)
    out_path = out("scrub_notes_dst.pdf")
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()

    d = pymupdf.open(out_path)

    # --- 注释 ---
    annots = []
    for page in d:
        annots.extend([str((a.info or {}).get("content") or "") + "|" +
                       str((a.info or {}).get("title") or "") for a in (page.annots() or [])])
    blob = "\n".join(annots)
    for probe in (PHONE, ID18, NAME):
        check("注释里不再出现 %s" % probe, probe not in blob, blob[:60])
    check("干净批注被保留", any("排版" in x for x in annots), str(len(annots)))

    # --- 书签 ---
    toc = d.get_toc()
    titles = "\n".join(t for _, t, _ in toc)
    check("书签标题里不再出现手机号", PHONE not in titles, titles.replace("\n", " / "))
    check("干净书签标题被保留", "第二章 正常章节" in titles)
    check("书签条数不变", len(toc) == 2, "共 %d 条" % len(toc))
    d.close()

    # --- 原始文件里的隐私确实会被正文打码带走 ---
    check("输出文件存在且非空", os.path.getsize(out_path) > 1000)
    print("\n结论:", "全部通过" if ok_all else "存在未通过项")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
