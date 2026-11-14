# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 项目创作时为初中生
#
# This file is part of PDF 隐私打码工具 (PDF Privacy Masker) and is distributed
# under the GNU Affero General Public License v3.0 or later. See LICENSE.

"""检查更新：双通道（Gitee / GitHub）。

安全约定（v1.4.3 起）
----------------------
1. **不再放宽证书校验。** 早期版本在直连失败时会用 ``ssl.CERT_NONE`` 再试一次，
   那等于放弃证书验证：一旦链路上有人做中间人，返回的 JSON 就能把「下载地址」
   换成任意站点。现在只有严格校验一条路，失败就如实报错。
2. **下载地址必须落在白名单域名内。** 即使 API 返回被污染（镜像站、DNS 污染、
   上游被接管），也不会把用户送到陌生域名去下载安装包。
3. 全程只读公开的版本号，不上传任何本地内容。

通道选择
--------
用户在设置里可以自己指定更新源（Gitee / GitHub），也可以留在「跟随系统」：
简体中文的界面 + 简体中文的系统 → 先 Gitee（国内直连稳定）；
其他语言 → 先 GitHub。指定的（或自动选中的）通道连不上时，会自动换另一个
再试一次，两个都拿不到才报错——不会因为选错源就彻底查不了更新。

系统语言问不出来时（ctypes 被拦、locale 异常等）一律按中文用户处理，
默认走 Gitee：宁可让海外用户多等一下，也不让国内用户卡在连不上的 GitHub 上。
"""

import json
import os
import re
import ssl
import urllib.parse
import urllib.request

GITHUB_REPO = "neurotracee/pdf-privacy-masker"
GITEE_REPO = "bio234/pdf-privacy-masker"

GITHUB_API = "https://api.github.com/repos/%s/releases?per_page=20" % GITHUB_REPO
GITEE_API = "https://gitee.com/api/v5/repos/%s/releases?per_page=20" % GITEE_REPO
GITHUB_PAGE = "https://github.com/%s/releases/latest" % GITHUB_REPO
GITEE_PAGE = "https://gitee.com/%s/releases/latest" % GITEE_REPO

UPDATE_TIMEOUT = 10      # 秒；单通道超时就换下一个通道，界面不会卡住。
                         # 原来是 8 秒，移动网络/首次解析常常刚过线就被判死，
                         # 于是「默认 Gitee」悄悄变成了 GitHub。

# 允许的下载域名：GitHub 的发布资产走 objects./release-assets. 两个 CDN，
# Gitee 的附件走 gitee.com 自身。其余域名一律不接受。
ALLOWED_HOSTS = (
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "codeload.github.com",
    "gitee.com",
)


def allowed_download(url):
    """下载地址是否可信：协议必须是 https，域名必须在白名单里（含其子域）。"""
    try:
        u = urllib.parse.urlparse(url or "")
        host = (u.hostname or "").lower()
    except Exception:
        return False
    if u.scheme not in ("https", ""):
        return False
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


# ---------------------------------------------------------------- 版本号工具

# 版本号统一四段：主.次.修订.补丁（例：1.4.7.0）。老的三段版本号（1.4.6）
# 在这里补 0 变成 (1,4,6,0)，与 1.4.6.0 视为同一版，历史 Release 照旧能比。
VER_SEG = 4


def ver_tuple(text):
    """把 v1.4.7.0 / 1.4.7 / 1.4.7.0-beta 之类统一成 (1,4,7,0)，取不出数字返回 None。"""
    nums = re.findall(r"\d+", text or "")
    if not nums:
        return None
    t = [int(x) for x in nums[:VER_SEG]]
    while len(t) < VER_SEG:
        t.append(0)
    return tuple(t)


def ver_text(t):
    """(1,4,7,0) → "1.4.7.0"。界面和弹窗显示版本号都走这里，避免手写格式。"""
    return ".".join(str(x) for x in t)


def asset_ver(name):
    """从文件名里抠版本：PDFPrivacyMasker-1.4.7.0.exe → (1,4,7,0)。"""
    m = re.search(r"(\d+\.\d+(?:\.\d+){0,2})", name or "")
    return ver_tuple(m.group(1)) if m else None


STRONG_RE = re.compile(
    r"^[ \t]*(?:更新级别\s*[：:]\s*强烈建议|<!--\s*update\s*:\s*force\s*-->)",
    re.I | re.M)


def update_strong(body):
    """发布正文里的更新级别：True 表示「强烈建议」更新。

    只有两档，都只是建议，用户永远能关掉：
      1. 正文里有一行「更新级别：强烈建议」（普通建议写「更新级别：建议」或不写）
      2. 早期版本用过的隐藏注释 <!-- update:force -->，现在降级成「强烈建议」
    正文里单独出现「强烈建议」几个字不算，避免说明文字被误判。
    """
    return bool(STRONG_RE.search(body or ""))


# ------------------------------------------------------- 发布正文 → 弹窗文案
#
# 发布页正文是我们自己写的 Markdown，格式约定（v1.4.4 起）：
#
#   更新级别：建议
#   > **一句话**：不超过 100 字，只说最关键的那几条
#   ## 1. 修复：xxx（Windows）
#   ## 2. 修复：xxx（安卓）
#
# 弹窗里先给那句摘要，再把各条目按 Windows / 安卓 归类列出来，
# 末尾写「具体详见 Release 页面」。解析只做保守的兜底：
# 找不到摘要标记就取正文第一段，找不到小标题就不给详细——
# 宁可少显示，也不要显示一堆 Markdown 记号。

_MD_HEAD = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_FENCE_LINE = re.compile(r"^\s*(`{3,}|~{3,})")
_BRIEF_MARK = re.compile(
    r"(?:一句话(?:结论|概括)?|一行概括|摘要|要点|"
    r"in\s+one\s+line|at\s+a\s+glance|tl;?dr|summary|highlight)",
    re.I)
_PLAT_TAIL = re.compile(r"[（(]\s*([^）)]{0,24}?)\s*[）)]\s*$")
_NAV_RE = re.compile(r"^\**[^\n]{0,12}\**\s*\|\s*\[", re.I)
# 「更新级别：建议」这类配置行不是摘要，别把它顶到弹窗顶上
_CONFIG_RE = re.compile(r"^(?:更新级别|更新说明|版本(?:说明)?|update\s*level|version)\s*[：:]", re.I)
# 只跳过「标题就是下载/校验/目录」这类章节。以前是「标题里出现 download 就跳过」，
# 结果「Fixed: Android downloads arrived as .apk.zip」这种正经修复条目被整条丢掉。
_SKIP_TITLE = re.compile(
    r"^(?:下载|校验|目录|附件|(?:downloads?|checksums?|contents)\b)", re.I)

MAX_BRIEF_ZH = 100        # 用户要求：一行摘要控制在 100 字以内
MAX_BRIEF_EN = 150        # 英文同样长度会更长，给 150 字符，读起来才不至于半句
MAX_ITEMS = 8             # 弹窗只列最关键的前几条，其余去发布页看
MAX_ITEM_CHARS = 360      # 单条正文上限，避免弹窗里一大坨字


def _plain(text):
    """去掉 Markdown 记号，只留能直接显示的文字。

    反引号里的内容原样保留（`` `0512****1234` `` 这种打码示例不能被吃掉星号），
    加粗只按成对的 ``**…**`` 剥，孤零零的 ``****`` 不当记号处理。
    """
    s = text or ""
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    s = re.sub(r"`([^`]*)`", keep, s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)          # 图片
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)      # 链接留文字
    s = re.sub(r"^\s*(?:>\s*)+", "", s)                 # 引用
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)              # 成对加粗
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"^\s*[-*+]\s+", "", s)                  # 列表符号
    s = re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)
    return s.strip()


def _clip(text, limit):
    """截到 limit 以内，尽量在句号处断开，实在不行截断加省略号。"""
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    head = s[:limit]
    cut = max(head.rfind(c) for c in "。！？；.!?;")
    if cut >= limit * 0.5:
        return head[:cut + 1]
    return head[:limit - 1].rstrip("，,、 ") + "…"


def split_lang(body):
    """把中英双语正文切成 (中文段, 英文段)。

    英文段的起点是第一个「完全不含汉字、且带 Release Notes / Release」的一级标题。
    没有这种标题时整篇按中文处理（英文段为空），弹窗就只用中文那份。
    """
    lines = (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    for i, ln in enumerate(lines):
        if not _MD_HEAD.match(ln) or not ln.startswith("# "):
            continue
        if re.search(r"[\u4e00-\u9fff]", ln):
            continue
        if re.search(r"release\s*notes?|what'?s\s*new", ln, re.I):
            return "\n".join(lines[:i]), "\n".join(lines[i:])
    return "\n".join(lines), ""


def _brief(section, limit):
    """那一行摘要。

    先找带标记的行（一句话 / TL;DR / Summary …），标记后面的文字就是摘要；
    没有标记时退回正文第一段话——作者偷懒也不会让弹窗空着。
    """
    lines = section.split("\n")
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            if s.startswith("## "):
                break          # 已经进到条目正文，摘要区结束了
            continue           # 一级标题（# v1.4.4 版本说明）跳过
        if _NAV_RE.match(s) or _CONFIG_RE.match(_plain(s)):
            continue
        m = _BRIEF_MARK.search(s[:24])
        if m:
            # 标记后面常跟着「**：」，这些记号先剥掉，剩下的才是摘要正文
            cand = re.sub(r"^[\s*_]*[：:\-—.。]*[\s*_]*", "", s[m.end():])
            cand = _plain(cand)
            cand = re.sub(r"^[\s:：\-—.。*]+", "", cand)
            if len(cand) >= 8:
                return _clip(cand, limit)
    # 兜底：第一段正文（跳过标题、列表、导航、分隔线、代码块）
    para = []
    in_code = False
    for ln in lines:
        s = ln.strip()
        if _MD_FENCE_LINE.match(s):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s or s.startswith("#") or s.startswith("---") or s.startswith("|"):
            if para:
                break
            continue
        if s[0] in "-*>" or _NAV_RE.match(s) or _CONFIG_RE.match(_plain(s)):
            if para:
                break
            continue
        para.append(_plain(s))
        if s.endswith(("。", ".", "！", "!", "？", "?")) and sum(len(x) for x in para) > 30:
            break
    cand = " ".join(x for x in para if x)
    return _clip(cand, limit) if len(cand) >= 10 else ""


def _platform(title):
    """标题尾巴上的平台标注：``both`` / ``win`` / ``android`` / ``""``（未标注）。"""
    m = _PLAT_TAIL.search(title)
    if not m:
        return ""
    tag = m.group(1).lower()
    has_win = "windows" in tag or "桌面" in tag
    has_and = ("安卓" in tag or "android" in tag or "手机" in tag)
    if has_win and has_and:
        return "both"
    if has_win:
        return "win"
    if has_and:
        return "android"
    return ""


def _items(section, limit_items=MAX_ITEMS):
    """把 ``## …`` 小标题拆成弹窗条目：[{t: 标题, p: 平台, b: [正文行]}]。"""
    items = []
    cur = None
    buf = []
    in_code = False

    def flush():
        if not cur:
            return
        body, used = [], 0
        for ln in buf:
            if not ln:
                continue
            left = MAX_ITEM_CHARS - used
            if left <= 20:
                break
            # 单段特别长（英文常见）时截断这一段，而不是把整条丢掉
            body.append(ln if len(ln) <= left else _clip(ln, left))
            used += min(len(ln), left)
        if body:
            cur["b"] = body
            items.append(cur)

    for raw in section.split("\n"):
        s = raw.rstrip()
        if _MD_FENCE_LINE.match(s):
            in_code = not in_code
            continue
        m = _MD_HEAD.match(s)
        if m and len(m.group(1)) <= 3 and not in_code:
            if len(m.group(1)) == 1:
                continue
            flush()
            title = _plain(m.group(2))
            plat = _platform(title)
            if plat:
                title = _PLAT_TAIL.sub("", title).strip()
            title = re.sub(r"^\d+\s*[.、)]\s*", "", title).strip()
            if not title or _SKIP_TITLE.match(title):
                cur = None
                buf = []
                continue
            cur = {"t": title, "p": plat or "both"}
            buf = []
            continue
        if cur is None:
            continue
        if not s or s.startswith("---") or s.startswith("|"):
            continue
        if _NAV_RE.match(s.strip()) or _BRIEF_MARK.search(_plain(s)[:24]) and "：" in s[:28]:
            continue
        line = _plain(s)
        if line:
            buf.append(line)
        if len(items) >= limit_items and not buf:
            break
    flush()
    return items[:limit_items]


def parse_digest(body, items=True):
    """发布正文 → 弹窗用的 ``{"brief": {zh,en}, "notes": {zh,en}}``。"""
    zh, en = split_lang(body)
    out = {"brief": {"zh": _brief(zh, MAX_BRIEF_ZH),
                     "en": _brief(en, MAX_BRIEF_EN) if en else ""},
           "notes": {"zh": [], "en": []}}
    if items:
        out["notes"]["zh"] = _items(zh)
        out["notes"]["en"] = _items(en) if en else []
    return out


# ---------------------------------------------------------------- 通道定义

def _channels(prefer_gitee):
    gitee = {"name": "gitee", "label": "Gitee", "api": GITEE_API, "page": GITEE_PAGE}
    github = {"name": "github", "label": "GitHub", "api": GITHUB_API, "page": GITHUB_PAGE}
    return [gitee, github] if prefer_gitee else [github, gitee]


def system_lang_state():
    """系统界面语言：``"zh"`` / ``"other"`` / ``None``（问不出来）。

    做成三态是因为「判断失败」和「明确是外语系统」要区别对待：
    前者按中文用户兜底（默认 Gitee），后者才让 GitHub 优先。
    """
    if os.name == "nt":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # 0x0804 = zh-CN，0x0404 / 0x0C04 / 0x1404 = zh-TW / zh-HK / zh-MO
            return "zh" if (langid & 0x3FF) == 0x04 else "other"
        except Exception:
            return None
    for key in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(key) or ""
        if v:
            return "zh" if v.lower().replace("-", "_").startswith("zh") else "other"
    try:
        import locale
        code = (locale.getdefaultlocale() or ("", ""))[0] or ""
        if not code:
            return None
        return "zh" if code.lower().startswith("zh") else "other"
    except Exception:
        return None


def system_is_chinese():
    """系统语言是不是中文。判断不出来按「是」处理（同一套兜底逻辑）。"""
    return system_lang_state() != "other"


def utc_offset_hours():
    """本机当前时区相对 UTC 的小时数；问不出来返回 None。"""
    try:
        import datetime
        off = datetime.datetime.now().astimezone().utcoffset()
        if off is None:
            return None
        return off.total_seconds() / 3600.0
    except Exception:
        return None


def prefer_gitee(ui_lang=None):
    """默认源是不是 Gitee。

    只看系统环境，**不看界面语言**：用户可能只是把界面切成英文，那不代表他在海外，
    不该因此把他引到可能连不上的 GitHub。

    判断顺序（任何一步问不出来都按 Gitee 兜底）：
      1. 系统语言是中文 → Gitee；
      2. 语言不是中文，但时区在东八区（中国大陆、中国港澳台、新加坡等）→ 仍按 Gitee；
      3. 两项都指向海外 → GitHub。

    ``ui_lang`` 只为兼容旧调用保留，不再参与判断。
    """
    state = system_lang_state()
    if state is None:
        return True
    if state == "zh":
        return True
    off = utc_offset_hours()
    if off is None:
        return True
    return abs(off - 8.0) < 0.01


def resolve_source(pref=None, ui_lang=None):
    """把设置里的 updateSource 解析成具体通道：``"gitee"`` 或 ``"github"``。

    ``pref`` 为 "auto" / 空 / 非法值时按环境自动选。
    """
    p = (pref or "auto").strip().lower()
    if p in ("gitee", "github"):
        return p
    return "gitee" if prefer_gitee(ui_lang) else "github"


# ---------------------------------------------------------------- 网络

def _fetch(api, user_agent, bypass_proxy=False):
    """严格证书校验的一次 GET。

    ``bypass_proxy`` 只影响「走不走系统代理」，不放松任何证书校验：
    有些机器的系统代理是残留的坏配置（指向一个已经不存在的端口），
    这时直连反而通——所以每个通道失败后都会再直连试一次。
    """
    ctx = ssl.create_default_context()
    req = urllib.request.Request(api, headers={
        "User-Agent": user_agent,
        "Accept": "application/vnd.github+json",
    })
    if bypass_proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ctx),
        )
        with opener.open(req, timeout=UPDATE_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    with urllib.request.urlopen(req, timeout=UPDATE_TIMEOUT, context=ctx) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def parse_releases(data, suffix, page_fallback):
    """从 releases 里挑出本平台能用的最新版本。

    优先用资产文件名里的版本（每个平台各自一个文件，最准）；
    资产名里没有版本号时退回 tag_name（例如 v1.4.0）。
    资产下载地址不在白名单里 → 退回发布页，绝不把用户送到陌生域名。
    """
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    best = None      # (ver, url, asset, strong, body)
    tag_only = None  # (ver, page, tag, strong, body)
    for rel in data:
        if not isinstance(rel, dict) or rel.get("draft"):
            continue
        page = rel.get("html_url") or page_fallback
        if not allowed_download(page):
            page = page_fallback
        tag = (rel.get("tag_name") or "").strip()
        body = rel.get("body") or ""
        strong = update_strong(body)
        tv = ver_tuple(tag)
        if tv and (tag_only is None or tv > tag_only[0]):
            tag_only = (tv, page, tag, strong, body)
        for a in rel.get("assets") or []:
            name = a.get("name") or ""
            if not name.lower().endswith(suffix):
                continue
            v = asset_ver(name)
            if not v:
                continue
            url = a.get("browser_download_url") or ""
            if not allowed_download(url):
                url = page          # 白名单外 → 只给发布页
            if best is None or v > best[0]:
                best = (v, url, name, strong, body)
    if best:
        return {"ver": best[0], "url": best[1], "asset": best[2], "source": "asset",
                "strong": best[3], "body": best[4]}
    if tag_only:
        return {"ver": tag_only[0], "url": tag_only[1], "asset": "", "source": "tag",
                "strong": tag_only[3], "body": tag_only[4]}
    return None


# ---------------------------------------------------------------- 对外入口

def check_update(current, suffix, t, ui_lang=None, source=None, order=None):
    """返回给界面的字典。任何失败都转成 ok=False + 兜底链接，绝不让界面卡住。

    current : 当前版本号（1.4.3）
    suffix  : 本平台安装包后缀（.exe / .apk）
    t       : 中英双语翻译函数 t(zh, en)
    source  : 设置里的更新源："auto" / "gitee" / "github"
    """
    cur = ver_tuple(current) or (0,) * VER_SEG
    src = resolve_source(source, ui_lang)
    # 指定源优先；它连不上时仍然回退到另一个通道，保证「有网就能查到更新」
    chans = order or _channels(src == "gitee")
    wanted_label = chans[0]["label"] if chans else ""
    errors = []
    seen_no_asset = None
    for ch in chans:
        label = ch["label"]
        ua = "PDFPrivacyMasker/" + current
        try:
            data = _fetch(ch["api"], ua)
        except Exception as e:
            # 系统代理坏了（残留配置指向死端口）时直连往往能通，再试一次
            try:
                data = _fetch(ch["api"], ua, bypass_proxy=True)
            except Exception as e2:
                errors.append("%s: %s: %s" % (label, e.__class__.__name__, str(e2)[:100]))
                continue
        got = parse_releases(data, suffix, ch["page"])
        if not got:
            errors.append("%s: %s" % (label, t(
                "仓库里还没有适用于本平台的安装包", "no build for this platform")))
            seen_no_asset = ch
            continue
        latest = ver_text(got["ver"])
        return {
            "ok": True,
            "current": current,
            "latest": latest,
            "hasUpdate": got["ver"] > cur,
            "strong": bool(got.get("strong")),
            "url": got["url"],
            "asset": got["asset"],
            "source": got["source"],
            "channel": label,
            # 首选通道连不上、自动换了一个时据实说明，免得用户以为「默认 Gitee 怎么用了 GitHub」
            "fallbackFrom": "" if label == wanted_label else wanted_label,
            "preferred": src,
            # 弹窗要显示的两段东西：一行摘要 + 按平台归类的详细条目
            "digest": parse_digest(got.get("body") or ""),
            "releasesUrl": ch["page"],
        }
    if seen_no_asset is not None:
        return {
            "ok": False,
            "current": current,
            "error": t("仓库里还没有适用于本平台的安装包，可以去发布页手动看看。",
                       "No build for this platform in the releases yet — "
                       "have a look at the releases page."),
            "detail": " | ".join(errors),
            "url": seen_no_asset["page"],
            "releasesUrl": seen_no_asset["page"],
        }
    return {
        "ok": False,
        "current": current,
        "error": t("连不上 Gitee 和 GitHub，可能是网络、代理或安全软件拦住了。",
                   "Cannot reach Gitee or GitHub — network, proxy or security "
                   "software may be blocking it."),
        "detail": " | ".join(errors),
        "url": GITHUB_PAGE,
        "releasesUrl": GITHUB_PAGE,
    }
