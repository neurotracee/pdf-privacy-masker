# -*- coding: utf-8 -*-
"""跨版本更新说明（更新弹窗里逐页翻看未更新版本）的回归测试。

场景：用户停在 1.4.6.2，仓库里已经有 1.4.6.3、1.4.6.4。更新弹窗除了默认
展示最新版说明，还要能翻到 1.4.6.3 的说明；但**下载与安装的目标必须始终是
1.4.6.4**——翻到哪一页都不改变这一点。

这里锁住的是数据层：
- pending 只包含「比当前新」且「本平台确实有安装包」的版本；
- pending 按版本升序（旧 → 新），最后一页就是最新版；
- 顶层 latest / url 与翻页无关，永远是最大版本。

界面层的翻页顺序与「下载目标恒为最新」由 test_platform_split 之外的
两端单测分别守着（Windows 在 ui 逻辑里、安卓在 UpdaterTest）。

跑法：python dev/test_pending_notes.py
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfmask_update as U  # noqa: E402

PAGE = "https://github.com/neurotracee/pdf-privacy-masker/releases"
CHAN = [{"api": "https://example.invalid/releases", "label": "Gitee", "page": PAGE}]


def rel(tag, names, body=""):
    return {
        "tag_name": tag,
        "html_url": "%s/tag/%s" % (PAGE, tag),
        "body": body,
        "draft": False,
        "assets": [
            {"name": n, "browser_download_url": "%s/download/%s/%s" % (PAGE, tag, n)}
            for n in names
        ],
    }


def both(ver, body=""):
    return rel("v" + ver, [
        "PDFPrivacyMasker-%s.exe" % ver,
        "PDFPrivacyMasker-%s-arm64.apk" % ver,
    ], body)


def check(data, current, suffix=".apk"):
    with mock.patch.object(U, "_fetch", return_value=data):
        return U.check_update(current, suffix, lambda zh, en: zh, order=CHAN)


class PendingNotesTest(unittest.TestCase):
    def test_lists_every_version_between_current_and_latest(self):
        """1.4.6.2 → 仓库有 1.4.6.3 / 1.4.6.4：两页都要有，升序。"""
        data = [both("1.4.6.4", "四"), both("1.4.6.3", "三"), both("1.4.6.2", "二")]
        r = check(data, "1.4.6.2")
        self.assertTrue(r["ok"])
        self.assertEqual(r["latest"], "1.4.6.4")
        self.assertEqual([p["ver"] for p in r["pending"]], ["1.4.6.3", "1.4.6.4"])
        self.assertEqual(r["pendingCount"], 2)

    def test_download_target_is_always_latest(self):
        """翻页不改变下载目标：顶层 url 指向最大版本，与 pending 顺序无关。"""
        data = [both("1.4.6.4"), both("1.4.6.3"), both("1.4.6.5")]
        r = check(data, "1.4.6.2")
        self.assertEqual(r["latest"], "1.4.6.5")
        self.assertIn("1.4.6.5-arm64.apk", r["url"])
        self.assertNotIn("1.4.6.3", r["url"])
        self.assertEqual([p["ver"] for p in r["pending"]],
                         ["1.4.6.3", "1.4.6.4", "1.4.6.5"])

    def test_current_version_not_in_pending(self):
        """等于当前版本的不算「未更新」。"""
        data = [both("1.4.6.4"), both("1.4.6.3")]
        r = check(data, "1.4.6.3")
        self.assertEqual([p["ver"] for p in r["pending"]], ["1.4.6.4"])

    def test_other_platform_only_version_is_skipped(self):
        """只给 Windows 发过包的版本，不应出现在安卓的翻页列表里。"""
        data = [
            rel("v1.4.6.4", ["PDFPrivacyMasker-1.4.6.4.exe"]),
            both("1.4.6.3"),
        ]
        r = check(data, "1.4.6.2", ".apk")
        self.assertTrue(r["ok"])
        self.assertEqual([p["ver"] for p in r["pending"]], ["1.4.6.3"])

    def test_release_without_assets_is_not_a_pending_page(self):
        """远古 Release 只有一个空壳（没有安装包）：不能翻出空白页。"""
        data = [
            both("1.4.6.4"),
            rel("v1.4.5", [], "老版本，没传安装包"),
        ]
        r = check(data, "1.4.6.2")
        self.assertEqual([p["ver"] for p in r["pending"]], ["1.4.6.4"])

    def test_has_update_false_means_no_pages(self):
        """已经是最新版：pending 为空，界面不该出现翻页。"""
        data = [both("1.4.6.4")]
        r = check(data, "1.4.6.4")
        self.assertFalse(r["hasUpdate"])
        self.assertEqual(r["pending"], [])

    def test_each_page_carries_its_own_digest(self):
        """每页显示的是这一版自己的说明，不能都拿最新版的正文顶上。"""
        data = [
            both("1.4.6.4", "一句话：第四版\n\n## 修复\n- 四的改动"),
            both("1.4.6.3", "一句话：第三版\n\n## 修复\n- 三的改动"),
        ]
        r = check(data, "1.4.6.2")
        pages = {p["ver"]: p["digest"] for p in r["pending"]}
        self.assertIn("四的改动", str(pages["1.4.6.4"]))
        self.assertIn("三的改动", str(pages["1.4.6.3"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
