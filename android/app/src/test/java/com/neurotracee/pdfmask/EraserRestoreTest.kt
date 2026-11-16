package com.neurotracee.pdfmask

import android.graphics.Bitmap
import android.graphics.Color
import com.neurotracee.pdfmask.core.EraserRestore
import com.neurotracee.pdfmask.core.Rect
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * 橡皮擦的像素级回归：只恢复划过的那一小块，别的一律不动。
 *
 * 对应用户 2026-11-16 重申的规则：擦「公民身份证号：」的前缀和冒号可以，
 * 但不能连带把后面的身份证号数字一起恢复，也不能删掉整个标记框。
 */
@RunWith(RobolectricTestRunner::class)
class EraserRestoreTest {

    private fun solid(w: Int, h: Int, color: Int): Bitmap =
        Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).apply { eraseColor(color) }

    private fun pixel(b: Bitmap, x: Int, y: Int) = b.getPixel(x, y)

    @Test
    fun restores_only_the_drawn_patch() {
        val original = solid(100, 100, Color.RED)      // 打码前：红（原文）
        val masked = solid(100, 100, Color.BLUE)       // 打码后：蓝（马赛克）

        // 页面点与像素 1:1，划 (10,10)-(25,25)
        val done = EraserRestore.apply(masked, original, Rect(10f, 10f, 25f, 25f), 1f, 1f)
        assertNotNull(done)

        // 框内恢复成红
        assertEquals(Color.RED, pixel(masked, 15, 15))
        assertEquals(Color.RED, pixel(masked, 11, 11))
        // 框外仍是蓝（旁边的打码区没被连带恢复）
        assertEquals(Color.BLUE, pixel(masked, 5, 5))
        assertEquals(Color.BLUE, pixel(masked, 40, 15))
        assertEquals(Color.BLUE, pixel(masked, 15, 40))
    }

    @Test
    fun patch_is_expanded_by_one_and_a_half_pixels() {
        val original = solid(60, 60, Color.GREEN)
        val masked = solid(60, 60, Color.MAGENTA)
        val r = EraserRestore.apply(masked, original, Rect(20f, 20f, 30f, 30f), 1f, 1f)
        assertNotNull(r)
        // 左边界 20 - 1.5 → 18；右边界 30 + 1.5 → 31
        assertEquals(18, r!![0])
        assertEquals(31, r[2])
        assertEquals(Color.GREEN, pixel(masked, 18, 18))
        assertEquals(Color.MAGENTA, pixel(masked, 17, 17))
    }

    @Test
    fun out_of_page_rect_is_clamped_not_crashed() {
        val original = solid(40, 40, Color.RED)
        val masked = solid(40, 40, Color.BLUE)
        val r = EraserRestore.apply(masked, original, Rect(-30f, -30f, 500f, 500f), 1f, 1f)
        assertNotNull(r)
        assertEquals(0, r!![0])
        assertEquals(0, r[1])
        assertEquals(40, r[2])
        assertEquals(40, r[3])
        assertEquals(Color.RED, pixel(masked, 0, 0))
        assertEquals(Color.RED, pixel(masked, 39, 39))
    }

    @Test
    fun respects_non_unit_scale() {
        // 页面 100x100 pt 渲染成 200x200 px：scale = 2
        val original = solid(200, 200, Color.RED)
        val masked = solid(200, 200, Color.BLUE)
        val r = EraserRestore.apply(masked, original, Rect(10f, 10f, 20f, 20f), 2f, 2f)
        assertNotNull(r)
        assertEquals(Color.RED, pixel(masked, 30, 30))     // 15pt → 30px
        assertEquals(Color.BLUE, pixel(masked, 5, 5))
        assertEquals(Color.BLUE, pixel(masked, 45, 45))
    }

    @Test
    fun invalid_inputs_are_no_ops() {
        val a = solid(20, 20, Color.RED)
        val b = solid(20, 20, Color.BLUE)
        // 空矩形
        assertNull(EraserRestore.apply(b, a, Rect(5f, 5f, 5f, 5f), 1f, 1f))
        // 尺寸不一致的备份（不该乱贴）
        val small = solid(10, 10, Color.RED)
        assertNull(EraserRestore.apply(b, small, Rect(2f, 2f, 8f, 8f), 1f, 1f))
        assertEquals(Color.BLUE, pixel(b, 5, 5))
    }
}
