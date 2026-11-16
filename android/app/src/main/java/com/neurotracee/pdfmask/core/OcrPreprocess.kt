package com.neurotracee.pdfmask.core

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.RectF
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin

/**
 * 扫描件的前处理：把「灰字 + 泛黄纸底」「一边亮一边暗」这类页面，拉回
 * 检测网络习惯的黑白纸面。
 *
 * 与 Windows 端 `pdfmask_ocr.normalize_contrast` / `flatten_illumination`
 * 是同一套算法、同一套阈值，两端结果要对得上。
 *
 * 两条规则，都是按页自适应，不写死任何一页的亮度：
 *
 * 1. **对比度归一化**：灰度 5% / 90% 分位当黑白端点，把 [lo, hi] 铺满
 *    [0,255]。只在「动态范围 < 120 且纸底够亮」时生效——刁难样本实测
 *    纸底 225、字最暗 154，动态范围只有 62~76，检测头整行激活不起来，
 *    一页 15 行只认出 8 行。正常文档一个像素都不动。
 *
 * 2. **光照压平**：把页面切成 64px 的格子，每格取 90% 分位当「纸底亮度」，
 *    再做双线性插值，逐像素除去。拍歪、台灯偏一侧的扫描件会出现
 *    「中心亮、四角暗」，全局拉伸会把暗区直接压死、行与行粘成一片，
 *    识别出来就是乱码——这种页面必须先除光照再谈对比度。
 *
 * 用分位数而不是均值：一格 64×64 里文字占比通常不到 10%，90% 分位基本
 * 落在纸底上；用均值会被笔画拉低，除完把笔画漂白、笔画断裂。
 *
 * 所有函数都只吃 FloatArray，便于在 JVM 单元测试里直接验证。
 */
object OcrPreprocess {

    private const val CELL = 64
    private const val GRAD_TRIGGER = 14f
    private const val RANGE_MIN = 120f
    private const val PAPER_MIN = 150f
    private const val LO_P = 0.05f
    private const val HI_P = 0.90f

    /** 处理结果：需要替换时返回新 Bitmap，不需要时返回 null（调用方继续用原图） */
    fun normalize(src: Bitmap): Bitmap? {
        val w = src.width
        val h = src.height
        if (w < 32 || h < 32) return null
        val px = IntArray(w * h)
        src.getPixels(px, 0, w, 0, 0, w, h)

        val gray = FloatArray(w * h)
        for (i in gray.indices) {
            val p = px[i]
            gray[i] = (((p shr 16) and 0xFF) * 0.299f +
                ((p shr 8) and 0xFF) * 0.587f +
                (p and 0xFF) * 0.114f)
        }

        var work = gray
        if (hasGradient(work, w, h)) work = flatten(work, w, h)
        if (!needsContrast(work, w, h)) return null

        val (lo, hi) = percentileRange(work, LO_P, HI_P)
        if (hi - lo < 2f) return null
        val scale = 255f / (hi - lo)
        val out = IntArray(w * h)
        for (i in out.indices) {
            var v = ((work[i] - lo) * scale).roundToInt()
            if (v < 0) v = 0
            if (v > 255) v = 255
            out[i] = (0xFF shl 24) or (v shl 16) or (v shl 8) or v
        }
        return Bitmap.createBitmap(out, w, h, Bitmap.Config.ARGB_8888)
    }

    /** 纸底够亮、但动态范围太窄 → 值得拉一次黑白场 */
    fun needsContrast(gray: FloatArray, w: Int, h: Int): Boolean {
        val med = percentileOf(sample(gray, 7), 0.5f)
        if (med < PAPER_MIN) return false
        val (lo, hi) = percentileRange(gray, LO_P, HI_P)
        return hi - lo < RANGE_MIN && hi - lo >= 2f
    }

    /** 网格纸底亮度差超过阈值 → 有明显光照渐变 */
    fun hasGradient(gray: FloatArray, w: Int, h: Int): Boolean {
        val f = paperField(gray, w, h)
        var lo = Float.MAX_VALUE
        var hi = -Float.MAX_VALUE
        for (v in f) {
            if (v < lo) lo = v
            if (v > hi) hi = v
        }
        return hi - lo >= GRAD_TRIGGER
    }

    /** 逐像素除以所在地的纸底亮度：纸底变均匀，字仍然更暗 */
    fun flatten(gray: FloatArray, w: Int, h: Int): FloatArray {
        val f = paperField(gray, w, h)
        val out = FloatArray(gray.size)
        val ny = max(1, h / CELL)
        val nx = max(1, w / CELL)
        for (y in 0 until h) {
            val fy = (y.toFloat() / (h - 1).coerceAtLeast(1)) * (ny - 1)
            val y0 = fy.toInt().coerceIn(0, ny - 1)
            val y1 = min(y0 + 1, ny - 1)
            val ty = fy - y0
            for (x in 0 until w) {
                val fx = (x.toFloat() / (w - 1).coerceAtLeast(1)) * (nx - 1)
                val x0 = fx.toInt().coerceIn(0, nx - 1)
                val x1 = min(x0 + 1, nx - 1)
                val tx = fx - x0
                val v00 = f[y0 * nx + x0]
                val v10 = f[y0 * nx + x1]
                val v01 = f[y1 * nx + x0]
                val v11 = f[y1 * nx + x1]
                val top = v00 + (v10 - v00) * tx
                val bot = v01 + (v11 - v01) * tx
                val bg = top + (bot - top) * ty
                var v = gray[y * w + x] / max(bg, 1f) * 255f
                if (v < 0f) v = 0f
                if (v > 255f) v = 255f
                out[y * w + x] = v
            }
        }
        return out
    }

    /** 每格取 90% 分位当纸底亮度，得到 ny×nx 的网格 */
    private fun paperField(gray: FloatArray, w: Int, h: Int): FloatArray {
        val ny = max(1, h / CELL)
        val nx = max(1, w / CELL)
        val ch = h / ny
        val cw = w / nx
        val field = FloatArray(ny * nx)
        val buf = FloatArray(max(1, ch * cw))
        for (gy in 0 until ny) {
            for (gx in 0 until nx) {
                var k = 0
                var y = gy * ch
                while (y < (gy + 1) * ch) {
                    var x = gx * cw
                    val row = y * w
                    while (x < (gx + 1) * cw) {
                        buf[k++] = gray[row + x]
                        x++
                    }
                    y++
                }
                // 用原始 float 数组排序：一页 A4 有 700 多个格子、每格 4000 像素，
                // 走 List<Float> 会装箱近 300 万个对象，中端机上 GC 直接卡住十几秒。
                java.util.Arrays.sort(buf, 0, k)
                field[gy * nx + gx] = pick(buf, k, 0.90f)
            }
        }
        return field
    }

    private fun percentileRange(gray: FloatArray, loP: Float, hiP: Float): Pair<Float, Float> {
        val s = sample(gray, 4)
        java.util.Arrays.sort(s)
        return pick(s, s.size, loP) to pick(s, s.size, hiP)
    }

    /** 等距抽样，避免全量拷贝 */
    private fun sample(gray: FloatArray, step: Int): FloatArray {
        val n = gray.size / step + 1
        val out = FloatArray(n)
        var i = 0
        var k = 0
        while (i < gray.size && k < n) {
            out[k++] = gray[i]
            i += step
        }
        return if (k == n) out else out.copyOf(k)
    }

    /** 在已排序的 [0, n) 上取分位 */
    private fun pick(sorted: FloatArray, n: Int, p: Float): Float {
        if (n <= 0) return 0f
        val idx = ((n - 1) * p).roundToInt().coerceIn(0, n - 1)
        return sorted[idx]
    }

    private fun percentileOf(values: FloatArray, p: Float): Float {
        if (values.isEmpty()) return 0f
        java.util.Arrays.sort(values)
        return pick(values, values.size, p)
    }

    // ------------------------------------------------------------------ 倾斜校正
    // 与 Python 端 pdfmask_ocr.estimate_skew 用同一套判据：
    // 旋转若干角度，看水平投影「相邻行差」的方差，文字摆得越正，行间空隙越干净。
    // 手机拍照 / 平板扫描的页面几乎都带 0.3~2 度歪，歪着送进检测网络会整行漏掉。

    private fun graySmall(src: Bitmap): Triple<FloatArray, Int, Int> {
        val s = min(1f, 600f / maxOf(src.width, src.height).toFloat())
        val w = max(1, (src.width * s).roundToInt())
        val h = max(1, (src.height * s).roundToInt())
        val small = if (w == src.width && h == src.height) src
                    else Bitmap.createScaledBitmap(src, w, h, true)
        val px = IntArray(w * h)
        small.getPixels(px, 0, w, 0, 0, w, h)
        val gray = FloatArray(w * h) { i ->
            val c = px[i]
            ((c shr 16 and 0xFF) * 0.299f + (c shr 8 and 0xFF) * 0.587f + (c and 0xFF) * 0.114f)
        }
        if (small !== src) small.recycle()
        return Triple(gray, w, h)
    }

    /** 水平投影相邻行差值的方差；不新建旋转后的图，直接按角度反采样，几十次评分也不卡 */
    private fun skewScore(gray: FloatArray, w: Int, h: Int, deg: Float): Float {
        val rad = Math.toRadians(deg.toDouble())
        val ca = cos(rad).toFloat()
        val sa = sin(rad).toFloat()
        val cx = w / 2f
        val cy = h / 2f
        val prof = FloatArray(h)
        for (y in 0 until h) {
            val dy = y - cy
            var cnt = 0f
            var x = 0
            while (x < w) {
                val dx = x - cx
                val sx = (ca * dx + sa * dy + cx).roundToInt()
                val sy = (-sa * dx + ca * dy + cy).roundToInt()
                if (sx in 0 until w && sy in 0 until h && gray[sy * w + sx] < 165f) cnt++
                x += 2
            }
            prof[y] = cnt
        }
        var mean = 0f
        for (y in 1 until h) mean += prof[y] - prof[y - 1]
        mean /= max(1, h - 1)
        var v = 0f
        for (y in 1 until h) {
            val d = prof[y] - prof[y - 1] - mean
            v += d * d
        }
        return v / max(1, h - 1)
    }

    /** 返回「把页面摆正需要旋转的角度」；小于 0.2 度不动，免得白转一次掉精度 */
    fun estimateSkew(src: Bitmap): Float {
        val (gray, w, h) = graySmall(src)
        var best = 0f
        var bestV = skewScore(gray, w, h, 0f)
        var t = -3f
        while (t <= 3.0001f) {
            val v = skewScore(gray, w, h, t)
            if (v > bestV) { bestV = v; best = t }
            t += 0.25f
        }
        t = best - 0.35f
        while (t <= best + 0.3501f) {
            val v = skewScore(gray, w, h, t)
            if (v > bestV) { bestV = v; best = t }
            t += 0.05f
        }
        return if (abs(best) < 0.2f) 0f else best
    }

    /** 整页旋转摆正，画布尺寸不变、四角补白，这样坐标换算只需要绕中心一次 */
    fun rotate(src: Bitmap, deg: Float): Bitmap {
        val out = Bitmap.createBitmap(src.width, src.height, Bitmap.Config.ARGB_8888)
        val c = Canvas(out)
        c.drawColor(Color.WHITE)
        val m = Matrix()
        m.postRotate(deg, src.width / 2f, src.height / 2f)
        c.drawBitmap(src, m, null)
        return out
    }

    /** 把摆正图里的检测框换回原图坐标：四角各转一次，取外接矩形 */    fun unrotateBox(box: RectF, cx: Float, cy: Float, deg: Float): RectF {
        if (deg == 0f) return box
        val rad = Math.toRadians(deg.toDouble())
        val ca = cos(rad).toFloat()
        val sa = sin(rad).toFloat()
        var x0 = Float.MAX_VALUE
        var y0 = Float.MAX_VALUE
        var x1 = -Float.MAX_VALUE
        var y1 = -Float.MAX_VALUE
        for (p in arrayOf(box.left to box.top, box.right to box.top,
                          box.right to box.bottom, box.left to box.bottom)) {
            val dx = p.first - cx
            val dy = p.second - cy
            val x = ca * dx - sa * dy + cx
            val y = sa * dx + ca * dy + cy
            x0 = min(x0, x); y0 = min(y0, y); x1 = max(x1, x); y1 = max(y1, y)
        }
        return RectF(x0, y0, x1, y1)
    }

}
