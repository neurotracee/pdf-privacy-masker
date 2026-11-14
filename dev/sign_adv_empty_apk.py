#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给平台的「含签名的 APK 空包」签名，用于 ADV 应用验证。

ADV（Android 侧载应用开发者身份验证，OPPO / vivo / 小米 / 荣耀四家互认）
验的是「这份签名属于这个开发者」。平台会发一个空壳 apk，要求你用它签名后回传；
平台只核对签名归属，不看你回传的包是不是真正的应用包。

用法：
    python dev/sign_adv_empty_apk.py <平台下载的空包.apk> [-o 输出.apk]

签名用的密钥读 android/keystore.properties，和正式发版是同一把。
**不要换密钥**：ADV 绑定的是「包名 + 签名」，一换就得重新验证，
而且用户已装的老版本无法被新包覆盖升级。

做完这一步，回到平台：上传输出文件 → 关联包名 com.neurotracee.pdfmask → 提交，机审通过后生效。
"""

import argparse
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "com.neurotracee.pdfmask"

# apk 里属于签名的条目，重签前要先剔掉，否则旧签名会和新的打架
SIG_PREFIX = "META-INF/"
SIG_SUFFIX = (".SF", ".RSA", ".DSA", ".EC", ".MF")


def find_apksigner():
    """优先用 ANDROID_HOME / ANDROID_SDK_ROOT 下的，找不到再扫常见路径。"""
    exe = "apksigner.bat" if os.name == "nt" else "apksigner"
    roots = []
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        v = os.environ.get(key)
        if v:
            roots.append(v)
    roots.append(os.path.expanduser("~/.workbuddy/toolchains/android/sdk"))
    for root in roots:
        hits = sorted(glob.glob(os.path.join(root, "build-tools", "*", exe)))
        if hits:
            return hits[-1]
    found = shutil.which("apksigner")
    if found:
        return found
    sys.exit("找不到 apksigner。请设置 ANDROID_HOME，或确认 Android SDK build-tools 已安装。")


def load_keystore():
    prop = os.path.join(ROOT, "android", "keystore.properties")
    if not os.path.exists(prop):
        sys.exit("缺少 android/keystore.properties，读不到签名密钥。")
    vals = {}
    with io.open(prop, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    need = ("storeFile", "storePassword", "keyAlias", "keyPassword")
    miss = [k for k in need if not vals.get(k)]
    if miss:
        sys.exit("keystore.properties 缺字段：%s" % ", ".join(miss))
    ks = vals["storeFile"]
    if not os.path.isabs(ks):
        ks = os.path.join(ROOT, "android", ks)
    if not os.path.exists(ks):
        sys.exit("找不到密钥文件：%s" % ks)
    vals["storeFile"] = ks
    return vals


def strip_signature(src, dst):
    """把 src 另存一份到 dst，去掉旧签名条目，其余字节原样保留。"""
    dropped = 0
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if item.filename.startswith(SIG_PREFIX) and item.filename.upper().endswith(SIG_SUFFIX):
                dropped += 1
                continue
            zout.writestr(item, zin.read(item.filename))
    return dropped


def cert_fingerprint(apksigner, apk):
    r = subprocess.run([apksigner, "verify", "--print-certs", apk],
                       capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"SHA-256 digest:\s*([0-9a-fA-F]{64})", out)
    return (m.group(1).lower() if m else None), out


def app_fingerprint(apksigner):
    """拿已发布 apk 的指纹当参照，确认签出来的是同一把密钥。"""
    hits = sorted(glob.glob(os.path.join(ROOT, "release", "v*", "*.apk")))
    if not hits:
        return None
    return cert_fingerprint(apksigner, hits[-1])[0]


def main():
    ap = argparse.ArgumentParser(description="用发版密钥给平台的 ADV 空包签名")
    ap.add_argument("apk", help="平台下载的「含签名的 APK 空包」")
    ap.add_argument("-o", "--out", help="输出文件名，默认在原文件名后加 -signed")
    ap.add_argument("--min-sdk", type=int, default=26, help="最低支持的安卓版本，默认 26")
    args = ap.parse_args()

    if not os.path.exists(args.apk):
        sys.exit("找不到输入文件：%s" % args.apk)
    if not zipfile.is_zipfile(args.apk):
        sys.exit("这不是一个 apk（不是 zip 结构）：%s" % args.apk)

    out = args.out
    if not out:
        base, ext = os.path.splitext(args.apk)
        out = base + "-signed" + (ext or ".apk")
    out = os.path.abspath(out)
    if os.path.abspath(args.apk) == out:
        sys.exit("输出不能和输入同名，换一个 -o。")

    apksigner = find_apksigner()
    ks = load_keystore()
    print("apksigner : %s" % apksigner)
    print("keystore  : %s" % ks["storeFile"])
    print("alias     : %s" % ks["keyAlias"])

    tmpdir = tempfile.mkdtemp(prefix="adv_")
    clean = os.path.join(tmpdir, "clean.apk")
    try:
        dropped = strip_signature(args.apk, clean)
        print("旧签名条目：剔除 %d 个" % dropped)

        cmd = [apksigner, "sign",
               "--ks", ks["storeFile"],
               "--ks-key-alias", ks["keyAlias"],
               "--ks-pass", "pass:" + ks["storePassword"],
               "--key-pass", "pass:" + ks["keyPassword"],
               "--min-sdk-version", str(args.min_sdk),
               "--v1-signing-enabled", "true",
               "--v2-signing-enabled", "true",
               "--v3-signing-enabled", "true",
               "--out", out, clean]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("签名失败：\n%s\n%s" % (r.stdout or "", r.stderr or ""))

        got, raw = cert_fingerprint(apksigner, out)
        if not got:
            sys.exit("签名后验不出来，输出：\n%s" % raw)
        print("签名校验  : 通过")
        print("SHA-256   : %s" % got)

        expect = app_fingerprint(apksigner)
        if expect:
            print("发版 apk  : %s" % expect)
            if got != expect:
                sys.exit("指纹和正式发版的 apk 不一致，不能用这个文件去验证。")
            print("结论      : 与正式发版同一把密钥，可以上传")
        else:
            print("提示      : release/ 下没有 apk 可比对，请人工确认指纹")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print("")
    print("输出文件  : %s" % out)
    print("下一步    : 回到平台上传这个文件，然后关联包名 %s 并提交。" % PKG)


if __name__ == "__main__":
    main()
