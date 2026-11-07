#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把本地 release/<tag>/ 里的安装包发布成 GitHub Release。

用法：
    python dev/publish_github_release.py --tag v1.4.3 --dry-run
    python dev/publish_github_release.py --tag v1.4.3

凭据：
    在 https://github.com/settings/tokens 生成 classic token（只需 repo 权限），
    写到 ~/.github_token 或环境变量 GITHUB_TOKEN。

行为：
    - Release 不存在就创建，已存在就更新标题/正文（幂等）
    - 附件按名字判断，已上传的跳过，不会重复传
    - 正文取 release/<tag>/RELEASE-NOTES.md
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

GH_OWNER, GH_REPO = "neurotracee", "pdf-privacy-masker"
API = "https://api.github.com/repos/%s/%s" % (GH_OWNER, GH_REPO)
UPLOADS = "https://uploads.github.com/repos/%s/%s" % (GH_OWNER, GH_REPO)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")


def token():
    p = os.path.join(HOME, ".github_token")
    if os.path.exists(p):
        t = io.open(p, encoding="utf-8").read().strip()
        if t:
            return t
    return (os.environ.get("GITHUB_TOKEN") or "").strip()


def api(url, method="GET", data=None, tok="", retries=6):
    """走系统 curl（本机 GitHub 需要 -k，其余情况正常校验）。"""
    cmd = ["curl", "-s", "-k", "--noproxy", "127.0.0.1", "--max-time", "90",
           "-X", method, "-H", "Accept: application/vnd.github+json",
           "-H", "X-GitHub-Api-Version: 2022-11-28",
           "-H", "User-Agent: pdfmask-publish"]
    if tok:
        cmd += ["-H", "Authorization: Bearer " + tok]
    body = None
    if data is not None:
        cmd += ["-H", "Content-Type: application/json"]
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    cmd += ["-w", "\n%{http_code}", url]
    for i in range(retries):
        args = cmd[:] + (["--data-binary", "@-"] if body is not None else [])
        r = subprocess.run(args, input=body, capture_output=True)
        out = r.stdout.decode("utf-8", "replace") if r.stdout else ""
        code = 0
        if "\n" in out:
            out, _, tail = out.rpartition("\n")
            try:
                code = int(tail.strip())
            except Exception:
                code = 0
        # 5xx 多半是本机加速通道临时抖了一下（502 常见），退避后重试；
        # 4xx 是真正的业务错误，立刻返回。
        if code and code < 500:
            try:
                return code, (json.loads(out) if out.strip() else {})
            except Exception:
                return code, {"raw": out[:300]}
        if code:
            last = (code, {"raw": out[:300]})
        else:
            last = (0, {"err": "curl 失败"})
        time.sleep(2.0 * (i + 1))
    return last


def upload_asset(rid, path, tok):
    name = os.path.basename(path)
    cmd = ["curl", "-s", "-k", "--noproxy", "127.0.0.1", "--max-time", "900",
           "-X", "POST", "-H", "Content-Type: application/octet-stream",
           "-H", "Authorization: Bearer " + tok,
           "-H", "User-Agent: pdfmask-publish",
           "-T", path,
           "-w", "\n%{http_code}",
           "%s/releases/%s/assets?name=%s" % (UPLOADS, rid, name)]
    r = subprocess.run(cmd, capture_output=True)
    out = r.stdout.decode("utf-8", "replace") if r.stdout else ""
    code = 0
    if "\n" in out:
        out, _, tail = out.rpartition("\n")
        try:
            code = int(tail.strip())
        except Exception:
            code = 0
    return code in (200, 201), out[:160]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    d = os.path.join(ROOT, "release", a.tag)
    notes = os.path.join(d, "RELEASE-NOTES.md")
    if not os.path.isdir(d) or not os.path.exists(notes):
        print("找不到 %s 或 RELEASE-NOTES.md" % d)
        return 1
    body = io.open(notes, encoding="utf-8").read()
    title = a.title or a.tag
    files = sorted(os.path.join(d, f) for f in os.listdir(d)
                   if f.lower().endswith((".exe", ".apk")))
    print("标题: %s | 正文 %d 字符 | 附件 %d 个" % (title, len(body), len(files)))

    tok = token()
    if not tok and not a.dry_run:
        print("缺少 GitHub 令牌：写入 %s 或设置 GITHUB_TOKEN" % os.path.join(HOME, ".github_token"))
        return 1

    code, rel = api(API + "/releases/tags/" + a.tag, tok=tok)
    if code == 200:
        print("已存在 release id=%s，更新标题与正文" % rel.get("id"))
        if not a.dry_run:
            c, rel = api(API + "/releases/%s" % rel["id"], "PATCH",
                         {"name": title, "body": body}, tok)
            print("  PATCH -> HTTP %s" % c)
    elif code == 404:
        print("不存在，创建 %s" % a.tag)
        if a.dry_run:
            for f in files:
                print("  [dry-run] 将上传 %s（%.2f MB）" % (os.path.basename(f),
                                                            os.path.getsize(f) / 1048576))
            return 0
        c, rel = api(API + "/releases", "POST",
                     {"tag_name": a.tag, "name": title, "body": body,
                      "draft": False, "prerelease": False}, tok)
        print("  POST -> HTTP %s" % c)
        if c not in (200, 201):
            print("  失败: %s" % str(rel)[:300])
            return 1
    else:
        print("查询失败 HTTP %s: %s" % (code, str(rel)[:200]))
        return 1

    rid = rel.get("id")
    have = {x.get("name") for x in (rel.get("assets") or [])}
    for f in files:
        n = os.path.basename(f)
        if n in have:
            print("  附件 %s 已存在，跳过" % n)
            continue
        if a.dry_run:
            print("  [dry-run] 将上传 %s" % n)
            continue
        ok = False
        for i in range(3):
            ok, info = upload_asset(rid, f, tok)
            print("  上传 %s 第 %d 次 -> %s" % (n, i + 1, "成功" if ok else "失败 %s" % info))
            if ok:
                break
            time.sleep(3 * (i + 1))

    print("\n完成：https://github.com/%s/%s/releases/tag/%s" % (GH_OWNER, GH_REPO, a.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
