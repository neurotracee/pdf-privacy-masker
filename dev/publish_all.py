#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键发布：本地 exe/apk + GitHub CI 构建的 AppImage → GitHub 与 Gitee。

一条命令搞定两个平台，和发 Windows / 安卓端时的流程一样：

    python dev/publish_all.py v1.4.9.1

流程：
  1. 把 release/<tag>/ 里的 exe、apk 传到 GitHub Release（版本号先对账）；
  2. GitHub Actions 构建好的 AppImage 由 dev/sync_gitee_releases.py 自动取回
     本机缓存（GitHub API 优先、ghproxy 兜底，按 API 字节数校验），再和
     exe/apk 一起传到 Gitee Release；
  3. 结束时核对 Gitee 上三端安装包是否齐全。

为什么 AppImage 要经本机一次：Linux 包只能在 Linux 上构建，而实测
GitHub Actions（美国）直传 Gitee 的 88 MB 附件会 30 分钟超时、收到 0 字节。
这个取回动作封装在脚本里、全自动，不用手工下载，以后每次发版都一样。

凭据：~/.github_token、~/.gitee_token（或同名环境变量）。
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = os.path.join(ROOT, "dev")
GE_API = "https://gitee.com/api/v5/repos/bio234/pdf-privacy-masker"


def run(script, *args):
    cmd = [sys.executable, os.path.join(DEV, script), *args]
    print("\n== %s %s ==" % (script, " ".join(args)), flush=True)
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc:
        print("!! %s 失败（退出码 %d），停止后续步骤" % (script, rc), flush=True)
        sys.exit(rc)


def check_gitee(tag):
    tok = (os.environ.get("GITEE_TOKEN") or "").strip()
    if not tok:
        p = os.path.join(os.path.expanduser("~"), ".gitee_token")
        if os.path.exists(p):
            tok = open(p, encoding="utf-8").read().strip()
    url = "%s/releases/tags/%s%s" % (
        GE_API, urllib.parse.quote(tag), ("?access_token=" + tok if tok else ""))
    with urllib.request.urlopen(url, timeout=60) as r:
        rel = json.loads(r.read().decode("utf-8", "replace"))
    names = [a.get("name") or "" for a in (rel.get("assets") or [])]
    need = {
        "Windows": any(n.lower().endswith(".exe") for n in names),
        "Android": any(n.lower().endswith(".apk") for n in names),
    }
    # GitHub 端（含 CI 产出的 AppImage）由 AI 全程负责；Gitee 端 AppImage 等用户
    # 手动上传，或等用户把文件路径给我后由我代传。没传只是待办，不算失败。
    linux_ok = any(n.lower().endswith(".appimage") for n in names)
    print("\n== Gitee 三端附件核对 ==")
    for k, v in need.items():
        print("  %-8s %s" % (k, "✅" if v else "❌ 缺失"))
    print("  %-8s %s" % ("Linux", "✅" if linux_ok else "⏳ 待处理：你手动传，或把文件给我代传"))
    print("  Gitee 发布页：https://gitee.com/bio234/pdf-privacy-masker/releases/tag/%s" % tag)
    return 0 if all(need.values()) else 2


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("v"):
        print("用法: python dev/publish_all.py v1.4.9.1")
        return 2
    tag = sys.argv[1]
    run("publish_github_release.py", "--tag", tag)
    run("sync_gitee_releases.py", "--tag", tag, "--no-prune")
    return check_gitee(tag)


if __name__ == "__main__":
    sys.exit(main())
