package com.neurotracee.pdfmask

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 发布正文 → 更新弹窗文案：一句话摘要要在 100 字内，条目要按平台归类，
 * 正文里不能残留 Markdown 记号。
 */
class ReleaseDigestTest {

    private val body = """
        # v1.4.4 版本说明（Windows + 安卓）

        **中文** | [English](#v144-release-notes)

        更新级别：建议

        > **一句话**：注释和书签里只出现的姓名地址不再漏打；安卓注释文字改成整块马赛克。

        这一版补掉上一版留下的三处同类残口。

        ---

        ## 1. 修复：注释和书签里独自出现的姓名、地址会漏（Windows）

        正文里没出现过的姓名、地址，现在也会被认出来。

        ```
        书签: 附件：赵** 体检报告
        ```

        ## 2. 修复：安卓端注释里的文字会变成像素（安卓）

        整块盖马赛克，宁可多盖也不漏。`0512****1234` 也遮住了。

        ## 3. 下载

        - Windows：PDFPrivacyMasker-1.4.4.exe

        # v1.4.4 Release Notes (Windows + Android)

        [中文](#v144) | **English**

        Update level: suggested

        > **In one line**: annotation/bookmark leaks fixed; Android comment text now mosaicked.

        ## 1. Fixed: annotation and bookmark leaks (Windows)

        Names that never appeared in the body are recognised now.

        ## 2. Fixed: Android comment text became pixels (Android)

        The annotation box is mosaicked whole.
    """.trimIndent()

    @Test
    fun brief_is_short_and_clean() {
        val d = ReleaseDigest.of(body)
        val zh = d.zh!!.brief
        assertTrue(zh.isNotEmpty())
        assertTrue("中文摘要 $zh", zh.length <= ReleaseDigest.MAX_BRIEF_ZH)
        assertTrue(zh.startsWith("注释和书签里只出现的姓名地址"))
        assertFalse(zh.contains("**"))
        assertFalse(zh.startsWith("更新级别"))

        val en = d.en!!.brief
        assertTrue(en.isNotEmpty())
        assertTrue(en.length <= ReleaseDigest.MAX_BRIEF_EN)
        assertTrue(en.startsWith("annotation/bookmark"))
    }

    @Test
    fun items_carry_platform_tags() {
        val d = ReleaseDigest.of(body)
        val items = d.zh!!.items
        assertEquals(2, items.size)
        assertEquals("win", items[0].platform)
        assertEquals("android", items[1].platform)
        assertTrue(items[0].title.startsWith("修复："))
        // 平台标注已经从标题里剥掉，界面用标签单独显示
        assertFalse(items[0].title.contains("Windows"))
        // 下载章节不该占弹窗的地方
        assertTrue(items.none { it.title.contains("下载") })
        // 打码示例里的星号必须原样保留
        assertTrue(items[1].lines.joinToString("\n").contains("0512****1234"))
        assertTrue(d.en!!.items.size == 2)
    }

    @Test
    fun empty_body_gives_nothing() {
        val d = ReleaseDigest.of("")
        assertTrue(d.zh!!.brief.isEmpty())
        assertTrue(d.zh!!.items.isEmpty())
        assertEquals(null, d.en)
        assertEquals(null, d.pick(en = true))
    }

    @Test
    fun falls_back_to_first_paragraph() {
        val d = ReleaseDigest.of("# v9.9.9\n\n这次就是修了几个小问题。\n\n## 修复\n\n- 某个按钮点不动。")
        assertEquals("这次就是修了几个小问题。", d.zh!!.brief)
        assertEquals("both", d.zh!!.items.single().platform)
    }
}
