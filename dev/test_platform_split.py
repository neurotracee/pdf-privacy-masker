"""两端版本号各自独立 · 单平台发版不误伤另一端的回归自检。

补的是一个真实会咬人的坑：Windows 与安卓共用一个版本号时，只改了安卓也得
把 Windows 重打一遍 73MB 的 exe；反过来更糟——发一个只带 exe 的新版本，
安卓的检查更新会拿 tag 版本兜底，提示「有新版」但下载页里根本没有 apk。

现在的规则：
- 两端版本号各自演进，允许不同（1.4.6 的 Windows 对 1.4.7.2 的安卓）；
- 判断某平台要不要更新，只认**该平台安装包文件名里的版本**；
- 某个 Release 只给另一端发了包 → 对本平台等于「没更新」，不允许拿 tag 兜底；
- 一个安装包都没有的远古 Release（v1.2.0 那种）仍允许 tag 兜底，否则老用户查不到更新。

跑法：python dev/test_platform_split.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfmask_update as U  # noqa: E402

PAGE = "https://github.com/neurotracee/pdf-privacy-masker/releases"


def rel(tag, names, body=""):
    """造一条假的 Release。资产地址用白名单内的域名，避免被换成发布页。"""
    return {
        "tag_name": tag,
        "html_url": PAGE + "/tag/" + tag,
        "body": body,
        "draft": False,
        "assets": [
            {
                "name": n,
                "browser_download_url": "%s/download/%s/%s" % (PAGE, tag, n),
            }
            for n in names
        ],
    }


def ver_of(data, suffix):
    got = U.parse_releases(data, suffix, PAGE)
    return got["ver"] if got else None


class PlatformSplitTest(unittest.TestCase):
    def test_each_platform_reads_its_own_asset(self):
        """一个 Release 里两端都有包：各取各的版本，互不干扰。"""
        data = [rel("v1.4.6.1", [
            "PDFPrivacyMasker-1.4.6.1.exe",
            "PDFPrivacyMasker-1.4.6.1-arm64.apk",
        ])]
        self.assertEqual(ver_of(data, ".exe"), (1, 4, 6, 1))
        self.assertEqual(ver_of(data, ".apk"), (1, 4, 6, 1))

    def test_android_only_release_does_not_touch_windows(self):
        """只发安卓（1.4.7.1）时，Windows 不该被 tag 顶到 1.4.7.1。"""
        data = [
            rel("v1.4.7.1", ["PDFPrivacyMasker-1.4.7.1-arm64.apk"]),
            rel("v1.4.6", ["PDFPrivacyMasker-1.4.6.exe",
                           "PDFPrivacyMasker-1.4.6-arm64.apk"]),
        ]
        self.assertEqual(ver_of(data, ".apk"), (1, 4, 7, 1))
        self.assertEqual(ver_of(data, ".exe"), (1, 4, 6, 0))
        # Windows 当前就是 1.4.6，结论必须是「已是最新」
        self.assertFalse(U.ver_tuple("1.4.6") < ver_of(data, ".exe"))

    def test_windows_only_release_does_not_fake_android_update(self):
        """只发 Windows 的新版：安卓看到的仍是自己那份包，不能提示假更新。"""
        data = [
            rel("v1.5.0", ["PDFPrivacyMasker-1.5.0.exe"]),
            rel("v1.4.6", ["PDFPrivacyMasker-1.4.6.exe",
                           "PDFPrivacyMasker-1.4.6-arm64.apk"]),
        ]
        self.assertEqual(ver_of(data, ".exe"), (1, 5, 0, 0))
        self.assertEqual(ver_of(data, ".apk"), (1, 4, 6, 0))
        self.assertFalse(U.ver_tuple("1.4.6") < ver_of(data, ".apk"))

    def test_two_platforms_can_hold_different_versions(self):
        """两端版本号允许不同：安卓 1.4.7，Windows 还停在 1.4.6。"""
        data = [
            rel("v1.4.7", ["PDFPrivacyMasker-1.4.7-arm64.apk"]),
            rel("v1.4.6", ["PDFPrivacyMasker-1.4.6.exe"]),
        ]
        self.assertEqual(ver_of(data, ".apk"), (1, 4, 7, 0))
        self.assertEqual(ver_of(data, ".exe"), (1, 4, 6, 0))

    def test_old_release_without_assets_still_uses_tag(self):
        """最早那些没有安装包的 Release，继续靠 tag 兜底，别让老用户查不到更新。"""
        data = [rel("v1.2.0", [])]
        self.assertEqual(ver_of(data, ".apk"), (1, 2, 0, 0))
        self.assertEqual(ver_of(data, ".exe"), (1, 2, 0, 0))

    def test_asset_version_beats_tag_when_both_exist(self):
        """资产名里的版本更准：tag 写成 v1.4.7 但包里是 1.4.6.2，按包算。"""
        data = [rel("v1.4.7", ["PDFPrivacyMasker-1.4.6.2.exe"])]
        self.assertEqual(ver_of(data, ".exe"), (1, 4, 6, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
