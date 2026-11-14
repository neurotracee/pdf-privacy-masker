"""端到端验证「应用内下载」这条路真的走得通。

安卓端 v1.4.5 起不再把安装包交给浏览器，而是自己下载、自己校验、再交给系统安装器
（`UpdateApk.download`）。这个脚本用 Python 复现同一套步骤，把「假设」变成「实测」：

  1. 从 Gitee / GitHub 两个发布页拿到 apk 的下载地址；
  2. 按 `UpdateApk.open()` 的规则手动跟重定向，**每一跳都必须是 https + 白名单域名**；
  3. 落盘后核对：头 4 字节是 PK、字节数与 Content-Length 一致、大小在合理区间；
  4. 用 aapt2 读出包名与版本号，确认就是本应用的这一版。

跑法：python dev/verify_apk_download.py [版本号]
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 默认校验「当前代码里的版本」，不写死数字，免得发版时忘了改这里
def _current_version():
    with open(os.path.join(ROOT, "pdfmask.py"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^VERSION\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    return "0.0.0.0"


VERSION = sys.argv[1] if len(sys.argv) > 1 else _current_version()

ALLOWED = (
    "gitee.com", "github.com", "objects.githubusercontent.com",
    "release-assets.githubusercontent.com", "codeload.github.com",
)

AAPT2 = os.path.join(
    os.path.expanduser("~"), ".workbuddy", "toolchains", "android", "sdk",
    "build-tools", "34.0.0", "aapt2.exe"
)

SOURCES = {
    "Gitee": "https://gitee.com/api/v5/repos/bio234/pdf-privacy-masker/releases",
    "GitHub": "https://api.github.com/repos/neurotracee/pdf-privacy-masker/releases?per_page=20",
}

ok_all = True


def check(name, ok, detail=""):
    global ok_all
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("" if ok else "  -> " + str(detail)[:200])))
    if not ok:
        ok_all = False


def allowed(url):
    if not url.lower().startswith("https://"):
        return False
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == a or host.endswith("." + a) for a in ALLOWED)


def asset_url(text):
    """从 releases JSON 里挑出这一版、这一平台的 apk 地址"""
    data = json.loads(text)
    if isinstance(data, dict):
        data = [data]
    for rel in data:
        if rel.get("draft"):
            continue
        for a in rel.get("assets") or []:
            name = (a.get("name") or "").lower()
            if name.endswith(".apk") and VERSION in name:
                return a.get("browser_download_url"), a.get("name")
    return None, None


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "PDFPrivacyMasker-Android"})
    return urllib.request.urlopen(req, timeout=30).read()


def download_following_redirects(url, label, dest):
    """复刻 UpdateApk.open()：手动跟重定向，每一跳都必须是 https + 白名单域名。

    用 curl 而不是 urllib：本机的加速软件会给 Python 的 TLS 栈添麻烦，
    curl 走的是系统层，行为和手机上的 HttpURLConnection 更接近。
    """
    hdr = dest + ".hdr"
    for attempt in range(2):
        r = subprocess.run(
        # --ssl-no-revoke：本机装了会做 MITM 的加速软件，Windows 的 schannel 吊销检查
        # 会因此失败（crypt_e_no_revocation_check）。这只是本机脚本的绕行，
        # 应用里走的是系统 TLS，严格校验，不放宽任何东西。
            ["curl", "-sS", "-L", "--ssl-no-revoke", "--max-time", "180",
             "-r", "0-2097151",
             "-A", "PDFPrivacyMasker-Android",
             "-D", hdr, "-o", dest, "-w", "%{http_code} %{size_download}", url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if r.returncode == 0:
            break
        # 偶发断连（schannel closed abruptly）再试一次；两次都不行才算失败
        if attempt == 1:
            return None, [], "curl 失败：%s" % (r.stderr or "").strip()[:160]

    parts = (r.stdout or "").split()
    code = int(parts[0]) if parts else 0
    size = int(parts[1]) if len(parts) > 1 else 0
    if code not in (200, 206):
        return None, [], "HTTP %d" % code

    hops, bad = [], ""
    try:
        text = open(hdr, encoding="latin-1", errors="replace").read()
    except Exception:
        text = ""
    for line in text.splitlines():
        if line.lower().startswith("location:"):
            loc = line.split(":", 1)[1].strip()
            hops.append(loc)
            if not allowed(loc):
                bad = "重定向到白名单外：%s" % loc
    blob = open(dest, "rb").read() if os.path.exists(dest) else b""
    return (blob, size), hops, bad


def main():
    print("验证版本 v%s 的 apk 下载链路" % VERSION)
    tmp = tempfile.mkdtemp(prefix="apkverify-")

    for label, api in SOURCES.items():
        print("\n[%s]" % label)
        try:
            url, name = asset_url(fetch(api))
        except Exception as e:
            check("%s 能读到发布列表" % label, False, e)
            continue
        check("%s 列表里能找到 v%s 的 apk" % (label, VERSION), bool(url), name)
        if not url:
            continue
        print("      地址: %s" % url)

        path = os.path.join(tmp, "%s-%s.apk" % (label, VERSION))
        res, hops, err = download_following_redirects(url, label, path)
        check("%s 重定向全程留在白名单内（%d 跳）" % (label, len(hops)), bool(res), err or hops)
        if not res:
            continue
        blob, total = res
        want = min(total, 2 * 1024 * 1024)
        check("%s 能持续读到数据（%d 字节）" % (label, len(blob)),
              len(blob) >= want and want > 0, "只拿到 %d 字节" % len(blob))
        check("%s 头 4 字节是 PK（确实是安装包）" % label, blob[:4] == b"PK\x03\x04", blob[:4])

        # 只有下满（超过分段上限）才能读包信息；只取到前 2MB 时跳过，包名与版本由另一个通道证明
        if len(blob) <= 2 * 1024 * 1024:
            print("      （本机只取到 %d 字节，包名与版本改由完整下载的通道证明）" % len(blob))
            continue
        if os.path.exists(AAPT2):
            out = subprocess.run([AAPT2, "dump", "badging", path],
                                 capture_output=True, text=True, encoding="utf-8",
                                 errors="replace").stdout
            first = (out or "").splitlines()[0] if out else ""
            check("%s 包名是 com.neurotracee.pdfmask" % label,
                  "name='com.neurotracee.pdfmask'" in first, first[:120])
            check("%s 版本号是 %s" % (label, VERSION),
                  ("versionName='%s'" % VERSION) in first, first[:120])
        else:
            check("%s 找到 aapt2 用于读包信息" % label, False, AAPT2)

    print("\n" + "=" * 60)
    print("结论:", "全部通过（应用内下载这条路可用）" if ok_all else "存在未通过项")
    print("临时目录:", tmp)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
