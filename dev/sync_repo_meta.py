# -*- coding: utf-8 -*-
"""一条命令同步两个平台的仓库元数据（简介 / 主页 / 标签）。

为什么需要这个脚本：
  GitCode / Gitee / GitHub 的设置分散在网页里，改一次要开三个页面点半天，
  而且容易改了一头忘了另一头。这个脚本把「两个平台该长什么样」写成常量，
  跑一次就把两边拉齐；以后要调整，只改下面的常量再跑。

用法：
  python dev/sync_repo_meta.py            # 同步
  python dev/sync_repo_meta.py --dry-run  # 只看会改成什么，不写入
  python dev/sync_repo_meta.py --show     # 只读当前值

令牌：
  GitHub  ~/.github_token   需要 repo 权限（改 topics 需要 public_repo 即可）
  Gitee   ~/.gitee_token    需要 projects 权限

踩过的坑（别改回去）：
  1. Gitee 的 project_labels 接口**只认一种格式**：body 直接是 JSON 字符串
     数组 + Content-Type: application/json。写成 {"project_labels": [...]}
     会报 `no implicit conversion of Hash into String`，写成表单会报
     `no implicit conversion of nil into String`。
  2. Gitee 的 PATCH /repos/{owner}/{repo} 不带 name 参数时，description 会被
     静默忽略（返回 200 但没改），所以下面必须带上 name。
  3. Gitee 偶发 RemoteDisconnected，所有请求都带重试。
"""

import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GH_OWNER = "neurotracee"
GH_REPO = "pdf-privacy-masker"
GT_OWNER = "bio234"
GT_REPO = "pdf-privacy-masker"

HOMEPAGE_GH = "https://gitee.com/bio234/pdf-privacy-masker"
HOMEPAGE_GT = "https://github.com/neurotracee/pdf-privacy-masker"

DESC = (
    "本地离线运行、无需 AI 模型的 PDF 隐私信息自动打码工具，可识别手机号、身份证号、"
    "银行卡号、邮箱、姓名、地址、出生日期等，打码后文字层一并抹除，不可还原。"
    " | Offline PDF redaction (no AI model): detects phone/ID/bank numbers, emails, "
    "names, addresses and wipes the text layer so it cannot be recovered. "
    "Windows + Android."
)

# GitHub topics：小写、用连字符，数量上限 20
GH_TOPICS = [
    "pdf", "pdf-processing", "pdf-redaction", "redaction", "privacy",
    "privacy-protection", "privacy-tools", "desensitization", "anonymization",
    "de-identification", "pii", "pymupdf", "python", "windows", "android",
    "offline", "local-first", "chinese",
]

# Gitee 项目标签：会尽量匹配平台已有的标签，没匹配上的也会创建
GT_LABELS = [
    "PDF", "Python", "Windows", "Android", "隐私保护", "数据脱敏",
    "脱敏", "安全", "PyMuPDF", "离线", "开源工具", "效率工具",
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def read_token(name):
    path = os.path.join(os.path.expanduser("~"), name)
    if not os.path.exists(path):
        sys.exit("找不到令牌文件：%s" % path)
    return io.open(path, encoding="utf-8").read().strip()


def http(url, method="GET", body=None, headers=None, tries=5):
    """带重试的请求。Gitee 偶尔直接断连，重试比失败好。"""
    hdrs = {"User-Agent": "pdfmask-sync-meta"}
    hdrs.update(headers or {})
    last = None
    for i in range(tries):
        req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=60) as f:
                raw = f.read().decode("utf-8", "replace")
                return f.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
        except urllib.error.HTTPError as e:
            # 4xx 是参数问题，重试没有意义
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 - 网络异常统一重试
            last = e
            time.sleep(1.5 * (i + 1))
    return 0, "网络异常：%r" % (last,)


def gh_api(path):
    return "https://api.github.com/repos/%s/%s%s" % (GH_OWNER, GH_REPO, path)


def gt_api(path):
    return "https://gitee.com/api/v5/repos/%s/%s%s" % (GT_OWNER, GT_REPO, path)


def sync_github(tok, dry):
    auth = {"Authorization": "Bearer " + tok,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}
    code, cur = http(gh_api(""), headers=auth)
    if code != 200:
        print("  [GitHub] 读取失败 %s %s" % (code, str(cur)[:160]))
        return False
    print("  [GitHub] 现在简介长度 %d，主页 %s，标签 %d 个"
          % (len(cur.get("description") or ""), cur.get("homepage") or "（空）",
             len(cur.get("topics") or [])))
    if dry:
        print("  [GitHub] 将写入：主页=%s，标签=%s" % (HOMEPAGE_GH, ", ".join(GH_TOPICS)))
        return True

    body = json.dumps({"description": DESC, "homepage": HOMEPAGE_GH}).encode("utf-8")
    code, r = http(gh_api(""), "PATCH", body, dict(auth, **{"Content-Type": "application/json"}))
    if code not in (200, 201):
        print("  [GitHub] 简介/主页写入失败 %s %s" % (code, str(r)[:200]))
        return False

    body = json.dumps({"names": GH_TOPICS}).encode("utf-8")
    code, r = http(gh_api("/topics"), "PUT", body, dict(auth, **{"Content-Type": "application/json"}))
    if code not in (200, 201):
        print("  [GitHub] 标签写入失败 %s %s" % (code, str(r)[:200]))
        return False
    print("  [GitHub] 已写入 %d 个标签" % len(r.get("names") or []))
    return True


def sync_gitee(tok, dry):
    code, cur = http(gt_api("?access_token=" + tok))
    if code != 200:
        print("  [Gitee] 读取失败 %s %s" % (code, str(cur)[:160]))
        return False
    print("  [Gitee] 现在简介长度 %d，主页 %s"
          % (len(cur.get("description") or ""), cur.get("homepage") or "（空）"))

    code, labels = http(gt_api("/project_labels?access_token=" + tok))
    if code == 200 and isinstance(labels, list):
        print("  [Gitee] 现在标签：%s" % ", ".join(x["name"] for x in labels))
    if dry:
        print("  [Gitee] 将写入：简介同上，主页=%s，标签=%s" % (HOMEPAGE_GT, ", ".join(GT_LABELS)))
        return True

    # 坑 2：必须带 name，否则 description 被静默忽略
    form = urllib.parse.urlencode({
        "access_token": tok,
        "name": GT_REPO,
        "description": DESC,
        "homepage": HOMEPAGE_GT,
    }).encode("utf-8")
    code, r = http(gt_api(""), "PATCH", form,
                   {"Content-Type": "application/x-www-form-urlencoded"})
    if code not in (200, 201):
        print("  [Gitee] 简介/主页写入失败 %s %s" % (code, str(r)[:200]))
        return False
    if isinstance(r, dict):
        print("  [Gitee] 简介已生效（长度 %d）" % len(r.get("description") or ""))

    # 坑 1：body 直接是 JSON 数组
    body = json.dumps(GT_LABELS, ensure_ascii=False).encode("utf-8")
    code, r = http(gt_api("/project_labels?access_token=" + tok), "PUT", body,
                   {"Content-Type": "application/json"})
    if code not in (200, 201):
        print("  [Gitee] 标签写入失败 %s %s" % (code, str(r)[:200]))
        return False
    names = [x["name"] for x in r] if isinstance(r, list) else []
    print("  [Gitee] 已写入 %d 个标签：%s" % (len(names), ", ".join(names)))
    return True


def main():
    dry = "--dry-run" in sys.argv
    show = "--show" in sys.argv
    print("同步仓库元数据%s" % ("（预览，不写入）" if dry else ""))
    gh = read_token(".github_token")
    gt = read_token(".gitee_token")

    if show:
        sync_github(gh, True)
        sync_gitee(gt, True)
        return

    ok_gh = sync_github(gh, dry)
    ok_gt = sync_gitee(gt, dry)
    print("结论：GitHub %s，Gitee %s" % ("OK" if ok_gh else "失败", "OK" if ok_gt else "失败"))
    sys.exit(0 if (ok_gh and ok_gt) else 1)


if __name__ == "__main__":
    main()
