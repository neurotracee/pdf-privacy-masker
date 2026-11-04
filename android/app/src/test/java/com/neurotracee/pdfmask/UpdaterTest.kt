package com.neurotracee.pdfmask

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * 检查更新的解析逻辑：版本号抠取、比较、按平台挑安装包。
 * 只测纯函数，不发网络请求。
 */
@RunWith(RobolectricTestRunner::class)
class UpdaterTest {

    @Test
    fun ver_parses_common_forms() {
        assertEquals(3, Updater.ver("1.4.0")!!.size)
        assertEquals(listOf(1, 4, 0), Updater.ver("v1.4.0")!!.toList())
        assertEquals(listOf(1, 4, 0), Updater.ver("PDFPrivacyMasker-1.4.0-arm64.apk")!!.toList())
        assertEquals(listOf(1, 5, 2), Updater.ver("PDFPrivacyMasker-1.5.2.exe")!!.toList())
        assertEquals(listOf(2, 0, 0), Updater.ver("2.0")!!.toList())
        assertEquals(null, Updater.ver("no-version-here"))
    }

    @Test
    fun cmp_orders_versions() {
        assertTrue(Updater.cmp(Updater.ver("1.5.0")!!, Updater.ver("1.4.9")!!) > 0)
        assertTrue(Updater.cmp(Updater.ver("1.4.0")!!, Updater.ver("1.4.0")!!) == 0)
        assertTrue(Updater.cmp(Updater.ver("1.4.0")!!, Updater.ver("1.10.0")!!) < 0)
    }

    @Test
    fun picks_newest_apk_and_flags_update() {
        val json = """
        [
          {"tag_name":"v1.3.0","draft":false,"html_url":"https://x/1.3.0",
           "assets":[{"name":"PDFPrivacyMasker-1.3.0-arm64.apk","browser_download_url":"https://x/a13.apk"}]},
          {"tag_name":"v1.5.0","draft":false,"html_url":"https://x/1.5.0",
           "assets":[{"name":"PDFPrivacyMasker-1.5.0-arm64.apk","browser_download_url":"https://x/a15.apk"},
                     {"name":"PDFPrivacyMasker-1.5.0.exe","browser_download_url":"https://x/e15.exe"}]}
        ]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertEquals("1.5.0", r.latest)
        assertTrue(r.hasUpdate)
        assertEquals("https://x/a15.apk", r.url)
    }

    @Test
    fun no_newer_apk_means_up_to_date() {
        val json = """
        [{"tag_name":"v1.4.0","html_url":"https://x/1.4.0",
          "assets":[{"name":"PDFPrivacyMasker-1.4.0-arm64.apk","browser_download_url":"https://x/a14.apk"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertFalse(r.hasUpdate)
    }

    @Test
    fun ignores_exe_when_looking_for_android_build() {
        val json = """
        [{"tag_name":"v9.9.9","html_url":"https://x/9",
          "assets":[{"name":"PDFPrivacyMasker-9.9.9.exe","browser_download_url":"https://x/e.exe"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertFalse(r.ok)
    }

    @Test
    fun strong_marker_only_matches_the_real_marker() {
        // 认：行首的「更新级别：强烈建议」，以及早期版本用过的旧注释（现在只降级成「强烈建议」，不再锁人）
        assertTrue(Updater.isStrongUpdate("更新级别：强烈建议"))
        assertTrue(Updater.isStrongUpdate("更新级别: 强烈建议\n修复了几个问题"))
        assertTrue(Updater.isStrongUpdate("  更新级别：强烈建议"))
        assertTrue(Updater.isStrongUpdate("正文\n<!-- update:force -->\n"))

        // 不认：普通建议、空正文、写在表格或句子里的标记
        assertFalse(Updater.isStrongUpdate("更新级别：建议"))
        assertFalse(Updater.isStrongUpdate(""))
        assertFalse(Updater.isStrongUpdate(null))
        assertFalse(Updater.isStrongUpdate("本次更新强烈建议你先备份，更新级别：建议"))
        // 说明文档里会把标记当例子写出来，不能因此把所有人判成强烈建议
        assertFalse(Updater.isStrongUpdate("| `更新级别：强烈建议` | 关之前劝一次 |"))
        assertFalse(Updater.isStrongUpdate("还认 `<!-- update:force -->` 这种写法"))
    }

    @Test
    fun strong_flag_follows_the_newest_release() {
        val json = """
        [
          {"tag_name":"v1.4.1","draft":false,"html_url":"https://x/1.4.1","body":"更新级别：建议",
           "assets":[{"name":"PDFPrivacyMasker-1.4.1-arm64.apk","browser_download_url":"https://x/a141.apk"}]},
          {"tag_name":"v1.4.2","draft":false,"html_url":"https://x/1.4.2","body":"更新级别：强烈建议",
           "assets":[{"name":"PDFPrivacyMasker-1.4.2-arm64.apk","browser_download_url":"https://x/a142.apk"}]}
        ]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.1")
        assertEquals("1.4.2", r.latest)
        assertTrue(r.hasUpdate)
        assertTrue(r.strong)
    }

    @Test
    fun plain_suggestion_is_not_strong() {
        val json = """
        [{"tag_name":"v1.4.2","html_url":"https://x/1.4.2","body":"更新级别：建议",
          "assets":[{"name":"PDFPrivacyMasker-1.4.2-arm64.apk","browser_download_url":"https://x/a142.apk"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.1")
        assertTrue(r.hasUpdate)
        assertFalse(r.strong)
    }
}
