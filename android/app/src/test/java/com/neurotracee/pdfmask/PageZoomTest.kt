package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.PageZoom
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 预览缩放/平移的数学回归。
 *
 * 2026-11-16 用户报的「一放大画面就往右下抽一下」就是这里过去的 bug：
 * 旧代码把锚点缩放和两指中心位移各算了一次，每帧多出 (Δc)(1-k) 的误差，
 * 放大倍数越高漂得越明显。下面的用例直接盯住「指下的内容点必须跟住手指」。
 */
class PageZoomTest {

    private val w = 400f
    private val h = 600f

    /** 捏合过程中两指中心一直在缓慢移动：内容点必须始终钉在中心下 */
    @Test
    fun pinch_keeps_content_point_under_moving_centroid() {
        var zoom = 1f
        var panX = 0f
        var panY = 0f
        // 取页面中心附近的一个内容点，初始时它就在两指中心下
        val contentX = 200f
        val contentY = 300f
        var prevCx = contentX
        var prevCy = contentY
        var prevDist = 100f

        for (i in 1..24) {
            val cx = prevCx + 2.5f          // 中心右移
            val cy = prevCy + 1.0f          // 中心下移
            val dist = prevDist + 7f        // 两指张开 → 放大
            val r = PageZoom.pinch(
                zoom, panX, panY, prevCx, prevCy, cx, cy, prevDist, dist, w, h
            )
            zoom = r[0]; panX = r[1]; panY = r[2]
            prevCx = cx; prevCy = cy; prevDist = dist

            val sx = contentX * zoom + panX
            val sy = contentY * zoom + panY
            assertEquals("第 $i 帧内容点横向跑掉了", cx, sx, 0.02f)
            assertEquals("第 $i 帧内容点纵向跑掉了", cy, sy, 0.02f)
        }
        assertTrue("这一串捏合应该放大到 2 倍以上", zoom > 2f)
    }

    /** 放大再缩回 1 倍，必须回到原点，不留残余偏移 */
    @Test
    fun zoom_in_then_out_returns_to_origin() {
        var zoom = 1f
        var panX = 0f
        var panY = 0f
        var prevDist = 100f
        var cx = 180f
        var cy = 260f

        repeat(18) {
            val d = prevDist + 8f
            val r = PageZoom.pinch(zoom, panX, panY, cx, cy, cx, cy, prevDist, d, w, h)
            zoom = r[0]; panX = r[1]; panY = r[2]
            prevDist = d
        }
        assertTrue(zoom > 1.5f)

        repeat(40) {
            val d = (prevDist - 8f).coerceAtLeast(1.5f)
            val r = PageZoom.pinch(zoom, panX, panY, cx, cy, cx, cy, prevDist, d, w, h)
            zoom = r[0]; panX = r[1]; panY = r[2]
            prevDist = d
        }
        assertEquals(1f, zoom, 0.001f)
        assertEquals(0f, panX, 0.001f)
        assertEquals(0f, panY, 0.001f)
    }

    /** 两指同时「缩+移」：真实手势大多是叠加的，长时间也不能漂 */
    @Test
    fun combined_pinch_and_pan_does_not_drift_over_time() {
        var zoom = 1f
        var panX = 0f
        var panY = 0f
        val contentX = 180f
        val contentY = 320f
        var prevCx = contentX
        var prevCy = contentY
        var prevDist = 120f
        val rnd = java.util.Random(20261116L)
        var broken = false

        repeat(200) { i ->
            // 中心来回晃、间距忽大忽小：模拟手指不老实
            val cx = prevCx + (rnd.nextFloat() - 0.45f) * 14f
            val cy = prevCy + (rnd.nextFloat() - 0.45f) * 10f
            val dist = (prevDist + (rnd.nextFloat() - 0.4f) * 12f).coerceIn(40f, 400f)
            val r = PageZoom.pinch(
                zoom, panX, panY, prevCx, prevCy, cx, cy, prevDist, dist, w, h
            )
            val nz = r[0]
            val nx = r[1]
            val ny = r[2]
            // 被边界夹住时（贴到页边）保真不再成立，从那一刻起不再断言
            val clamped = (nx > 0.001f || ny > 0.001f ||
                nx < -(nz - 1f) * w + 0.001f || ny < -(nz - 1f) * h + 0.001f)
            zoom = nz; panX = nx; panY = ny
            prevCx = cx; prevCy = cy; prevDist = dist
            if (!clamped && !broken) {
                assertEquals("第 $i 帧横向漂了", cx, contentX * zoom + panX, 0.05f)
                assertEquals("第 $i 帧纵向漂了", cy, contentY * zoom + panY, 0.05f)
            } else if (clamped) {
                broken = true
            }
        }
    }

    /** 只用平移、不改间距：必须等价于屏幕位移多少、内容就移多少 */
    @Test
    fun pure_two_finger_pan_moves_content_by_the_same_delta() {
        val zoom = 2.2f
        val panX = -120f
        val panY = -80f
        val contentX = 150f
        val contentY = 200f
        val before = PageZoom.toScreen(contentX, contentY, zoom, panX, panY)
        val r = PageZoom.pinch(zoom, panX, panY, 200f, 260f, 230f, 260f, 90f, 90f, w, h)
        assertEquals(zoom, r[0], 1e-4f)
        val after = PageZoom.toScreen(contentX, contentY, r[0], r[1], r[2])
        assertEquals("横向位移应等于两指中心位移", 30f, after[0] - before[0], 1e-3f)
        assertEquals("纵向不该动", 0f, after[1] - before[1], 1e-3f)
    }

    /** 没有上一帧基准时不能动，避免首帧把画面拽走 */
    @Test
    fun first_frame_without_baseline_is_a_no_op() {
        val r = PageZoom.pinch(1f, 0f, 0f, 0f, 0f, 123f, 456f, 0f, 80f, w, h)
        assertEquals(1f, r[0], 0f)
        assertEquals(0f, r[1], 0f)
        assertEquals(0f, r[2], 0f)
    }

    /** 平移量永远不能超出「放大后多出来的那块」 */
    @Test
    fun pan_is_clamped_to_scaled_overflow() {
        val z = 2f
        val a = PageZoom.clampPan(z, -9999f, -9999f, w, h)
        assertEquals(-w, a[0], 0.001f)
        assertEquals(-h, a[1], 0.001f)
        val b = PageZoom.clampPan(z, 500f, 500f, w, h)
        assertEquals(0f, b[0], 0.001f)
        assertEquals(0f, b[1], 0.001f)
        // 1 倍时不允许任何平移
        val c = PageZoom.clampPan(1f, -50f, -50f, w, h)
        assertEquals(0f, c[0], 0.001f)
        assertEquals(0f, c[1], 0.001f)
    }

    /** 屏幕 ↔ 内容坐标互为逆运算（放大镜、虚线框回显都靠这个） */
    @Test
    fun screen_and_content_coordinates_round_trip() {
        val zoom = 3.4f
        val panX = -210f
        val panY = -95f
        val c = PageZoom.toContent(133f, 244f, zoom, panX, panY)
        val s = PageZoom.toScreen(c[0], c[1], zoom, panX, panY)
        assertEquals(133f, s[0], 0.001f)
        assertEquals(244f, s[1], 0.001f)
    }
}
