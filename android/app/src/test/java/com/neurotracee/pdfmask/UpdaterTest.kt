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
        // 版本号统一四段：主.次.修订.小版本。三段写法补 0，与四段同版
        assertEquals(4, Updater.ver("1.4.0")!!.size)
        assertEquals(listOf(1, 4, 0, 0), Updater.ver("v1.4.0")!!.toList())
        assertEquals(listOf(1, 4, 0, 0), Updater.ver("PDFPrivacyMasker-1.4.0-arm64.apk")!!.toList())
        assertEquals(listOf(1, 5, 2, 0), Updater.ver("PDFPrivacyMasker-1.5.2.exe")!!.toList())
        assertEquals(listOf(2, 0, 0, 0), Updater.ver("2.0")!!.toList())
        // 四段版本号本身
        assertEquals(listOf(1, 4, 6, 1), Updater.ver("v1.4.6.1")!!.toList())
        assertEquals(listOf(1, 4, 6, 2), Updater.ver("PDFPrivacyMasker-1.4.6.2-arm64.apk")!!.toList())
        assertEquals(null, Updater.ver("no-version-here"))
    }

    @Test
    fun cmp_orders_versions() {
        assertTrue(Updater.cmp(Updater.ver("1.5.0")!!, Updater.ver("1.4.9")!!) > 0)
        assertTrue(Updater.cmp(Updater.ver("1.4.0")!!, Updater.ver("1.4.0")!!) == 0)
        assertTrue(Updater.cmp(Updater.ver("1.4.0")!!, Updater.ver("1.10.0")!!) < 0)
        // 1.4.6 与 1.4.6.0 是同一版，不算更新
        assertTrue(Updater.cmp(Updater.ver("1.4.6")!!, Updater.ver("1.4.6.0")!!) == 0)
        // 小版本段能拉开新旧：日常发版就动这一位，这是四段版本号存在的意义
        assertTrue(Updater.cmp(Updater.ver("1.4.6.2")!!, Updater.ver("1.4.6.1")!!) > 0)
        assertTrue(Updater.cmp(Updater.ver("1.4.6.1")!!, Updater.ver("1.4.6")!!) > 0)
        // 大版本（第三位）永远压过小版本（第四位）：1.4.7.0 > 1.4.6.9
        assertTrue(Updater.cmp(Updater.ver("1.4.7.0")!!, Updater.ver("1.4.6.9")!!) > 0)
    }

    @Test
    fun picks_newest_apk_and_flags_update() {
        val json = """
        [
          {"tag_name":"v1.3.0","draft":false,"html_url":"https://github.com/x/1.3.0",
           "assets":[{"name":"PDFPrivacyMasker-1.3.0-arm64.apk","browser_download_url":"https://github.com/x/a13.apk"}]},
          {"tag_name":"v1.5.0","draft":false,"html_url":"https://github.com/x/1.5.0",
           "assets":[{"name":"PDFPrivacyMasker-1.5.0-arm64.apk","browser_download_url":"https://github.com/x/a15.apk"},
                     {"name":"PDFPrivacyMasker-1.5.0.exe","browser_download_url":"https://github.com/x/e15.exe"}]}
        ]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertEquals("1.5.0.0", r.latest)
        assertTrue(r.hasUpdate)
        assertEquals("https://github.com/x/a15.apk", r.url)
    }

    @Test
    fun no_newer_apk_means_up_to_date() {
        val json = """
        [{"tag_name":"v1.4.0","html_url":"https://github.com/x/1.4.0",
          "assets":[{"name":"PDFPrivacyMasker-1.4.0-arm64.apk","browser_download_url":"https://github.com/x/a14.apk"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertFalse(r.hasUpdate)
    }

    @Test
    fun release_with_only_exe_falls_back_to_release_page() {
        // 只有 exe 的版本在安卓上装不了：不认它的下载地址，
        // 但 tag 兜底仍会告诉用户「有新版本」，链接给的是发布页而不是 .exe
        val json = """
        [{"tag_name":"v9.9.9","html_url":"https://github.com/x/9",
          "assets":[{"name":"PDFPrivacyMasker-9.9.9.exe","browser_download_url":"https://github.com/x/e.exe"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertEquals("9.9.9.0", r.latest)
        // 链接是「这个版本的发布页」，而不是安卓装不了的 .exe
        assertEquals("https://github.com/x/9", r.url)
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
          {"tag_name":"v1.4.1","draft":false,"html_url":"https://github.com/x/1.4.1","body":"更新级别：建议",
           "assets":[{"name":"PDFPrivacyMasker-1.4.1-arm64.apk","browser_download_url":"https://github.com/x/a141.apk"}]},
          {"tag_name":"v1.4.2","draft":false,"html_url":"https://github.com/x/1.4.2","body":"更新级别：强烈建议",
           "assets":[{"name":"PDFPrivacyMasker-1.4.2-arm64.apk","browser_download_url":"https://github.com/x/a142.apk"}]}
        ]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.1")
        assertEquals("1.4.2.0", r.latest)
        assertTrue(r.hasUpdate)
        assertTrue(r.strong)
    }

    @Test
    fun download_url_outside_whitelist_falls_back_to_release_page() {
        // 镜像站 / 被接管的 API 可能返回任意下载地址，白名单外的只给发布页
        val json = """
        [{"tag_name":"v1.9.0","html_url":"https://evil.example.com/1.9.0",
          "assets":[{"name":"PDFPrivacyMasker-1.9.0-arm64.apk",
                     "browser_download_url":"https://evil.example.com/a.apk"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertEquals("1.9.0.0", r.latest)
        assertEquals(Updater.RELEASES_PAGE, r.url)
    }

    @Test
    fun whitelist_accepts_release_hosts_only() {
        assertTrue(Updater.allowedDownload("https://github.com/a/b/releases/download/v1/x.apk"))
        assertTrue(Updater.allowedDownload("https://objects.githubusercontent.com/x.apk"))
        assertTrue(Updater.allowedDownload("https://gitee.com/bio234/pdf-privacy-masker/releases/download/v1/x.apk"))
        assertFalse(Updater.allowedDownload("http://github.com/x.apk"))          // 必须 https
        assertFalse(Updater.allowedDownload("https://evil-github.com/x.apk"))     // 后缀伪装
        assertFalse(Updater.allowedDownload("https://github.com.evil.com/x.apk")) // 前缀伪装
        assertFalse(Updater.allowedDownload(""))
    }

    @Test
    fun channel_order_is_gitee_first_for_chinese() {
        assertEquals("gitee", Updater.order(true).first().name)
        assertEquals("github", Updater.order(false).first().name)
    }

    @Test
    fun explicit_source_wins_over_environment() {
        // 用户自己选了源，就不该再按语言猜
        assertTrue(Updater.resolve("gitee"))
        assertFalse(Updater.resolve("github"))
        assertTrue(Updater.resolve("GITEE"))
        // 空值 / 未知值 → 走环境判断（不抛异常即可）
        Updater.resolve("")
        Updater.resolve(null)
        Updater.resolve("nonsense")
    }

    @Test
    fun plain_suggestion_is_not_strong() {
        val json = """
        [{"tag_name":"v1.4.2","html_url":"https://github.com/x/1.4.2","body":"更新级别：建议",
          "assets":[{"name":"PDFPrivacyMasker-1.4.2-arm64.apk","browser_download_url":"https://github.com/x/a142.apk"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.1")
        assertTrue(r.hasUpdate)
        assertFalse(r.strong)
    }
}
