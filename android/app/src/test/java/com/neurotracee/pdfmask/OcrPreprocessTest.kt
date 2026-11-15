package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.OcrPreprocess
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 扫描件前处理的回归测试（纯 JVM，不需要真机）。
 *
 * 这些数字都来自那份「豆包生成的刁难 PDF」实测：纸底 225~228、字最暗 154，
 * 动态范围 62~76；第 8 页还有中心亮、四角暗的径向光照。
 * 检测网络对这两种页面几乎不激活，一页 15 行只认出 8 行，甚至整页 0 检出。
 */
class OcrPreprocessTest {

    /** 造一页「灰字 + 泛黄纸底」：纸 226，字 154
     *
     *  字号与行距按实际排版来——正文约占版面的 10% 以上，
     *  否则 5% 分位取到的还是纸底，测不出真实场景。 */
    private fun lowContrastPage(w: Int = 128, h: Int = 128): FloatArray {
        val g = FloatArray(w * h) { 226f }
        for (y in 20 until h - 20 step 4) {
            for (x in 20 until w - 20 step 2) {
                g[y * w + x] = 154f
            }
        }
        return g
    }

    /** 正常扫描件：纸 255，字 0 */
    private fun normalPage(w: Int = 128, h: Int = 128): FloatArray {
        val g = FloatArray(w * h) { 255f }
        for (y in 20 until h - 20 step 8) {
            for (x in 20 until w - 20 step 3) {
                g[y * w + x] = 0f
            }
        }
        return g
    }

    @Test
    fun `低对比度页面需要归一化`() {
        val g = lowContrastPage()
        assertTrue(OcrPreprocess.needsContrast(g, 128, 128))
    }

    @Test
    fun `正常页面的动态范围已经够，一个像素都不动`() {
        val g = normalPage()
        assertFalse(OcrPreprocess.needsContrast(g, 128, 128))
    }

    @Test
    fun `均匀纸底没有光照渐变`() {
        assertFalse(OcrPreprocess.hasGradient(lowContrastPage(), 128, 128))
    }

    @Test
    fun `一侧亮一侧暗的页面判定为有渐变`() {
        val w = 128
        val h = 128
        // 左边 226、右边 180：模拟台灯偏一侧
        val g = FloatArray(w * h) { i ->
            val x = i % w
            if (x < w / 2) 226f else 180f
        }
        assertTrue(OcrPreprocess.hasGradient(g, w, h))
    }

    @Test
    fun `压平之后纸底趋于均匀`() {
        val w = 128
        val h = 128
        val g = FloatArray(w * h) { i ->
            val x = i % w
            if (x < w / 2) 226f else 180f
        }
        val f = OcrPreprocess.flatten(g, w, h)
        // 原来左右差 46，压平后左半与右半的纸底应当基本一致
        val left = f[10 * w + 10]
        val right = f[10 * w + (w - 10)]
        assertEquals(255f, left, 6f)
        assertEquals(255f, right, 6f)
    }
}
