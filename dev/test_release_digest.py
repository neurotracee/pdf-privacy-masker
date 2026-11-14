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
RELEASE_DIR = os.path.join(ROOT, "release")

# 发布正文放在 release/<tag>/ 里，而 release/ 是产物目录（不进仓库），
# 所以 CI 里没有真实样本。没有时用下面这段内置样本：结构与真实正文一致
# （一句话 / 中英双语 / 分平台标注 / 一个应当被过滤的下载章节），
# 断言强度不打折。本地有真实正文时仍然优先用真实的。
INLINE_NOTES = """# v9.9.9 版本说明（Windows + 安卓）

**中文** | [English](#v999-release-notes-windows--android)

更新级别：建议

> **一句话**：修好了安卓更新包变成压缩包、默认更新源乱跳、返回手势直接退出这三个问题。

这一版修的都是用着用着才撞上的问题，三条都堵住了。

---

## 1. 修复：关标签页前先问一句（Windows）

**现象**：直接关浏览器标签，未保存的编辑全丢。

**改法**：关闭前拦一下，有未保存内容才提示。

## 2. 修复：默认更新源乱跳（Windows + 安卓）

**改法**：按系统语言与时区判断，界面语言不参与，启动时只算一次。

## 3. 修复：更新包变成压缩包（安卓）

**改法**：改为应用内下载，校验通过后交给系统安装器。

## 4. 修复：返回手势直接退出（安卓）

**改法**：返回时先问一句，可以保存后离开。

## 5. 改进：弱网下的超时（Windows + 安卓）

**改法**：单通道 8 秒放宽到 10 秒，减少误判。

## 6. 下载

- `PDFPrivacyMasker-9.9.9.exe`
- `PDFPrivacyMasker-9.9.9-arm64.apk`

---

# v9.9.9 Release Notes (Windows + Android)

**中文** | [English](#v999-release-notes-windows--android)

> **In one line**: Fixed archive-named Android updates, a flipping default source, and back gestures quitting the app.

All three were things you only hit in real use.

---

## 1. Fixed: ask before closing the tab (Windows)

The tab can no longer throw away unsaved edits.

## 2. Fixed: the default update source flipped (Windows + Android)

The rule now uses system language and time zone, computed once at launch.

## 3. Fixed: updates arrived as archives (Android)

Downloads happen in-app and are verified before being handed to the installer.

## 4. Downloads

- `PDFPrivacyMasker-9.9.9.exe`
"""


def _ver_key(name):
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)$", name)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def find_notes():
    """找 release/ 下最新一版的正文；没有就返回 None（改用内置样本）。"""
    if os.environ.get("PDFMASK_TEST_NOTES") == "inline":
        return None
    if not os.path.isdir(RELEASE_DIR):
        return None
    best = None
    for name in os.listdir(RELEASE_DIR):
        key = _ver_key(name)
        path = os.path.join(RELEASE_DIR, name, "RELEASE-NOTES.md")
        if key and os.path.exists(path) and (best is None or key > best[0]):
            best = (key, path)
    return best[1] if best else None


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
    notes_path = find_notes()
    if notes_path:
        body = open(notes_path, encoding="utf-8").read()
        print("样本：%s" % os.path.relpath(notes_path, ROOT))
    else:
        body = INLINE_NOTES
        print("样本：内置（release/ 不进仓库，没有真实正文时用这段）")

    # 走一遍真实入口：解析 GitHub 的 releases JSON
    got = U.parse_releases(json.loads(json.dumps(fake_release(body))), ".exe", U.GITHUB_PAGE)
    check("能从资产名认出最新版", got and U.ver_text(got["ver"]) == "1.4.4.0")
    # 四段版本号（主.次.修订.补丁）的解析与排序
    four = U.asset_ver("PDFPrivacyMasker-1.4.7.0.exe")
    check("四段版本号能认出来", four == (1, 4, 7, 0), str(four))
    check("四段比三段新", bool(four) and four > (U.ver_tuple("1.4.6") or ()))
    check("1.4.6 与 1.4.6.0 是同一版",
          U.ver_tuple("1.4.6") == U.ver_tuple("1.4.6.0"))
    check("补丁段能拉开新旧（1.4.7.1 > 1.4.7.0）",
          (U.ver_tuple("1.4.7.1") or ()) > (U.ver_tuple("1.4.7.0") or ()))
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
    # 这条不能依赖某一版正文里正好有打码示例，自己造一段才稳定
    sample = U.parse_digest(
        "# v9.9.9\n\n> **一句话**：这是一段足够长的摘要文字，用来验证解析。\n\n"
        "## 修复（Windows）\n\n- 座机号显示成 `0512****1234`，姓名显示成 `赵**`。\n")
    s_join = "\n".join("\n".join(it.get("b") or []) for it in sample["notes"]["zh"])
    check("打码示例的星号没被吃掉（0512****1234 / 赵**）",
          "0512****1234" in s_join and "赵**" in s_join, s_join[:80])
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
