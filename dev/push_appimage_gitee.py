#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 专用：把构建好的 AppImage 直接推到 Gitee 对应 tag 的 Release。

在 GitHub Actions 的 ubuntu runner 上、AppImage 构建并冒烟通过后调用。
包就在本地 dist/，直接传给 Gitee——不像本机那样要从 GitHub 把 88 MB
拉回来再上传（多此一举且慢）。

设计要点：
- 幂等：同名附件已存在就跳过；
- 配额：上传前统计 Gitee 全部附件，已用 + 本包 > 1 GB 才跳过并说明；
- 正文：Gitee 上还没有该 tag 时，先从 GitHub 读标题/正文创建 Release，
  保证「历代更新说明都要有」；
- 只用标准库 + curl，CI 不需要额外装包。

用法：
    GITEE_TOKEN=xxx GITHUB_TOKEN=yyy python dev/push_appimage_gitee.py v1.4.9.1 dist/*.AppImage dist/SHA256SUMS-linux.txt
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GE_OWNER, GE_REPO = "bio234", "pdf-privacy-masker"
GH_OWNER, GH_REPO = "neurotracee", "pdf-privacy-masker"
GE_API = "https://gitee.com/api/v5/repos/%s/%s" % (GE_OWNER, GE_REPO)
GH_API = "https://api.github.com/repos/%s/%s" % (GH_OWNER, GH_REPO)
QUOTA = 1024 ** 3
GE_TOK = os.environ.get("GITEE_TOKEN", "").strip()
GH_TOK = os.environ.get("GITHUB_TOKEN", "").strip()
TARGET = "main"


def call(url, method="GET", data=None, tok=""):
    """JSON 接口，带 403/429 限流退避。"""
    sep = "&" if "?" in url else "?"
    if tok:
        url += sep + "access_token=" + tok if "api.github.com" not in url else url
    body = None
    headers = {"User-Agent": "pdfmask-ci"}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if tok and "api.github.com" in url:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                raw = r.read().decode("utf-8", "replace")
                return r.status, _json(raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code in (403, 429):
                time.sleep(3 * (i + 1))
                continue
            return e.code, _json(raw)
        except Exception as e:
            if i == 4:
                return 0, str(e)
            time.sleep(3 * (i + 1))
    return 0, ""


def _json(raw):
    raw = (raw or "").strip()
    if raw.startswith(("{", "[")):
        try:
            return json.loads(raw)
        except Exception:
            pass
    return raw


def used_bytes():
    """Gitee 全仓库附件占用。"""
    c, rels = call(GE_API + "/releases?per_page=100", tok=GE_TOK)
    if c != 200 or not isinstance(rels, list):
        print("  取 Gitee 版本列表失败（HTTP %s），配额按 0 计" % c)
        return 0
    total = 0
    for r in rels:
        c2, files = call(GE_API + "/releases/%s/attach_files" % r.get("id"), tok=GE_TOK)
        if c2 == 200 and isinstance(files, list):
            total += sum(int(f.get("size") or 0) for f in files)
    return total


def find_release(tag):
    c, r = call(GE_API + "/releases/tags/" + urllib.parse.quote(tag), tok=GE_TOK)
    return r if c == 200 and isinstance(r, dict) and r.get("id") else None


def ensure_release(tag):
    """Gitee 没有这个 tag 就按 GitHub 的标题/正文创建，保证更新说明不丢。"""
    rel = find_release(tag)
    if rel:
        return rel
    print("  Gitee 还没有 %s，从 GitHub 取正文创建" % tag)
    c, g = call(GH_API + "/releases/tags/" + urllib.parse.quote(tag), tok=GH_TOK)
    if c != 200 or not isinstance(g, dict):
        print("  取 GitHub Release 失败（HTTP %s），无法创建" % c)
        return None
    body = (g.get("body") or "").replace("\r\n", "\n")
    c2, r = call(GE_API + "/releases", "POST", {
        "tag_name": tag,
        "name": g.get("name") or tag,
        "body": body,
        "target_commitish": TARGET,
        "prerelease": bool(g.get("prerelease")),
    }, GE_TOK)
    if c2 in (200, 201) and isinstance(r, dict) and r.get("id"):
        print("  创建成功（正文 %d 字符）" % len(body))
        return r
    print("  创建失败：HTTP %s %s" % (c2, str(r)[:200]))
    return None


def upload(rid, path):
    cmd = ["curl", "-sSL", "--max-time", "900", "-X", "POST",
           "-F", "access_token=" + GE_TOK,
           "-F", "file=@" + path,
           "%s/releases/%s/attach_files" % (GE_API, rid)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    d = _json(out)
    if isinstance(d, dict) and d.get("browser_download_url"):
        return True, d["browser_download_url"]
    return False, (out or "(空响应)")[:200]


def main():
    args = sys.argv[1:]
    if not GE_TOK or len(args) < 2:
        print("用法: GITEE_TOKEN=xxx GITHUB_TOKEN=yyy %s <tag> <文件...>" % sys.argv[0])
        return 2
    tag, files = args[0], args[1:]
    for f in files:
        if not os.path.isfile(f):
            print("文件不存在:", f)
            return 2

    rel = ensure_release(tag)
    if not rel:
        return 1
    rid = rel["id"]

    have = {a.get("name") for a in (rel.get("assets") or []) if a.get("name")}
    c, af = call(GE_API + "/releases/%s/attach_files" % rid, tok=GE_TOK)
    if c == 200 and isinstance(af, list):
        have |= {a.get("name") for a in af if a.get("name")}

    used = used_bytes()
    print("Gitee 附件已用 %.1f MB / 1024 MB，剩余 %.1f MB" %
          (used / 1048576, (QUOTA - used) / 1048576))

    fail = 0
    for f in files:
        name = os.path.basename(f)
        size = os.path.getsize(f)
        if name in have:
            print("  已存在，跳过:", name)
            continue
        if used + size > QUOTA:
            print("  配额不足，跳过 %s（已用 %.1f MB + 本包 %.1f MB > 1024 MB）" %
                  (name, used / 1048576, size / 1048576))
            print("     腾出空间后重跑本脚本会自动补传。")
            fail += 1
            continue
        print("  上传 %s（%.1f MB）..." % (name, size / 1048576))
        ok, info = upload(rid, f)
        print("   -> %s %s" % ("成功" if ok else "失败", info[:120]))
        if ok:
            used += size
        else:
            fail += 1

    print("完成：%s" % ("全部成功" if not fail else "%d 个失败" % fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
