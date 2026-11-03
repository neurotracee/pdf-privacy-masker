# -*- coding: utf-8 -*-
"""把 pdfmask.py 里的 PROJECT_URL 同步到所有文档与 exe 属性。

改仓库地址时只需要改 pdfmask.py 里 PROJECT_URL 那一行，然后跑：

    python dev/sync_url.py

会更新仓库里所有文档（根目录 *.md、docs/*.md、使用说明.txt、version_info.txt）。
只替换本项目的地址（形如 github.com/<用户名>/pdf-privacy-masker），
不会碰到依赖项的 GitHub 链接。
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pdfmask  # noqa: E402

DOCS = ["README.md", "CHANGELOG.md", "DOCS.md", "NOTICE.md", "ADDITIONAL-TERMS.md",
        "使用说明.txt", "version_info.txt"]
DOCS += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "docs", "*.md")))

# 只匹配「本项目」的仓库路径，避免误伤 PyMuPDF / Pillow 等依赖的链接
PAT = re.compile(r"(?:https?://)?github\.com/[A-Za-z0-9_.\-]+/pdf-privacy-masker")


def main():
    url = pdfmask.PROJECT_URL
    if "REPLACE_ME" in url:
        print("[提示] PROJECT_URL 还是占位符，先改 pdfmask.py 再同步：%s" % url)
    changed = []
    for rel in DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
        new = PAT.sub(url, old)
        if new != old:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            changed.append(rel)
    if changed:
        print("已同步 %s -> %s" % (url, "、".join(changed)))
    else:
        print("文档里的地址已是最新：%s" % url)


if __name__ == "__main__":
    main()
