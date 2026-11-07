# -*- coding: utf-8 -*-
"""生成跨端一致性基准：同一份 PDF，Python 端识别出什么，Kotlin 端必须一致。

用法：
    python dev/gen_rules_golden.py          # 重新生成 test/rules_golden.json

产物 `test/rules_golden.json` 进仓库；安卓单元测试
`android/app/src/test/.../RuleParityTest.kt` 读同一份 PDF + 这份基准，
用 Kotlin 的 Detector 再跑一遍，逐条比对 page / type / text。

只要两端的规则发生漂移（改了一边忘了另一边），测试立刻变红。
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import pdfmask  # noqa: E402
from _testpaths import IN_DIR  # noqa: E402

SAMPLE = "测试文档_含隐私.pdf"
OUT = os.path.join(os.path.dirname(HERE), "test", "rules_golden.json")


def main():
    src = os.path.join(IN_DIR, SAMPLE)
    if not os.path.exists(src):
        print("样本不存在:", src)
        return 1
    doc, findings = pdfmask.detect_document(src)
    items = sorted(
        ({"page": int(f["page"]), "type": f["type"], "text": f["text"].strip()}
         for f in findings if f.get("type") != "manual"),
        key=lambda d: (d["page"], d["type"], d["text"]))
    data = {
        "source": "test/" + SAMPLE,
        "note": "由 dev/gen_rules_golden.py 生成，请勿手改；改规则后重新生成并与安卓端对齐",
        "count": len(items),
        "findings": items,
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("已写入 %s（%d 条）" % (OUT, len(items)))
    by_type = {}
    for it in items:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1
    print("分布:", ", ".join("%s=%d" % kv for kv in sorted(by_type.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
