#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键发布：本地 exe/apk + GitHub CI 构建的 AppImage → GitHub 与 Gitee。

一条命令搞定两个平台，和发 Windows / 安卓端时的流程一样：

    python dev/publish_all.py v1.4.9.1

流程：
  1. 把 release/<tag>/ 里的 exe、apk 传到 GitHub Release（版本号先对账）；
  2. 等 GitHub Actions 把 AppImage 挂到该 Release，再用 dev/fetch_appimage_accel.py
     从加速站（github.akams.cn 的公益节点）自动测速、多节点分段取回本机，
     并用 Release 的 SHA256SUMS-linux.txt 校验；
  3. 三端包一起传到 Gitee Release（校验字节数、清旧版附件）；
  4. 结束时核对 Gitee 上三端安装包是否齐全。

为什么 AppImage 要经本机一次：Linux 包只能在 Linux 上构建，而实测
GitHub Actions（美国）直传 Gitee 的 88 MB 附件会 30 分钟超时、收到 0 字节。
下载走加速节点后 88 MB 约 40 秒，比手动点网页选节点再等浏览器下载更快。

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
    # 正常发版时 AppImage 由第 2 步自动取回并上传；这里缺失说明自动步骤没成，
    # 照日志补一次即可（也可以自己从 GitHub 下载后手动传，或把文件交给 AI）。
    linux_ok = any(n.lower().endswith(".appimage") for n in names)
    print("\n== Gitee 三端附件核对 ==")
    for k, v in need.items():
        print("  %-8s %s" % (k, "✅" if v else "❌ 缺失"))
    print("  %-8s %s" % ("Linux", "✅" if linux_ok else "❌ 缺失（自动取回没成，看上面的日志补一次）"))
    print("  Gitee 发布页：https://gitee.com/bio234/pdf-privacy-masker/releases/tag/%s" % tag)
    return 0 if all(need.values()) and linux_ok else 2


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("v"):
        print("用法: python dev/publish_all.py v1.4.9.1")
        return 2
    tag = sys.argv[1]
    rel_dir = os.path.join(ROOT, "release", tag)
    run("publish_github_release.py", "--tag", tag)
    # 等 CI 出包 → 走加速节点取回（约 40 秒）→ 落到 release/<tag>/，
    # 这样后面的同步脚本直接从本地传，不必再从 GitHub 拉一遍。
    run("fetch_appimage_accel.py", "--tag", tag, "--wait-ci", "30", "--out", rel_dir)
    run("sync_gitee_releases.py", "--tag", tag, "--no-prune", "--with-appimage")
    return check_gitee(tag)


if __name__ == "__main__":
    sys.exit(main())
