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
    fun release_with_only_exe_is_not_an_android_update() {
        // 这一版只给 Windows 发了包（两端版本号各自独立，允许不同步）。
        // 安卓看到的应是「没有更新」，而不是拿 tag 版本提示一条下载不到 apk 的假更新。
        val json = """
        [{"tag_name":"v9.9.9","html_url":"https://github.com/x/9",
          "assets":[{"name":"PDFPrivacyMasker-9.9.9.exe","browser_download_url":"https://github.com/x/e.exe"}]}]
        """.trimIndent()
        val r = parseReleasesForTest(json, "1.4.0")
        assertFalse(r.hasUpdate)
        // 连版本号都不该显示：界面弹「发现 9.9.9」但点下载没东西，比不提示更糟
        assertEquals("", r.latest)
    }

    @Test
    fun legacy_release_without_assets_still_uses_tag() {
        // 最早的几个版本没挂附件，tag 兜底要留着，否则老用户永远查不到更新
        val json = """[{"tag_name":"v1.5.0","html_url":"https://github.com/x/15","assets":[]}]"""
        val r = parseReleasesForTest(json, "1.4.0")
        assertTrue(r.ok)
        assertTrue(r.hasUpdate)
        assertEquals("1.5.0.0", r.latest)
        assertEquals("https://github.com/x/15", r.url)
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

    // ------------------------------------------------ 跨版本说明（v1.4.6.5）

    /** 造一条 Release（只给安卓的 apk） */
    private fun apkRel(ver: String, body: String = ""): String =
        """{"tag_name":"v$ver","html_url":"https://github.com/x/$ver","body":"$body",
           "assets":[{"name":"PDFPrivacyMasker-$ver-arm64.apk",
                      "browser_download_url":"https://github.com/x/PDFPrivacyMasker-$ver-arm64.apk"}]}"""

    @Test
    fun download_urls_put_gitee_first() {
        // 哪怕更新信息是从 GitHub 查到的，下载也先试 Gitee：
        // 国内 GitHub 的资产 CDN 基本下不动，「查得到、下不了」就是这么来的
        val urls = Updater.downloadUrls(
            "https://github.com/neurotracee/pdf-privacy-masker/releases/download/v1.4.9.0/" +
                "PDFPrivacyMasker-1.4.9.0-arm64.apk",
            "v1.4.9.0",
            "PDFPrivacyMasker-1.4.9.0-arm64.apk"
        )
        assertEquals(2, urls.size)
        assertTrue(urls[0], urls[0].startsWith("https://gitee.com/"))
        assertTrue(urls[0], urls[0].endsWith("/v1.4.9.0/PDFPrivacyMasker-1.4.9.0-arm64.apk"))
        assertTrue(urls[1], urls[1].contains("github.com"))
    }

    @Test
    fun download_urls_skip_release_page() {
        // 只拿到发布页（没有具体资产）时，不能把发布页当成下载地址
        val urls = Updater.downloadUrls(
            Updater.RELEASES_PAGE, "v1.4.9.0", "PDFPrivacyMasker-1.4.9.0-arm64.apk"
        )
        assertEquals(1, urls.size)
        assertTrue(urls[0].startsWith("https://gitee.com/"))
    }

    @Test
    fun parse_keeps_tag_and_asset_for_download() {
        val r = parseReleasesForTest("[" + apkRel("1.4.6.4") + "]", "1.4.6.3")
        assertEquals("v1.4.6.4", r.tag)
        assertTrue(r.asset, r.asset.endsWith(".apk"))
    }

    @Test
    fun pending_lists_every_version_behind_oldest_first() {
        // 当前 1.4.6.2，仓库有 1.4.6.3 / 1.4.6.4：两页都要有，且是「旧 → 新」升序。
        // 故意把 1.4.6.4 放在前面，确认不是照 JSON 顺序堆出来的。
        val json = "[" + apkRel("1.4.6.4") + "," + apkRel("1.4.6.3") + "]"
        val r = parseReleasesForTest(json, "1.4.6.2")
        assertEquals("1.4.6.4", r.latest)
        assertEquals(listOf("1.4.6.3", "1.4.6.4"), r.pending.map { it.ver })
    }

    @Test
    fun pending_last_page_is_always_the_download_target() {
        // 翻到哪一页都不改变下载目标：url 只能是最大版本，最后一页的版本号必须等于 latest
        val json = "[" + apkRel("1.4.6.3") + "," + apkRel("1.4.6.4") + "," + apkRel("1.4.6.5") + "]"
        val r = parseReleasesForTest(json, "1.4.6.2")
        assertEquals("1.4.6.5", r.latest)
        assertEquals("1.4.6.5", r.pending.last().ver)
        assertTrue(r.url.contains("1.4.6.5"))
        assertFalse(r.url.contains("1.4.6.3"))
        assertFalse(r.url.contains("1.4.6.4"))
    }

    @Test
    fun pending_skips_versions_built_only_for_the_other_platform() {
        // 只发了 exe 的版本，安卓不该翻出一页「下载不到 apk」的说明
        val exeOnly = """{"tag_name":"v1.4.6.4","html_url":"https://github.com/x/4",
            "assets":[{"name":"PDFPrivacyMasker-1.4.6.4.exe",
                       "browser_download_url":"https://github.com/x/PDFPrivacyMasker-1.4.6.4.exe"}]}"""
        val json = "[" + exeOnly + "," + apkRel("1.4.6.3") + "]"
        val r = parseReleasesForTest(json, "1.4.6.2")
        assertEquals(listOf("1.4.6.3"), r.pending.map { it.ver })
    }

    @Test
    fun pending_excludes_current_version() {
        val json = "[" + apkRel("1.4.6.3") + "," + apkRel("1.4.6.4") + "]"
        val r = parseReleasesForTest(json, "1.4.6.3")
        assertEquals(listOf("1.4.6.4"), r.pending.map { it.ver })
    }

    @Test
    fun pending_is_empty_when_already_latest() {
        val json = "[" + apkRel("1.4.6.4") + "]"
        val r = parseReleasesForTest(json, "1.4.6.4")
        assertFalse(r.hasUpdate)
        assertTrue(r.pending.isEmpty())
    }

    @Test
    fun each_pending_page_keeps_its_own_notes() {        // 每页显示的是这一版自己的正文，不能都拿最新版顶替
        // 摘要要求 ≥8 字才收（ReleaseDigest 的既有口径），这里写足长度
        val z3 = "更新级别：建议\\n\\n> **一句话**：第三版修掉了扫描件长句整行漏检的问题\\n"
        val z4 = "更新级别：建议\\n\\n> **一句话**：第四版修掉了住址被折行切开时漏打的问题\\n"
        val json = "[" + apkRel("1.4.6.4", z4) + "," + apkRel("1.4.6.3", z3) + "]"
        val r = parseReleasesForTest(json, "1.4.6.2")
        val texts = r.pending.map { it.digest?.pick(false)?.brief ?: "" }
        assertTrue("第 1 页应是 1.4.6.3 的说明：" + texts[0], texts[0].contains("第三版"))
        assertTrue("第 2 页应是 1.4.6.4 的说明：" + texts[1], texts[1].contains("第四版"))
    }
}
