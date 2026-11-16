package com.neurotracee.pdfmask

import android.graphics.RectF
import com.neurotracee.pdfmask.core.OcrPreprocess
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/**
 * 倾斜校正的坐标反算。
 *
 * 这条回归以前没有：`unrotateBox` 抄成了正向旋转矩阵，而「摆正图 → 原图」
 * 需要逆矩阵，等于把位移放大成 2θ。歪 1 度的页面上，离页心 500px 的框会偏
 * 十几个像素——正是用户看到的「打码块从左向右上飘、字的下面漏打」。
 */
@RunWith(RobolectricTestRunner::class)
class SkewGeometryTest {

    private fun rotate(x: Float, y: Float, cx: Float, cy: Float, deg: Float): FloatArray {
        // 与 OcrPreprocess.rotate() 一致：Matrix.postRotate，顺时针为正
        val rad = Math.toRadians(deg.toDouble())
        val ca = kotlin.math.cos(rad).toFloat()
        val sa = kotlin.math.sin(rad).toFloat()
        val dx = x - cx
        val dy = y - cy
        return floatArrayOf(ca * dx - sa * dy + cx, sa * dx + ca * dy + cy)
    }

    @Test
    fun map_to_source_inverts_the_rotation() {
        val cx = 400f
        val cy = 600f
        for (deg in floatArrayOf(-3f, -1.2f, 0.5f, 1.8f, 2.75f)) {
            for (p in arrayOf(120f to 90f, 700f to 150f, 380f to 900f, 40f to 1100f)) {
                val r = rotate(p.first, p.second, cx, cy, deg)
                val q = OcrPreprocess.mapToSource(r[0], r[1], cx, cy, deg)
                assertEquals(p.first, q[0], 0.02f)
                assertEquals(p.second, q[1], 0.02f)
            }
        }
    }

    @Test
    fun a_box_on_the_right_edge_does_not_drift_upwards() {
        // 页心 (500,700)，1.5 度倾斜，右侧一行的中心：反算后必须回到原位，
        // 而不是往上飘（旧实现会飘 ~26px）
        val cx = 500f
        val cy = 700f
        val deg = 1.5f
        val aligned = rotate(900f, 400f, cx, cy, deg)
        val back = OcrPreprocess.unrotateBox(
            RectF(aligned[0] - 60f, aligned[1] - 12f, aligned[0] + 60f, aligned[1] + 12f),
            cx, cy, deg
        )
        val mx = (back.left + back.right) / 2f
        val my = (back.top + back.bottom) / 2f
        assertEquals(900f, mx, 0.6f)
        assertEquals(400f, my, 0.6f)
        // 外接矩形只会比原框略大（补偿旋转），不会只往上扩
        val topGrow = 388f - back.top
        val botGrow = back.bottom - 412f
        assertEquals(topGrow, botGrow, 1.5f)
    }
}
