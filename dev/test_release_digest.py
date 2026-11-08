# -*- coding: utf-8 -*-
"""发布正文 → 更新弹窗文案的回归。

盯的是三件事：
  1. 顶上那句摘要必须在 100 字以内，而且能认得出发布页里写的「一句话」；
  2. 详细条目要按 Windows / 安卓 分开标注，正文里不能残留 Markdown 记号；
  3. 发布页写得随意（没有「一句话」、甚至没有小标题）时，宁可不显示也不能吐一堆记号。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pdfmask_update as U  # noqa: E402

ROOT = os.path.join(HERE, "..")
NOTES = os.path.join(ROOT, "release", "v1.4.4", "RELEASE-NOTES.md")

ok_all = True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    print(("[PASS] " if cond else "[FAIL] ") + name + (("  -> " + detail) if detail else ""))


def fake_release(body, ver="1.4.4"):
    return [{
        "tag_name": "v" + ver,
        "draft": False,
        "html_url": "https://github.com/neurotracee/pdf-privacy-masker/releases/tag/v" + ver,
        "body": body,
        "assets": [{
            "name": "PDFPrivacyMasker-%s.exe" % ver,
            "browser_download_url":
                "https://github.com/neurotracee/pdf-privacy-masker/releases/download/v%s/"
                "PDFPrivacyMasker-%s.exe" % (ver, ver),
        }],
    }]


def mask_leftover(text):
    """正文里不该再出现的 Markdown 记号。

    注意 `0512****1234`、`赵**` 这类打码示例本身带星号，必须原样留着，
    所以只把「成对加粗」认作残留，孤零零的星号不算。
    """
    bad = []
    if re.search(r"\*\*[^\s*][^*]*\*\*", text):
        bad.append("成对加粗 **")
    for token in ("](", "```", "## ", "__"):
        if token in text:
            bad.append(token)
    return bad


def main():
    body = open(NOTES, encoding="utf-8").read()

    # 走一遍真实入口：解析 GitHub 的 releases JSON
    got = U.parse_releases(json.loads(json.dumps(fake_release(body))), ".exe", U.GITHUB_PAGE)
    check("能从资产名认出最新版", got and "%d.%d.%d" % got["ver"] == "1.4.4")
    check("正文被带回来了", got and got.get("body") == body)

    d = U.parse_digest(got["body"])

    # --- 摘要 ---
    zh, en = d["brief"]["zh"], d["brief"]["en"]
    check("中文摘要非空", bool(zh), zh[:40])
    check("中文摘要 ≤100 字（实际 %d）" % len(zh), 0 < len(zh) <= U.MAX_BRIEF_ZH)
    check("中文摘要不是「更新级别」配置行", not zh.startswith("更新级别"))
    check("中文摘要没有 Markdown 记号", not mask_leftover(zh), str(mask_leftover(zh)))
    check("英文摘要非空", bool(en), en[:40])
    check("英文摘要 ≤%d 字符（实际 %d）" % (U.MAX_BRIEF_EN, len(en)), 0 < len(en) <= U.MAX_BRIEF_EN)

    # --- 详细条目 ---
    items = d["notes"]["zh"]
    check("中文条目数量合理（%d 条）" % len(items), 3 <= len(items) <= U.MAX_ITEMS)
    plats = [it["p"] for it in items]
    check("有条目标成 Windows", "win" in plats, str(plats))
    check("有条目标成安卓", "android" in plats, str(plats))
    check("每条都有标题和正文",
          all(it["t"] and it.get("b") for it in items))
    check("标题里不再残留平台标注",
          not any(re.search(r"[（(](Windows|安卓|Android)[^）)]*[）)]$", it["t"]) for it in items))
    joined = "\n".join("\n".join(it.get("b") or []) for it in items)
    check("条目标题/正文没有 Markdown 记号", not mask_leftover(joined), str(mask_leftover(joined)))
    check("打码示例的星号没被吃掉（0512****1234）", "0512****1234" in joined)
    check("下载章节不重复列进弹窗", not any("下载" in it["t"] for it in items))
    check("英文条目也解析出来了", len(d["notes"]["en"]) >= 3)

    # --- 兜底：发布页写得随意 ---
    plain = U.parse_digest("# v9.9.9\n\n这次就是修了几个小问题。\n\n## 修复\n\n- 某个按钮点不动。\n")
    check("没有「一句话」标记时用第一段兜底",
          plain["brief"]["zh"] == "这次就是修了几个小问题。", plain["brief"]["zh"])
    check("没有平台标注时归到「两端」", plain["notes"]["zh"][:1] and plain["notes"]["zh"][0]["p"] == "both")

    empty = U.parse_digest("")
    check("正文为空时摘要和条目都为空",
          empty["brief"]["zh"] == "" and empty["notes"]["zh"] == [] and empty["notes"]["en"] == [])

    onlytitle = U.parse_digest("# v9.9.9 版本说明\n\n更新级别：建议\n")
    check("只有标题和配置行时不瞎编摘要", onlytitle["brief"]["zh"] == "",
          onlytitle["brief"]["zh"])

    # --- 老版本发布正文（v1.4.3，没有「一句话」标记）也要能用 ---
    old = os.path.join(ROOT, "release", "v1.4.3", "RELEASE-NOTES.md")
    if os.path.exists(old):
        od = U.parse_digest(open(old, encoding="utf-8").read())
        check("老正文也能拿到摘要（%d 字）" % len(od["brief"]["zh"]),
              0 < len(od["brief"]["zh"]) <= U.MAX_BRIEF_ZH)
        check("老正文也能拆出条目（%d 条）" % len(od["notes"]["zh"]),
              len(od["notes"]["zh"]) >= 2)

    print("-" * 60)
    print("发布正文解析自检:", "全部通过" if ok_all else "存在未通过项")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
