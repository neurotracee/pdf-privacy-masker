#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 GitHub 的每一个 Release（标题 / 正文 / 安装包）原样搬到 Gitee。

用法：
    python dev/sync_gitee_releases.py --dry-run      # 只看计划，不写入
    python dev/sync_gitee_releases.py                # 真正创建 + 上传（幂等）
    python dev/sync_gitee_releases.py --tag v1.4.3   # 只处理某一个版本
    python dev/sync_gitee_releases.py --verify-order # 校验 Gitee 的「最新版」是不是真正的最大版本
    python dev/sync_gitee_releases.py --audit        # 列出各版本创建时间、预发布标记、附件与总配额占用
    python dev/sync_gitee_releases.py --prune-old-assets --dry-run  # 预览一次性批量清理旧版附件
    python dev/sync_gitee_releases.py --reorder      # 重建全部 Release，让新版排在最上面

Gitee 附件配额（1 GB / 整个仓库）与版本顺序规范
------------------------------------------------
见 docs/05-构建与发布.md 的 5.4 节。要点：Gitee **同时保留最新版与上一版**
两个版本的安装包（Windows exe + 安卓 apk + Linux AppImage + SHA256SUMS）；
再往前的版本附件统一清理、**正文（更新说明）一个字都不能少**，用户仍能在
Gitee 看到每一版改了什么，安装包则去 GitHub 发布页下载。

**配额没满就照传**：exe 与 apk 不再因为体积被跳过，上传前会先算一遍
已占用多少，只有真的装不下（已用 + 本包 > 1 GB）才跳过并说明原因；
想无视预检硬传用 `--force-quota`。

**AppImage 不归这个脚本管**：用户的习惯是 GitHub 上手动下载、再手动传到
Gitee，脚本默认跳过它（`--with-appimage` 才代劳），校验时也只提示「等你搬」，
不算失败。

旧版本附件不逐个删、不逐个改文字，留到 `--prune-old-assets` 一次性批量处理；
禁止「从旧版开始删附件 → 加新附件 → 回头改旧版文字」的交错操作，因为 Gitee 的
latest 是「最后创建的非预发布 Release」，不是版本号最大的那个。
正常同步结束会自动跑一次 `--verify-order` 的同等校验，并且**自动清理第 3 个及
更早版本的安装包**（正文保留、只补一段「去 GitHub 下载」说明）。这样「Gitee 只
留最新两版附件」是发版动作自带的，不靠人记得手动跑清理；需要保留更多版本时用
`--keep-recent N`，想跳过这一步用 `--no-prune`。

为什么要 `--reorder`
--------------------
Gitee 的 Release 列表是**按创建时间倒序**排的，没有「按版本号排序」这回事。
如果把历史版本补传到 Gitee，补得最晚的那个（往往是最旧的版本）就会顶在列表
第一位，看起来像「最新版」，用户点进去下载到的是老版本。
`--reorder` 会按版本号**升序**重放：先删掉现有 Release，再依次创建
v1.3.0 → v1.4.0 → v1.4.1 → …，最后一次创建的最新版自然落在最上面。

凭据：
    Gitee 私人令牌，写在 ~/.gitee_token 或环境变量 GITEE_TOKEN（权限需含 projects）。
    GitHub 侧读列表用公开 API，下载大附件时优先用 ~/.github_token 走官方 asset 地址。

幂等：同名 Release 已存在就不重复创建；同名附件已存在就跳过上传。
"""
import argparse
import io
import json
import os
import re
import subprocess
import time
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

GH_OWNER, GH_REPO = "neurotracee", "pdf-privacy-masker"
GE_OWNER, GE_REPO = "bio234", "pdf-privacy-masker"
GE_API = "https://gitee.com/api/v5/repos/%s/%s" % (GE_OWNER, GE_REPO)
GH_API = "https://api.github.com/repos/%s/%s" % (GH_OWNER, GH_REPO)
TAG = "main"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
PKG = ROOT
CACHE = os.path.join(HOME, "AppData", "Local", "Temp", "gitee-assets")

# 本地找不到的旧版安装包，用镜像兜底：tag -> [原名]
REMOTE_FALLBACK = {
    "v1.3.0": ["PDF.exe"],
}


def token():
    p = os.path.join(HOME, ".gitee_token")
    if os.path.exists(p):
        t = io.open(p, encoding="utf-8").read().strip()
        if t:
            return t
    return (os.environ.get("GITEE_TOKEN") or "").strip()


def http_json(url, method="GET", data=None, tok=None, retries=4):
    """调 Gitee / GitHub 的 JSON 接口。

    统一走系统 curl：Python 的 urllib 在本机偶尔会被中间层掐断
    （报 "Remote end closed connection without response"），curl 重试即可。
    """
    if data is not None or tok:
        sep = "&" if "?" in url else "?"
        if tok:
            url += sep + urllib.parse.urlencode({"access_token": tok})
            sep = "&"
    cmd = ["curl", "-s", "--noproxy", "*", "--max-time", "60",
           "-X", method, "-H", "Content-Type: application/json; charset=utf-8",
           "-H", "Accept: application/json", "-H", "User-Agent: sync-gitee",
           "-w", "\n%{http_code}", url]
    if "api.github.com" in url:
        # 本机装了抓包/加速软件时 GitHub 走的是它签发的证书，curl 需要 -k；
        # 这条通道只读公开数据，不涉及任何凭据。
        cmd.insert(1, "-k")
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    for i in range(retries):
        args = cmd[:]
        if body is not None:
            args += ["--data-binary", "@-"]
        r = subprocess.run(args, input=body, capture_output=True)
        out = r.stdout.decode("utf-8", "replace") if r.stdout else ""
        code = 0
        if "\n" in out:
            out, _, tail = out.rpartition("\n")
            try:
                code = int(tail.strip())
            except Exception:
                code = 0
        if code:
            try:
                return code, (json.loads(out) if out.strip() else {})
            except Exception:
                return code, {"raw": out[:300]}
        if i + 1 < retries:
            import time as _t
            _t.sleep(1.5 * (i + 1))
    return 0, {"err": "curl 多次失败"}


def ver_key(text):
    """v1.4.10 要排在 v1.4.9 后面，所以按数字元组排，不能按字符串排。"""
    nums = re.findall(r"\d+", text or "")
    # 版本号是四段（1.4.6.5），只取前三段会让同一修订下的几个小版本平起平坐，
    # max() / 排序就会挑错「最新版」。四段全部参与比较。
    t = [int(x) for x in nums[:4]]
    while len(t) < 4:
        t.append(0)
    return tuple(t)


def gh_releases():
    """读 GitHub 的 Release 列表。

    个别网络环境里 Python 的 urllib 过不去（例如本机装了抓包/加速软件、
    系统信任它但 OpenSSL 不信任）。这时退回系统 curl，再不行才报错。
    """
    code, data = http_json(GH_API + "/releases?per_page=30")
    if code == 200 and isinstance(data, list):
        return [r for r in data if not r.get("draft")]
    r = subprocess.run(["curl", "-sk", "--noproxy", "127.0.0.1", "--max-time", "40",
                        GH_API + "/releases?per_page=30"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        data = json.loads(r.stdout)
    except Exception:
        print("读取 GitHub Release 失败：HTTP %s / curl 也拿不到" % code)
        return []
    return [x for x in data if not x.get("draft")]


def local_asset(tag, name):
    """按文件名在本地 release/<tag>/ 里找对应安装包。"""
    d = os.path.join(PKG, "release", tag)
    if not os.path.isdir(d):
        return None
    p = os.path.join(d, name)
    if os.path.exists(p):
        return p
    for f in os.listdir(d):
        if f.lower() == name.lower():
            return os.path.join(d, f)
    return None


def gh_token():
    p = os.path.join(HOME, ".github_token")
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read().strip()
    return (os.environ.get("GITHUB_TOKEN") or "").strip()


def size_ok(path, expect):
    """GitHub API 报了字节数时，必须一字节不差；没报才退回「大于 1 MB」的粗判。"""
    if not os.path.isfile(path):
        return False
    if expect:
        return os.path.getsize(path) == expect
    return os.path.getsize(path) > 1024 * 1024


def download_parallel(url, out, expect_size, parts=8):
    """大文件单连接只有 10~50 KB/s，用 Range 分块并发拉，再按序拼回。

    服务端必须返回 206 且每块字节数完全对得上，否则整批丢弃走普通下载。
    """
    chunk = expect_size // parts
    spans = [(i * chunk, (i + 1) * chunk - 1) for i in range(parts - 1)]
    spans.append(((parts - 1) * chunk, expect_size - 1))

    def fetch(idx, start, end):
        part = "%s.part%d" % (out, idx)
        cmd = ["curl", "-sk", "--noproxy", "*", "--max-time", "900",
               "-r", "%d-%d" % (start, end), "-o", part,
               "-w", "%{http_code}", url]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            ok = ("206" in (r.stdout or "") and os.path.isfile(part)
                  and os.path.getsize(part) == end - start + 1)
        except Exception:
            ok = False
        return idx, ok

    results = {}
    with ThreadPoolExecutor(max_workers=parts) as pool:
        futures = [pool.submit(fetch, i, s, e) for i, (s, e) in enumerate(spans)]
        for fut in as_completed(futures):
            idx, ok = fut.result()
            results[idx] = ok
    if not all(results.get(i) for i in range(parts)):
        for i in range(parts):
            p = "%s.part%d" % (out, i)
            if os.path.exists(p):
                os.remove(p)
        return False
    try:
        with open(out, "wb") as dst:
            for i in range(parts):
                p = "%s.part%d" % (out, i)
                with open(p, "rb") as src:
                    while True:
                        block = src.read(1024 * 1024)
                        if not block:
                            break
                        dst.write(block)
                os.remove(p)
    except Exception:
        return False
    return size_ok(out, expect_size)


def download(name, tag, out_name, expect_size=0, asset_url=""):
    """下载 GitHub 附件，并按 API 给出的字节数校验。

    2026-11-15 事故：ghproxy 把 47 MB 的 apk 截断成 3.4 MB，而旧代码只判
    「> 1 MB 就算成功」，坏包被当成正式安装包装到 Gitee 的 v1.4.7.0 上，
    点「最新版」会下到装不上的残包。现在优先走 GitHub API 的 asset 地址
    （token + Accept: application/octet-stream），大小必须完全一致才允许上传。
    """
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, out_name)
    if size_ok(out, expect_size):
        print("  已有缓存 %s（%.2f MB）" % (out_name, os.path.getsize(out) / 1048576))
        return out
    # 大于 20 MB 的包单连接在国内只有 10~50 KB/s，先用 Range 并发拉。
    if expect_size > 20 * 1024 * 1024:
        fast = "https://gh-proxy.com/https://github.com/%s/%s/releases/download/%s/%s" % (
            GH_OWNER, GH_REPO, tag, urllib.parse.quote(name))
        print("  并行下载 %s（8 路 Range）..." % name, flush=True)
        if download_parallel(fast, out, expect_size):
            print("  -> 完成，%.2f MB" % (os.path.getsize(out) / 1048576), flush=True)
            return out
        print("  并行下载失败，换普通下载", flush=True)
    tok = gh_token()
    urls = []
    if asset_url and tok:
        urls.append(("GitHub API", [
            "curl", "-sL", "-k", "--noproxy", "*", "--max-time", "600",
            "-H", "Authorization: token " + tok,
            "-H", "Accept: application/octet-stream",
            asset_url, "-o", out, "-w", "%{http_code}"]))
    mirror = "https://ghproxy.net/https://github.com/%s/%s/releases/download/%s/%s" % (
        GH_OWNER, GH_REPO, tag, urllib.parse.quote(name))
    urls.append(("ghproxy 镜像", [
        "curl", "-sL", "--noproxy", "*", "--max-time", "600",
        mirror, "-o", out, "-w", "%{http_code}"]))
    for label, cmd in urls:
        print("  下载 %s（%s）..." % (name, label))
        if os.path.exists(out):
            os.remove(out)
        r = subprocess.run(cmd, capture_output=True, text=True)
        sz = os.path.getsize(out) if os.path.exists(out) else 0
        print("  -> HTTP %s，%.2f MB" % (r.stdout.strip(), sz / 1048576))
        if size_ok(out, expect_size):
            return out
        print("     字节数与 GitHub API 不符（期望 %s），换下一个源" % expect_size)
    if os.path.exists(out):
        os.remove(out)
    return None


def upload_asset(release_id, path, tok, tries=3):
    """Gitee 上传附件：multipart/form-data，用 curl 更稳。

    Gitee 的附件接口会抖：同一条命令第一次返回空、过几秒重来就成功
    （2026-11-14 发布 1.4.6.1 / 1.4.6.2 时都遇到过，大文件尤其明显）。
    所以这里自己重试，别让人守着终端一条条手动重跑。
    """
    last = "未知原因"
    for i in range(tries):
        if i:
            time.sleep(3)
        cmd = ["curl", "-s", "--noproxy", "*", "--max-time", "900", "-X", "POST",
               "-F", "access_token=" + tok,
               "-F", "file=@" + path,
               "%s/releases/%s/attach_files" % (GE_API, release_id)]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        out = (r.stdout or "").strip()
        try:
            d = json.loads(out)
        except Exception:
            last = out[:200] or (r.stderr or "").strip()[:200] or "空响应（接口抖动）"
            continue
        if isinstance(d, dict) and d.get("browser_download_url"):
            return True, d.get("name")
        last = str(d)[:200]
        # 业务层面的拒绝（重名、没权限）重试也没用，直接返回
        if "exist" in last.lower() or "已存在" in last or "permission" in last.lower():
            break
    return False, "%s（已重试 %d 次）" % (last, tries)


def gitee_releases():
    code, ge = http_json(GE_API + "/releases?page=1&per_page=50")
    return ge if isinstance(ge, list) else []


def create_release(rel, tok, dry):
    tag = rel["tag_name"]
    name = rel.get("name") or tag
    body = (rel.get("body") or "").replace("\r\n", "\n")
    pre = bool(rel.get("prerelease"))
    if dry:
        print("  [dry-run] 创建 %s 并上传附件" % tag)
        return None
    c, resp = http_json(GE_API + "/releases", "POST",
                        {"tag_name": tag, "name": name, "body": body,
                         "target_commitish": TAG, "prerelease": pre}, tok)
    print("  POST -> HTTP %s" % c)
    if c not in (200, 201):
        print("  失败：%s" % str(resp)[:300])
        return None
    return resp


def upload_all(rel, rid, tok, dry, force_quota=False):
    tag = rel["tag_name"]
    used = 0
    quota_known = False
    if tok:
        try:
            used = gitee_used_bytes(tok)
            quota_known = True
        except Exception:
            pass
    for asset in (rel.get("assets") or []):
        an = asset["name"]
        expect = int(asset.get("size") or 0)
        path = None
        if an not in (REMOTE_FALLBACK.get(tag) or []):
            path = local_asset(tag, an)
            if path and expect and os.path.getsize(path) != expect:
                print("  本地 %s 大小不符（%s != %s），改用远端" %
                      (an, os.path.getsize(path), expect))
                path = None
        if not path:
            path = download(an, tag, an, expect, asset.get("url") or "")
        if not path:
            print("  附件 %s 拿不到或大小校验失败，跳过" % an)
            continue
        if expect and os.path.getsize(path) != expect:
            print("  附件 %s 大小校验失败，拒绝上传" % an)
            continue
        size = os.path.getsize(path)
        if quota_known and not force_quota and used + size > GITEE_QUOTA:
            print("  跳过 %s：配额不够（已用 %.1f MB + 本包 %.1f MB > %d MB）"
                  % (an, used / 1048576, size / 1048576, GITEE_QUOTA // 1048576))
            continue
        if dry:
            print("  [dry-run] 将上传 %s（%.2f MB）" % (an, size / 1048576))
            if quota_known:
                used += size
            continue
        print("  上传 %s（%.2f MB）..." % (an, size / 1048576))
        ok, info = upload_asset(rid, path, tok)
        print("  -> %s %s" % ("成功" if ok else "失败", info))
        if ok and quota_known:
            used += size


def reorder(rels, tok, dry):
    """按版本号升序重建全部 Release，让最新版回到列表最上面。"""
    order = sorted(rels, key=lambda r: ver_key(r["tag_name"]))
    cur = {r.get("tag_name"): r for r in gitee_releases()}
    print("将要重放的顺序（旧 → 新）：%s\n" % " → ".join(r["tag_name"] for r in order))

    for tag, item in cur.items():
        if tag not in [r["tag_name"] for r in order]:
            continue
        if dry:
            print("  [dry-run] 删除现有 %s（id=%s）" % (tag, item.get("id")))
            continue
        c, resp = http_json(GE_API + "/releases/%s" % item.get("id"), "DELETE", tok=tok)
        print("  DELETE %s -> HTTP %s" % (tag, c))
        if c not in (200, 204):
            print("    失败：%s" % str(resp)[:200])

    for rel in order:
        print("=== 重建 %s ===" % rel["tag_name"])
        resp = create_release(rel, tok, dry)
        if dry or not resp:
            continue
        upload_all(rel, resp.get("id"), tok, dry)

    if not dry:
        print("\n重建后的顺序（Gitee 显示顺序，新 → 旧）：")
        for r in gitee_releases():
            print("  %-8s 创建于 %s" % (r.get("tag_name"), r.get("created_at")))


# ---------------------------------------------------------------- 配额 / 顺序

GH_RELEASES_URL = "https://github.com/neurotracee/pdf-privacy-masker/releases"
GE_LATEST_URL = "https://gitee.com/bio234/pdf-privacy-masker/releases/latest"
GITEE_QUOTA = 1024 ** 3          # 整个仓库所有历史版本附件累计，1 GB
KEEP_RECENT = 2                  # Gitee 保留最近两个版本（最新版 + 上一版），各端都留

# 我们**主动上传**的安装包后缀（Gitee 自带的源码 zip / tar.gz 不算，别删）。
# 三端一起同步：Windows exe、安卓 apk、Linux AppImage。
# 只要配额没满就都传——不按「哪个平台小就砍哪个」做减法，那是用户该决定的事。
ASSET_SUFFIXES = (".exe", ".apk", ".appimage")

# AppImage 由本人手动搬运（GitHub 下载 → Gitee 上传），脚本默认不碰它。
# 这是用户在 2026-11-24 明确要求的：自动取回再传一次多花十分钟，
# 手动反而更快、更可控。确实想让脚本代劳时加 --with-appimage。
MANUAL_SUFFIXES = (".appimage",)

HISTORY_NOTE_TEMPLATE = """> **本页是历史版本，安装包已从 Gitee 移除（下面这一版的更新说明完整保留）。** Gitee 仓库的 Release 附件总额度只有 1 GB，只保留**最新版与上一版**两个版本的全部安装包（Windows exe、安卓 apk、Linux AppImage 都留在本站，额度够就会一起传）；更早版本的附件已统一清理，只能麻烦你到 GitHub 发布页查看和下载。
> 这一版的发布页（三端安装包都在 Assets 区）：
> https://github.com/neurotracee/pdf-privacy-masker/releases/tag/{tag}
> 全部历史版本：https://github.com/neurotracee/pdf-privacy-masker/releases
> 只想装软件用的话，直接下最新版：https://gitee.com/bio234/pdf-privacy-masker/releases/latest

"""


def newest_tag(rels):
    return max((r["tag_name"] for r in rels), key=ver_key)


def recent_tags(rels, n=None):
    """Gitee 要保留的版本：按版本号取最近 n 个（最新版 + 上一版）。

    n 默认取模块级 KEEP_RECENT，不能用 def 默认值直接绑定，否则命令行改
    --keep-recent 时这里还按旧数字算。
    """
    if n is None:
        n = KEEP_RECENT
    return set(sorted((r["tag_name"] for r in rels), key=ver_key, reverse=True)[:n])


def ge_latest_tag():
    """直接问 Gitee 的 /releases/latest 落在哪个 tag，不靠列表猜。

    用 HEAD 读 Location 头，而不是 %{redirect_url}：本机走代理时，第一跳是
    「Connection Established」，%{redirect_url} 会拿到空值，导致明明正确也报
    「取不到」。用户点网页链接看到的就是这个 302 的落点，所以以它为准。
    """
    r = subprocess.run(["curl", "-sI", "--max-time", "30", GE_LATEST_URL],
                       capture_output=True, text=True)
    out = r.stdout or ""
    for line in out.splitlines():
        if line.lower().startswith("location:"):
            m = re.search(r"/tag/([^/?#\s]+)", line.split(":", 1)[1])
            if m:
                return m.group(1)
    return ""


def ge_attach_files(rid, tok):
    c, d = http_json("%s/releases/%s/attach_files" % (GE_API, rid), tok=tok)
    return d if isinstance(d, list) else []


def install_assets(files):
    """我们上传的安装包（exe / apk / AppImage）。

    排除 Gitee 自动附带的源码包（`v1.4.9.1.zip`、`.tar.gz`）——它们不在
    attach_files 里，但判断时统一用后缀，避免误伤。
    """
    return [a for a in files
            if (a.get("name") or "").lower().endswith(ASSET_SUFFIXES)]


def gitee_used_bytes(tok, rels=None, deep=False):
    """整个仓库所有 Release 附件已占用的字节数。

    默认只统计**最近的 KEEP_RECENT+1 个版本**：更早版本的附件本来就会被发版
    流程清空，为了一个预检把 24 个版本全查一遍（单次 3~4 秒，串行 90 秒以上，
    并发还会被 Gitee 限流拖死）不值得。要逐版本核对用 `--full-quota` 走 deep。
    """
    rels = rels if rels is not None else gitee_releases()
    picked = rels if deep else sorted(
        rels, key=lambda r: ver_key(r.get("tag_name") or ""),
        reverse=True)[:KEEP_RECENT + 1]
    total = 0
    for r in picked:
        rid = r.get("id")
        if rid is None:
            continue
        try:
            total += sum(int(a.get("size") or 0) for a in ge_attach_files(rid, tok))
        except Exception as e:
            print("  配额明细取不到（%s）：按 0 计入" % str(e)[:80])
    return total


def verify_order(rels=None, tok=None, quiet=False):
    """校验「Gitee 显示的最新版」==「版本号最大的版本」。

    四条都过才算绿：latest 重定向、Gitee 列表里最后创建的那个、最新版两端
    安装包（exe + apk）都在，且附件字节数与 GitHub API 一致（防止镜像截断的
    残包冒充正式安装包）。上一版的两端包缺失只提示不报错。
    """
    tok = tok or token()
    rels = rels or gh_releases()
    if not rels:
        return False, ["拿不到 GitHub Release 列表"]
    want = newest_tag(rels)
    problems = []

    got = ge_latest_tag()
    if got != want:
        problems.append("/releases/latest 落在 %s，应为 %s" % (got or "(空)", want))

    ges = gitee_releases()
    by_created = sorted(ges, key=lambda x: x.get("created_at") or "", reverse=True)
    top = by_created[0].get("tag_name") if by_created else ""
    if top != want:
        problems.append("Gitee 列表第一条是 %s，应为 %s（它是最后创建的非预发布 Release）" % (top, want))

    cur = next((x for x in ges if x.get("tag_name") == want), None)
    manual_pending = []
    if not cur:
        problems.append("Gitee 上还没有 %s" % want)
    else:
        ghr = next((x for x in rels if x["tag_name"] == want), None)
        expect = {a["name"]: int(a.get("size") or 0) for a in (ghr.get("assets") or [])}
        have = {a["name"]: int(a.get("size") or 0) for a in ge_attach_files(cur["id"], tok)}
        for n, sz in expect.items():
            if not n.lower().endswith(ASSET_SUFFIXES):
                continue
            if n not in have:
                # AppImage 由本人手动搬，没传是「待办」不是「出错」
                if n.lower().endswith(MANUAL_SUFFIXES):
                    manual_pending.append(n)
                else:
                    problems.append("最新版缺少安装包 %s（Gitee 必须各端都留）" % n)
            elif have[n] != sz:
                problems.append("附件 %s 大小不符：Gitee %s / GitHub %s" % (n, have[n], sz))

    keep = recent_tags(rels)
    prev = sorted(keep, key=ver_key, reverse=True)[1:]
    missing_prev = []
    for tag in prev:
        r = next((x for x in ges if x.get("tag_name") == tag), None)
        if not r:
            continue
        have = {a["name"] for a in ge_attach_files(r["id"], tok)}
        for n in ((next((x for x in rels if x["tag_name"] == tag), {}) or {}).get("assets") or []):
            if n["name"].lower().endswith(ASSET_SUFFIXES) and n["name"] not in have:
                missing_prev.append("%s/%s" % (tag, n["name"]))

    # 历代更新说明必须都在：附件可以清、正文不能丢。哪怕旧版只剩一段说明，
    # 用户点进去也要能看到「这一版改了什么、去哪下」。
    empty_body = [r.get("tag_name") for r in ges
                  if len((r.get("body") or "").strip()) < 80]
    if empty_body:
        problems.append("这些版本的更新说明缺失或过短（正文必须保留）：%s"
                        % ", ".join(sorted(empty_body, key=ver_key)))

    # 保留版本之外的旧版还有多少附件：不是错误（留待一次性批量清理），但必须看得见
    old_with_assets = []
    for r in ges:
        if r.get("tag_name") in keep:
            continue
        if install_assets(ge_attach_files(r["id"], tok)):
            old_with_assets.append(r.get("tag_name"))

    if not quiet or problems:
        print("=== 版本顺序校验 ===")
        print("  最大版本：%s" % want)
        print("  Gitee /releases/latest：%s" % (got or "(取不到)"))
        print("  Gitee 列表第一条：%s" % (top or "(取不到)"))
        print("  Gitee 保留版本：%s（各端安装包）" % ", ".join(sorted(keep, key=ver_key, reverse=True)))
        if missing_prev and not quiet:
            print("  上一版缺附件（提示，不算失败）：%s" % ", ".join(missing_prev))
        if manual_pending and not quiet:
            print("  等你手动搬的附件（不算失败）：%s" % ", ".join(manual_pending))
            print("    做法：GitHub 那一版的 Assets 里下载 → Gitee 同一版的「上传附件」里传上去。")
        print("  仍带附件的更早版本：%d 个%s（按策略留待一次性批量清理，不是错误）" % (
            len(old_with_assets),
            "：" + ", ".join(old_with_assets) if old_with_assets and not quiet else ""))
        print("  结果：%s" % ("通过" if not problems else "不通过"))
        for x in problems:
            print("    - " + x)
        if problems:
            print("  修复：把误建的历史 Release 标 pre-release；必要时用 --reorder 按旧→新重建；")
            print("        校验通过前不要在 README / 更新说明里写「Gitee 最新版可下载」。")
    return not problems, problems


def audit(tok):
    """给「后续一次性批量清理」提供依据：谁有附件、谁标了预发布、一共占了多少配额。"""
    rels = gh_releases()
    keep = recent_tags(rels) if rels else set()
    ges = sorted(gitee_releases(), key=lambda x: ver_key(x.get("tag_name") or ""))
    total = 0
    print("=== Gitee Release 附件审计（配额 %d MB）===" % (GITEE_QUOTA // 1048576))
    print("%-11s %-6s %-8s %-22s %s" % ("版本", "Gitee", "预发布", "安装包", "安装包体积"))
    for r in ges:
        tag = r.get("tag_name") or ""
        files = install_assets(ge_attach_files(r["id"], tok))
        sz = sum(int(a.get("size") or 0) for a in files)
        total += sz
        print("%-11s %-6s %-8s %-22s %.2f MB" % (
            tag, "保留" if tag in keep else "清走", "是" if r.get("prerelease") else "",
            ("%d 个" % len(files)) if files else "无", sz / 1048576))
    print("安装包合计：%.2f MB / %d MB（%.1f%%）" %
          (total / 1048576, GITEE_QUOTA // 1048576, total * 100.0 / GITEE_QUOTA))
    print("保留规则：最近 %d 个版本（最新版 + 上一版）两端都留；更早的附件在发版同步结束时会自动清理（正文保留）。" % KEEP_RECENT)


def history_note_body(body, tag):
    """把旧版正文开头的「附件已移除」提示统一成同一段文字，其余一个字不动。"""
    note = HISTORY_NOTE_TEMPLATE.format(tag=tag)
    m = re.search(r"^## ", body, flags=re.M)
    head_end = m.start() if m else 0
    head = body[:head_end]
    if "安装包已移除" in head or "本页是历史版本" in head:
        body = body[head_end:].lstrip("\n")
    # 早期手工改过的旧版还留着一块「本页没有，去 GitHub 下」的表格，统一模板里
    # 已经写了链接，这块就成了重复内容，批量处理时一并去掉。
    m2 = re.search(r"^## 安装包.*?(?=\n更新级别：|\n## |\Z)", body,
                   flags=re.S | re.M)
    if m2:
        body = body[:m2.start()] + body[m2.end():]
    return note + body


def prune_old_assets(tok, dry=False):
    """一次性批量清理旧版附件（独立任务，正常发版流程不调用）。

    按版本号**从旧到新**统一处理，不夹带「给新版本加附件」的动作；新版附件
    由发版流程的最后一步负责。结束后立即校验版本顺序，避免 Gitee 的 latest
    被旧版本顶掉。
    """
    rels = gh_releases()
    if not rels:
        return
    keep = recent_tags(rels)
    ges = {r.get("tag_name"): r for r in gitee_releases()}
    order = sorted((t for t in ges if t not in keep), key=ver_key)
    print("=== %s旧版本附件 ===" % ("[dry-run] 预览" if dry else "批量清理"))
    print("保留 %s 的两端附件（最新版 + 上一版）；更早的按旧 → 新统一处理：" %
          ", ".join(sorted(keep, key=ver_key, reverse=True)))
    for tag in order:
        r = ges[tag]
        files = install_assets(ge_attach_files(r["id"], tok))
        print("  %-11s 待删 %d 个安装包%s" %
              (tag, len(files), "" if files else "（已清空，只统一说明文字）"))
        if dry:
            continue
        for a in files:
            c, resp = http_json("%s/releases/%s/attach_files/%s" % (GE_API, r["id"], a["id"]),
                                "DELETE", None, tok)
            if c not in (200, 204):
                print("    删除 %s 失败：HTTP %s %s" % (a["name"], c, str(resp)[:120]))
        body = history_note_body((r.get("body") or "").replace("\r\n", "\n"), tag)
        c, resp = http_json("%s/releases/%s" % (GE_API, r["id"]), "PATCH",
                            {"tag_name": tag, "name": r.get("name") or tag,
                             "body": body, "prerelease": bool(r.get("prerelease"))}, tok)
        print("    说明文字 -> HTTP %s" % c)
    if dry:
        print("  [dry-run] 未做任何改动。确认无误后去掉 --dry-run 再跑。")
    else:
        print("=== 批量清理后校验版本顺序 ===")
        verify_order(rels, tok)


def main():
    global KEEP_RECENT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--replace-assets", action="store_true",
                    help="已存在的 Release：整个删掉重建并重传附件（重发同一版本号时用）")
    ap.add_argument("--reorder", action="store_true",
                    help="按版本号升序重建全部 Release，修正 Gitee 的倒序排列")
    ap.add_argument("--verify-order", action="store_true",
                    help="只校验 Gitee 的 latest / 列表顺序 / 最新版附件大小，不改任何东西")
    ap.add_argument("--audit", action="store_true",
                    help="列出各版本创建时间、预发布标记、附件与 1GB 配额占用")
    ap.add_argument("--prune-old-assets", action="store_true",
                    help="一次性批量清理旧版附件并统一说明文字（独立任务，配 --dry-run 预览）")
    ap.add_argument("--no-prune", action="store_true",
                    help="正常同步结束后不做自动清理（默认会自动清掉第 3 个及更早版本的安装包）")
    ap.add_argument("--force-quota", action="store_true",
                    help="无视 1GB 配额预检硬上传（默认只在配额够时才传，不够会跳过并说明）")
    ap.add_argument("--full-quota", action="store_true",
                    help="配额预检时把全部历史版本都查一遍（默认只查最近几个，快得多）")
    ap.add_argument("--keep-recent", type=int, default=KEEP_RECENT,
                    help="Gitee 保留几个版本的安装包（默认 2：最新版 + 上一版）")
    ap.add_argument("--with-appimage", action="store_true",
                    help="连 AppImage 也自动传（默认不传：AppImage 由本人从 GitHub 下载后手动上传）")
    a = ap.parse_args()

    if a.keep_recent and a.keep_recent > 0:
        KEEP_RECENT = a.keep_recent

    tok = token()
    if not tok and not a.dry_run and not a.verify_order:
        print("缺少 Gitee 令牌：请写入 %s 或设置 GITEE_TOKEN" % os.path.join(HOME, ".gitee_token"))
        return 1

    rels = gh_releases()
    if not rels:
        return 1
    if a.verify_order:
        ok, _ = verify_order(rels, tok)
        return 0 if ok else 2
    if a.audit:
        audit(tok)
        return 0
    if a.prune_old_assets:
        prune_old_assets(tok, a.dry_run)
        return 0
    print("GitHub 共 %d 个 Release：%s\n" % (len(rels), ", ".join(r["tag_name"] for r in rels)))

    if a.reorder:
        reorder(rels, tok, a.dry_run)
        print("\n完成。")
        return 0

    existing = {r.get("tag_name"): r for r in gitee_releases()}
    print("Gitee 现有 %d 个：%s\n" % (len(existing), ", ".join(existing) or "无"))

    # 配额先摸一遍：只要没到上限就照传，不预先替用户砍平台。
    used = 0
    quota_known = False
    if tok:
        try:
            used = gitee_used_bytes(tok, list(existing.values()), deep=a.full_quota)
            quota_known = True
            print("Gitee 附件已占用 %.2f MB / %d MB（%.1f%%），剩余 %.2f MB\n" % (
                used / 1048576, GITEE_QUOTA // 1048576, used * 100.0 / GITEE_QUOTA,
                (GITEE_QUOTA - used) / 1048576))
        except Exception as e:
            print("读取配额占用失败（仍继续上传，单个包超限时接口会报错）：%s\n" % e)

    for r in sorted(rels, key=lambda x: ver_key(x["tag_name"])):
        tag = r["tag_name"]
        if a.tag and tag != a.tag:
            continue
        name = r.get("name") or tag
        body = (r.get("body") or "").replace("\r\n", "\n")
        pre = bool(r.get("prerelease"))
        print("=== %s · %s ===" % (tag, name))

        cur = existing.get(tag)
        if cur:
            same_name = (cur.get("name") or "") == name
            same_body = (cur.get("body") or "").strip() == body.strip()
            print("  已存在 id=%s，标题%s，正文%s" % (
                cur.get("id"),
                "一致" if same_name else "不同（'%s'）" % (cur.get("name") or "")[:30],
                "一致" if same_body else "不同（%d vs %d 字符）" % (
                    len(cur.get("body") or ""), len(body))))
            if a.replace_assets:
                # Gitee 的 API 不提供删除单个附件的接口（assets 里连 id 都没有），
                # 所以要换附件只能整个 Release 删掉重建——tag 不变，指向同一提交。
                if a.dry_run:
                    print("  [dry-run] 删除整个 Release 后重建，并重传全部附件")
                    rel = dict(cur, assets=[])
                else:
                    c, resp = http_json(GE_API + "/releases/%s" % cur.get("id"),
                                        "DELETE", None, tok)
                    print("  删除旧 Release -> HTTP %s" % c)
                    if c not in (200, 204):
                        print("  删除失败：%s" % str(resp)[:200])
                        continue
                    time.sleep(2)
                    rel = create_release(r, tok, False)
                    if not rel:
                        continue
            else:
                if not (same_name and same_body) and not a.dry_run:
                    # Gitee 的 PATCH 是「整对象更新」，不带 tag_name 会 400
                    c, resp = http_json(GE_API + "/releases/%s" % cur.get("id"), "PATCH",
                                        {"tag_name": tag, "name": name, "body": body,
                                         "target_commitish": TAG, "prerelease": pre}, tok)
                    print("  PATCH -> HTTP %s %s" % (c, "" if c in (200, 201) else str(resp)[:200]))
                elif a.dry_run and not (same_name and same_body):
                    print("  [dry-run] 将更新标题与正文")
                rel = cur
        else:
            print("  不存在，需要创建（正文 %d 字符）" % len(body))
            rel = create_release(r, tok, a.dry_run)
            if a.dry_run:
                for asset in (r.get("assets") or []):
                    if asset["name"].lower().endswith(MANUAL_SUFFIXES) and not a.with_appimage:
                        print("  [dry-run] %s 留给手动上传，不上传" % asset["name"])
                        continue
                    print("  [dry-run] 将上传 %s" % asset["name"])
                continue
            if not rel:
                continue

        if a.skip_upload:
            continue
        rid = rel.get("id")
        have = {x.get("name") for x in (rel.get("assets") or [])}
        have = {h for h in have if h} | {os.path.basename(x.get("browser_download_url") or "")
                                         for x in (rel.get("assets") or [])}
        for asset in (r.get("assets") or []):
            an = asset["name"]
            if an in have or any(h.endswith(an) for h in have):
                print("  附件 %s 已存在，跳过" % an)
                continue
            if an.lower().endswith(MANUAL_SUFFIXES) and not a.with_appimage:
                print("  跳过 %s：AppImage 按约定留给你手动搬（GitHub 下载 → Gitee 上传）" % an)
                continue
            expect = int(asset.get("size") or 0)
            path = None
            if an not in (REMOTE_FALLBACK.get(tag) or []):
                path = local_asset(tag, an)
                if path and expect and os.path.getsize(path) != expect:
                    print("  本地 %s 大小不符（%s != %s），改用远端" %
                          (an, os.path.getsize(path), expect))
                    path = None
            if not path:
                path = download(an, tag, an, expect, asset.get("url") or "")
            if not path:
                print("  附件 %s 拿不到或大小校验失败，跳过" % an)
                continue
            if expect and os.path.getsize(path) != expect:
                print("  附件 %s 大小校验失败，拒绝上传" % an)
                continue
            size = os.path.getsize(path)
            if quota_known and not a.force_quota and used + size > GITEE_QUOTA:
                print("  跳过 %s：配额不够（已用 %.1f MB + 本包 %.1f MB > %d MB）。"
                      % (an, used / 1048576, size / 1048576, GITEE_QUOTA // 1048576))
                print("     腾出空间后重跑本脚本会自动补传；确实要硬传用 --force-quota。")
                continue
            if a.dry_run:
                print("  [dry-run] 将上传 %s（%.2f MB）" % (an, size / 1048576))
                if quota_known:
                    used += size
                continue
            print("  上传 %s（%.2f MB）..." % (an, size / 1048576))
            ok, info = upload_asset(rid, path, tok)
            print("  -> %s %s" % ("成功" if ok else "失败", info))
            if ok and quota_known:
                used += size

    print("\n完成。")
    if not a.dry_run:
        # 「Gitee 只留最新两版附件」是发版自带的一步：新版本刚传完再清理更早的，
        # 顺序不能反——先删旧再建新，latest 会被旧版本顶掉（见文件头 5.4 节）。
        if not a.no_prune:
            print("\n=== 自动清理第 %d 个及更早版本的安装包（正文保留）===" % (KEEP_RECENT + 1))
            prune_old_assets(tok)
        # 每次动过 Gitee 都必须确认「最新版」没有跑偏，这是 5.4 节的硬规矩
        ok, _ = verify_order(rels, tok, quiet=True)
        if not ok:
            print("警告：版本顺序校验未通过，请先修好再对外说「Gitee 最新版可下载」。")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
