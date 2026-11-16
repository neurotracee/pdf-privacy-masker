package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.MaskRegion
import com.neurotracee.pdfmask.core.Rect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 橡皮擦 = 打码区域减去擦除矩形。
 *
 * 关键回归：叠划多层时，剩余区域必须**互不重叠、并集等于「原区域 − 擦除区」**，
 * 否则同一片像素会被重复马赛克，或者（更糟）擦掉的地方又被盖回去。
 * 以前用「贴回原图像素」的做法，叠划正是出错最多的场景。
 */
class MaskRegionTest {

    private fun area(list: List<Rect>) = list.sumOf { (it.width * it.height).toDouble() }

    private fun noOverlap(list: List<Rect>): Boolean {
        for (i in list.indices) for (j in i + 1 until list.size) {
            if (list[i].intersect(list[j]) != null) return false
        }
        return true
    }

    @Test
    fun no_cut_returns_the_same_rect() {
        val r = Rect(10f, 10f, 30f, 20f)
        assertEquals(listOf(r), MaskRegion.subtract(r, emptyList()))
    }

    @Test
    fun cut_inside_produces_four_pieces_and_keeps_area() {
        val r = Rect(0f, 0f, 100f, 40f)          // 4000
        val cut = Rect(40f, 10f, 60f, 30f)       // 400
        val parts = MaskRegion.subtract(r, listOf(cut))
        assertEquals(4, parts.size)
        assertEquals(3600.0, area(parts), 0.001)
        assertTrue(noOverlap(parts))
        // 每一块都不能与擦除区相交
        for (p in parts) assertEquals(null, p.intersect(cut))
    }

    @Test
    fun cut_at_edges_leaves_three_pieces() {
        val r = Rect(0f, 0f, 100f, 40f)
        val edge = Rect(0f, 0f, 30f, 20f)        // 贴左上角
        val parts = MaskRegion.subtract(r, listOf(edge))
        assertEquals(4000.0 - 600.0, area(parts), 0.001)
        assertTrue(noOverlap(parts))
    }

    @Test
    fun full_cover_leaves_nothing() {
        val r = Rect(10f, 10f, 20f, 20f)
        assertTrue(MaskRegion.subtract(r, listOf(Rect(0f, 0f, 100f, 100f))).isEmpty())
    }

    @Test
    fun touching_without_overlap_is_untouched() {
        val r = Rect(10f, 10f, 20f, 20f)
        val parts = MaskRegion.subtract(r, listOf(Rect(20f, 10f, 30f, 20f)))
        assertEquals(listOf(r), parts)
    }

    @Test
    fun stacked_cuts_never_duplicate_area() {
        // 用户「反复框选、叠加多层」的场景：几十个互相重叠的擦除框
        val r = Rect(0f, 0f, 200f, 60f)
        val cuts = ArrayList<Rect>()
        for (k in 0 until 40) {
            val x = (k * 4).toFloat()
            cuts.add(Rect(x, 5f + (k % 7), x + 18f, 45f - (k % 5)))
        }
        val parts = MaskRegion.subtract(r, cuts)
        assertTrue(noOverlap(parts))
        // 用像素栅格独立算一遍：并集必须严格等于「原区域 − 擦除区」
        val W = 200
        val H = 60
        var expected = 0
        val erased = BooleanArray(W * H)
        for (c in cuts) {
            for (y in c.y0.toInt() until c.y1.toInt()) {
                for (x in c.x0.toInt() until c.x1.toInt()) erased[y * W + x] = true
            }
        }
        for (i in 0 until W * H) if (!erased[i]) expected++
        assertEquals(expected.toDouble(), area(parts), 0.001)
    }

    @Test
    fun erase_part_of_a_name_keeps_the_rest_masked() {
        // 「公民身份证号：」被擦回来时，后面那串数字仍要打码
        val name = Rect(0f, 0f, 60f, 12f)
        val prefix = Rect(0f, 0f, 20f, 12f)
        val parts = MaskRegion.subtract(name, listOf(prefix))
        assertEquals(1, parts.size)
        assertEquals(20f, parts[0].x0, 0.001f)
        assertEquals(60f, parts[0].x1, 0.001f)
    }
}
