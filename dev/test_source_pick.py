"""更新源默认选择的回归自检。

这一项是补一个真实踩过的坑：默认更新源曾经把「界面语言」当成「用户在哪个国家」，
界面切成英文就跑去 GitHub——可用户只是换了个界面语言，人还在国内。启动时还出现过
「一进来判成 GitHub、关掉窗口又变回 Gitee」的抖动，因为判断依赖了进程默认 Locale。

现在规则只有一条：默认 Gitee，只有「系统语言明确不是中文 + 时区也不在东八区」才用 GitHub，
任何一项问不出来都按 Gitee 兜底；界面语言完全不参与。

跑法：python dev/test_source_pick.py
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfmask_update as U  # noqa: E402


class SourcePickTest(unittest.TestCase):
    def pick(self, lang_state, offset, ui_lang=None):
        with mock.patch.object(U, "system_lang_state", return_value=lang_state), \
             mock.patch.object(U, "utc_offset_hours", return_value=offset):
            return U.resolve_source("auto", ui_lang)

    def test_chinese_system_uses_gitee(self):
        self.assertEqual(self.pick("zh", 8.0), "gitee")
        self.assertEqual(self.pick("zh", -5.0), "gitee", "中文系统在哪个时区都先走 Gitee")

    def test_foreign_language_but_utc8_still_gitee(self):
        self.assertEqual(self.pick("other", 8.0), "gitee")

    def test_foreign_language_and_foreign_timezone_uses_github(self):
        self.assertEqual(self.pick("other", -5.0), "github")
        self.assertEqual(self.pick("other", 9.0), "github")

    def test_unknown_environment_falls_back_to_gitee(self):
        self.assertEqual(self.pick(None, None), "gitee")
        self.assertEqual(self.pick(None, 8.0), "gitee")
        self.assertEqual(self.pick("other", None), "gitee", "时区问不出来也按 Gitee 兜底")

    def test_ui_language_never_changes_the_source(self):
        for lang in (None, "en", "en-US", "zh", ""):
            self.assertEqual(self.pick("zh", 8.0, lang), "gitee", "界面语言=%r 不该把中文用户赶到 GitHub" % lang)

    def test_explicit_choice_wins(self):
        with mock.patch.object(U, "system_lang_state", return_value="other"), \
             mock.patch.object(U, "utc_offset_hours", return_value=-5.0):
            self.assertEqual(U.resolve_source("gitee"), "gitee")
            self.assertEqual(U.resolve_source("github"), "github")
            self.assertEqual(U.resolve_source("GITHUB"), "github")


if __name__ == "__main__":
    unittest.main(verbosity=2)
