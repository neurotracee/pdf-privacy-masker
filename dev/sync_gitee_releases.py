#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 GitHub 的每一个 Release（标题 / 正文 / 安装包）原样搬到 Gitee。

用法：
    python dev/sync_gitee_releases.py --dry-run      # 只看计划，不写入
    python dev/sync_gitee_releases.py                # 真正创建 + 上传（幂等）
    python dev/sync_gitee_releases.py --tag v1.4.3   # 只处理某一个版本
    python dev/sync_gitee_releases.py --reorder      # 重建全部 Release，让新版排在最上面

为什么要 `--reorder`
--------------------
Gitee 的 Release 列表是**按创建时间倒序**排的，没有「按版本号排序」这回事。
如果把历史版本补传到 Gitee，补得最晚的那个（往往是最旧的版本）就会顶在列表
第一位，看起来像「最新版」，用户点进去下载到的是老版本。
`--reorder` 会按版本号**升序**重放：先删掉现有 Release，再依次创建
v1.3.0 → v1.4.0 → v1.4.1 → …，最后一次创建的最新版自然落在最上面。

凭据：
    Gitee 私人令牌，写在 ~/.gitee_token 或环境变量 GITEE_TOKEN（权限需含 projects）。
    GitHub 侧读公开 API 不需要令牌；本地缺的安装包会用 ghproxy 镜像下载。

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
    t = [int(x) for x in nums[:3]]
    while len(t) < 3:
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


def download(name, tag, out_name):
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, out_name)
    if os.path.exists(out) and os.path.getsize(out) > 1024 * 1024:
        print("  已有缓存 %s（%.2f MB）" % (out_name, os.path.getsize(out) / 1048576))
        return out
    url = "https://ghproxy.net/https://github.com/%s/%s/releases/download/%s/%s" % (
        GH_OWNER, GH_REPO, tag, urllib.parse.quote(name))
    print("  下载 %s ..." % name)
    r = subprocess.run(["curl", "-sL", "--noproxy", "*", "--max-time", "600", url, "-o", out,
                        "-w", "%{http_code}"], capture_output=True, text=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 1024 * 1024
    print("  -> HTTP %s，%.2f MB" % (r.stdout.strip(), (os.path.getsize(out) / 1048576) if ok else 0))
    return out if ok else None


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


def upload_all(rel, rid, tok, dry):
    tag = rel["tag_name"]
    for asset in (rel.get("assets") or []):
        an = asset["name"]
        if an in (REMOTE_FALLBACK.get(tag) or []):
            path = download(an, tag, an)
        else:
            path = local_asset(tag, an) or download(an, tag, an)
        if not path:
            print("  附件 %s 拿不到，跳过" % an)
            continue
        if dry:
            print("  [dry-run] 将上传 %s（%.2f MB）" % (an, os.path.getsize(path) / 1048576))
            continue
        print("  上传 %s（%.2f MB）..." % (an, os.path.getsize(path) / 1048576))
        ok, info = upload_asset(rid, path, tok)
        print("  -> %s %s" % ("成功" if ok else "失败", info))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--skip-upload", action="store_true")
    ap.add_argument("--replace-assets", action="store_true",
                    help="已存在的 Release：整个删掉重建并重传附件（重发同一版本号时用）")
    ap.add_argument("--reorder", action="store_true",
                    help="按版本号升序重建全部 Release，修正 Gitee 的倒序排列")
    a = ap.parse_args()

    tok = token()
    if not tok and not a.dry_run:
        print("缺少 Gitee 令牌：请写入 %s 或设置 GITEE_TOKEN" % os.path.join(HOME, ".gitee_token"))
        return 1

    rels = gh_releases()
    if not rels:
        return 1
    print("GitHub 共 %d 个 Release：%s\n" % (len(rels), ", ".join(r["tag_name"] for r in rels)))

    if a.reorder:
        reorder(rels, tok, a.dry_run)
        print("\n完成。")
        return 0

    existing = {r.get("tag_name"): r for r in gitee_releases()}
    print("Gitee 现有 %d 个：%s\n" % (len(existing), ", ".join(existing) or "无"))

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
            if an in (REMOTE_FALLBACK.get(tag) or []):
                path = download(an, tag, an)
            else:
                path = local_asset(tag, an) or download(an, tag, an)
            if not path:
                print("  附件 %s 拿不到，跳过" % an)
                continue
            if a.dry_run:
                print("  [dry-run] 将上传 %s（%.2f MB）" % (an, os.path.getsize(path) / 1048576))
                continue
            print("  上传 %s（%.2f MB）..." % (an, os.path.getsize(path) / 1048576))
            ok, info = upload_asset(rid, path, tok)
            print("  -> %s %s" % ("成功" if ok else "失败", info))

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
