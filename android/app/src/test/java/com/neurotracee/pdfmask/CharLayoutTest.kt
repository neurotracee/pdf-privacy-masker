package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.CharLayout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 字框几何的回归测试（纯 JVM）。
 *
 * 这三条对应用户实测看到的三种「打码不准」：
 *  - 末字只盖住左半（「刘某东」的「东」露右边）；
 *  - 内部字符整体漂移半个字（「何某某」的框压在「何」上）；
 *  - 字的底缘残留一条（检测概率图的紧框比字形矮）。
 */
class CharLayoutTest {

    private class Canvas(val w: Int, val h: Int) {
        val lum = IntArray(w * h) { 255 }
        fun block(x0: Int, y0: Int, x1: Int, y1: Int, v: Int = 0) {
            for (y in y0 until y1) for (x in x0 until x1) lum[y * w + x] = v
        }
    }

    /** 一行等宽汉字：n 个字，字宽 cw，字间留 gap 像素白缝 */
    private fun cjkLine(n: Int, cw: Int = 20, gap: Int = 2, left: Int = 20,
                        top: Int = 30, height: Int = 15): Canvas {
        val c = Canvas(240, 60)
        for (k in 0 until n) {
            val x = left + k * (cw + gap)
            c.block(x, top, x + cw, top + height)
        }
        return c
    }

    private fun spansOf(vararg ranges: Pair<Float, Float>) =
        ranges.map { floatArrayOf(it.first, it.second) }

    @Test
    fun band_stops_at_the_gap_between_lines() {
        val c = Canvas(200, 70)
        c.block(20, 10, 120, 22)       // 上一行
        c.block(20, 38, 120, 52)       // 这一行
        // 检测紧框给得偏松（上下各多出 4px），墨迹实测应该收回到 38..52
        val s = CharLayout.split(
            c.lum, 200, 70, "一二三", spansOf(0.1f to 0.25f, 0.25f to 0.4f, 0.4f to 0.55f),
            hintTop = 34f, hintBottom = 56f, contentLeft = 18f, contentRight = 122f
        )
        assertEquals(38, s.top)
        assertEquals(52, s.bottom)
    }

    @Test
    fun last_char_reaches_the_ink_end_even_if_ctc_stops_early() {
        // CTC 只报到 0.62（真实墨迹到 0.9 左右）：等宽汉字要按墨迹铺满
        val c = cjkLine(4)
        val s = CharLayout.split(
            c.lum, 240, 60, "一二三四",
            spansOf(0.08f to 0.18f, 0.18f to 0.28f, 0.28f to 0.38f, 0.38f to 0.50f),
            hintTop = 29f, hintBottom = 46f, contentLeft = 18f, contentRight = 110f
        )
        assertEquals(20f, s.xs[0], 0.001f)          // 贴到第一个字的墨迹左缘
        assertEquals(106f, s.xs[4], 0.001f)         // 20 + 3*22 + 20 = 106，最后一个字的右缘
        // 每个字都落在自己的格子里
        for (k in 0 until 4) {
            val cellL = 20f + k * 22f
            assertTrue("第 $k 个字的左边不能越界", s.xs[k] >= cellL - 1.5f)
            assertTrue("第 $k 个字的右边不能越界", s.xs[k + 1] <= cellL + 22f + 1.5f)
        }
    }

    @Test
    fun internal_boundary_snaps_to_the_white_valley() {
        val c = cjkLine(3)
        // 故意把内部两条边界给偏（0.22 / 0.34 → 分别落在第 1、2 个字里面）
        val s = CharLayout.split(
            c.lum, 240, 60, "何某某",
            spansOf(0.05f to 0.15f, 0.15f to 0.22f, 0.22f to 0.34f),
            hintTop = 29f, hintBottom = 46f, contentLeft = 18f, contentRight = 90f
        )
        // 真实白缝在 40..42 与 62..64（字宽 20、间隔 2）
        assertTrue("第一条边界应吸附到 40~42，实际 ${s.xs[1]}", s.xs[1] in 40f..42.5f)
        assertTrue("第二条边界应吸附到 62~64，实际 ${s.xs[2]}", s.xs[2] in 62f..64.5f)
    }

    @Test
    fun digits_keep_ctc_spacing_but_cover_the_whole_ink_extent() {
        val c = Canvas(240, 60)
        // 10 个窄数字，等宽 12，间隔 2，从 50 到 190
        for (k in 0 until 10) c.block(50 + k * 14, 30, 50 + k * 14 + 12, 46)
        val spans = (0 until 10).map {
            val f0 = 0.20f + it * 0.06f
            floatArrayOf(f0, f0 + 0.055f)
        }
        val s = CharLayout.split(
            c.lum, 240, 60, "1234567890", spans,
            hintTop = 29f, hintBottom = 47f, contentLeft = 48f, contentRight = 192f
        )
        assertEquals(50f, s.xs[0], 0.001f)
        assertEquals(188f, s.xs[10], 0.001f)
        for (k in 1..10) assertTrue("边界必须递增", s.xs[k] > s.xs[k - 1])
    }

    @Test
    fun wide_char_detection_matches_real_chinese_text() {
        assertTrue(CharLayout.isWide('刘'))
        assertTrue(CharLayout.isWide('，'))
        assertTrue(CharLayout.isWide('１'))
        assertTrue(!CharLayout.isWide('1'))
        assertTrue(!CharLayout.isWide('A'))
        assertTrue(!CharLayout.isWide(' '))
    }

    @Test
    fun degenerate_input_never_crashes() {
        val lum = IntArray(4) { 255 }
        val s = CharLayout.split(lum, 2, 2, "一", listOf(floatArrayOf(0f, 1f)), 0f, 1f, 0f, 2f)
        assertEquals(2, s.xs.size)
        assertTrue(s.bottom > s.top)
    }
}
