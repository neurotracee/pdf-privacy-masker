package com.neurotracee.pdfmask

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.neurotracee.pdfmask.core.DraftStore
import com.neurotracee.pdfmask.core.Finding
import com.neurotracee.pdfmask.core.Kind
import com.neurotracee.pdfmask.core.Rect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * 临时保存（草稿）的存取。
 *
 * 这块一旦写错，用户丢的是「刚刚手动框了二十个框」的劳动成果，而且丢得
 * 悄无声息——所以字段逐个验一遍：框的坐标、勾选状态、擦除笔画、停在第几页。
 */
@RunWith(RobolectricTestRunner::class)
class DraftStoreTest {

    private lateinit var ctx: Context

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()
        DraftStore.clear(ctx)
    }

    /** 造一个假源文件，内容无所谓，只要长度 > 0 */
    private fun fakeSource(): File {
        val f = File(ctx.cacheDir, "src_test.pdf")
        f.writeBytes(ByteArray(1024) { it.toByte() })
        return f
    }

    private fun sampleFindings() = listOf(
        Finding(page = 0, type = Kind.PHONE, text = "13812346780",
            rect = Rect(10f, 20f, 120f, 34f), note = "", id = 7),
        Finding(page = 1, type = Kind.MANUAL, text = "",
            rect = Rect(50f, 60f, 150f, 90f), note = "手动", id = -1),
    )

    @Test
    fun save_then_meta_reports_counts() {
        val ok = DraftStore.save(
            ctx, fakeSource(), "测试.pdf", pagesCount = 3,
            findings = sampleFindings(), selected = setOf(7, -1),
            erasers = mapOf(0 to listOf(Rect(1f, 2f, 3f, 4f))), current = 1
        )
        assertTrue("保存应当成功", ok)

        val m = DraftStore.meta(ctx)
        assertNotNull(m)
        assertEquals("测试.pdf", m!!.name)
        assertEquals(3, m.pages)
        assertEquals(2, m.marks)
        assertEquals(1, m.current)
        assertTrue(m.savedAt > 0)
    }

    @Test
    fun load_round_trips_every_field() {
        val findings = sampleFindings()
        val erasers = mapOf(0 to listOf(Rect(1f, 2f, 3f, 4f), Rect(5f, 6f, 7f, 8f)), 2 to listOf(Rect(9f, 9f, 10f, 10f)))
        DraftStore.save(ctx, fakeSource(), "round.pdf", 3, findings, setOf(7, -1), erasers, 2)

        val s = DraftStore.load(ctx)
        assertNotNull(s)
        assertEquals("round.pdf", s!!.name)
        assertEquals(2, s.current)
        assertEquals(2, s.findings.size)

        val phone = s.findings.first { it.type == Kind.PHONE }
        assertEquals(7, phone.id)
        assertEquals(0, phone.page)
        assertEquals("13812346780", phone.text)
        assertEquals(10f, phone.rect.x0, 0.001f)
        assertEquals(120f, phone.rect.x1, 0.001f)

        val manual = s.findings.first { it.type == Kind.MANUAL }
        assertEquals(-1, manual.id)

        assertEquals(setOf(7, -1), s.selected)
        assertEquals(2, s.erasers[0]?.size)
        assertEquals(1, s.erasers[2]?.size)
        assertEquals(9f, s.erasers[2]!![0].x0, 0.001f)
    }

    @Test
    fun empty_selection_survives_the_round_trip() {
        // 用户可以把勾全取消；恢复时不能「好心」帮他全选上
        DraftStore.save(ctx, fakeSource(), "none.pdf", 1, sampleFindings(), emptySet(), emptyMap(), 0)
        val s = DraftStore.load(ctx)
        assertNotNull(s)
        assertTrue(s!!.selected.isEmpty())
    }

    @Test
    fun clear_removes_draft() {
        DraftStore.save(ctx, fakeSource(), "x.pdf", 1, sampleFindings(), setOf(7), emptyMap(), 0)
        assertTrue(DraftStore.has(ctx))
        DraftStore.clear(ctx)
        assertFalse(DraftStore.has(ctx))
        assertNull(DraftStore.meta(ctx))
        assertNull(DraftStore.load(ctx))
    }

    @Test
    fun unknown_version_is_discarded_not_guessed() {
        DraftStore.save(ctx, fakeSource(), "v.pdf", 1, sampleFindings(), setOf(7), emptyMap(), 0)
        // 模拟「老版本草稿」：把版本号改掉
        val j = DraftStore.jsonFile(ctx)
        j.writeText(j.readText().replace("\"v\":1", "\"v\":99"))
        assertNull("版本不符就该当作没有草稿", DraftStore.load(ctx))
        assertNull(DraftStore.meta(ctx))
    }

    @Test
    fun missing_pdf_means_no_draft() {
        DraftStore.save(ctx, fakeSource(), "gone.pdf", 1, sampleFindings(), setOf(7), emptyMap(), 0)
        DraftStore.pdfFile(ctx).delete()
        assertFalse(DraftStore.has(ctx))
        assertNull(DraftStore.meta(ctx))
        assertNull(DraftStore.load(ctx))
    }

    @Test
    fun save_overwrites_previous_draft() {
        DraftStore.save(ctx, fakeSource(), "first.pdf", 1, sampleFindings(), setOf(7), emptyMap(), 0)
        DraftStore.save(ctx, fakeSource(), "second.pdf", 2, emptyList(), emptySet(), emptyMap(), 1)
        val m = DraftStore.meta(ctx)
        assertEquals("second.pdf", m!!.name)
        assertEquals(0, m.marks)
        assertEquals(1, DraftStore.load(ctx)!!.current)
    }

    @Test
    fun save_reports_false_when_source_is_missing() {
        val ghost = File(ctx.cacheDir, "not_here.pdf")
        val ok = DraftStore.save(ctx, ghost, "ghost.pdf", 1, emptyList(), emptySet(), emptyMap(), 0)
        assertFalse("源文件不存在时必须如实报失败", ok)
    }
}
