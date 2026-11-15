package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.ctcGroups
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CTC 解码的回归测试。
 *
 * 背景：安卓端识别阶段曾经把「还没有上一个字符」的 -1 哨兵也送去查字典，
 * 抛 ArrayIndexOutOfBoundsException: length=6625; index=-1，异常被上层吞成
 * 「这页没有文字」，于是整份 8 页扫描件在界面上显示「没有识别到隐私信息」，
 * 而检测框其实有 154 个、概率峰值 1.00。这组用例把边界钉死。
 */
class CtcDecodeTest {

    /** 全是 blank：一个字都不该产出 */
    @Test
    fun allBlankYieldsNothing() {
        assertTrue(ctcGroups(intArrayOf(0, 0, 0, 0)).isEmpty())
    }

    /** 空输入不能崩 */
    @Test
    fun emptyInputYieldsNothing() {
        assertTrue(ctcGroups(IntArray(0)).isEmpty())
    }

    /**
     * 首帧就是字符：以前这里会先 flush(-1)，直接数组越界。
     * 现在要求正常返回，且区间从第 0 帧开始。
     */
    @Test
    fun leadingCharDoesNotCrash() {
        val g = ctcGroups(intArrayOf(7, 7, 0, 0))
        assertEquals(1, g.size)
        assertEquals(7, g[0][0])
        assertEquals(0, g[0][1])
        assertEquals(2, g[0][2])
    }

    /** 同一字符被 blank 隔开算两个字（CTC 的标准行为） */
    @Test
    fun blankSeparatesRepeatedChar() {
        val g = ctcGroups(intArrayOf(5, 0, 5))
        assertEquals(2, g.size)
        assertEquals(5, g[0][0])
        assertEquals(5, g[1][0])
        assertEquals(2, g[1][1])
        assertEquals(3, g[1][2])
    }

    /** 相邻同类只合并成一个，区间覆盖整个连续段 */
    @Test
    fun adjacentSameCharMerges() {
        val g = ctcGroups(intArrayOf(0, 3, 3, 3, 0))
        assertEquals(1, g.size)
        assertEquals(3, g[0][0])
        assertEquals(1, g[0][1])
        assertEquals(4, g[0][2])
    }

    /** 多个字符之间的区间首尾相接，不丢帧也不重叠 */
    @Test
    fun spansAreContiguous() {
        val g = ctcGroups(intArrayOf(1, 1, 2, 0, 3, 3, 3))
        assertEquals(3, g.size)
        assertEquals(0, g[0][1]); assertEquals(2, g[0][2])
        assertEquals(2, g[1][1]); assertEquals(3, g[1][2])
        assertEquals(4, g[2][1]); assertEquals(7, g[2][2])
    }

    /** 任何情况下返回的字符索引都必须是正数，否则会去查 dict[-1] */
    @Test
    fun neverReturnsNonPositiveIndex() {
        val g = ctcGroups(intArrayOf(0, 0, 1, 0, 0, 2, 0))
        assertTrue(g.isNotEmpty())
        assertTrue(g.all { it[0] > 0 })
    }
}
