package com.neurotracee.pdfmask.core

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 逐字切分与行带精修：把「一行一个检测框 + 每字一个 CTC 比例」变成真正的字矩形。
 *
 * 纯计算（只吃灰度数组），不依赖 Android，可以直接跑 JVM 单元测试——
 * 打码准不准全靠这里的几何，必须能一条一条验证。
 *
 * 为什么不能直接「检测框 × CTC 比例」：
 *
 *  - **末字偏窄**：CTC 在行尾常常提前收尾，最后一个字只占到 70~85% 的字宽，
 *    打码块盖不住右半边（「刘某东」的「东」露一条边）。
 *  - **内部字漂移**：识别前裁图左右各留了 0.85 个字高的白边，模型会把字往中间挤，
 *    误差沿行累加；到了「担保人何某某」这种行，「某某」的框整体左移半个字，
 *    结果压在「何」上，真正要盖的两个字反而没盖住。
 *  - **上下露底**：检测概率图的紧框在灰字/细笔画上比真实字形矮，
 *    字的底部（尤其汉字的下半截）会露一条。
 *
 * 所以改成「以墨迹实测为准」，全部判据都是通用的，不针对任何一份文档：
 *
 *  1. 行带：只在紧框上下 0.55 个字高的窗口里找「连续有墨的行段」，取与紧框重叠最多的那段。
 *     窗口限制保证不会把上下邻行、表格横线一起吞进来。
 *  2. 横向：汉字（含全角标点）在同一行里是等宽的，先按「墨迹起止 + 等分」铺开，
 *     再把每条内部边界吸附到墨迹投影的谷值；首尾边界直接贴到墨迹两端。
 *     英文/数字这类不等宽文本仍用 CTC 比例，只做首尾贴边与谷值吸附。
 */
object CharLayout {

    /** @param xs 长度 = 字数 + 1 的横向切分边界（crop 像素坐标） */
    data class Split(val top: Int, val bottom: Int, val xs: FloatArray)

    private const val WIDE_MIN = 0x2E80

    /** 汉字、假名、全角标点/字母：等宽排版，可以按等分铺开 */
    fun isWide(c: Char): Boolean {
        val o = c.code
        if (o < WIDE_MIN) return false
        return o in 0x2E80..0x9FFF ||      // CJK 部首 ~ 统一汉字
            o in 0xA000..0xA4CF ||          // 彝文
            o in 0xAC00..0xD7AF ||          // 谚文
            o in 0xF900..0xFAFF ||          // 兼容汉字
            o in 0xFE30..0xFE4F ||          // 竖排标点
            o in 0xFF00..0xFFEF             // 全角字符
    }

    /**
     * @param lum    crop 的灰度像素（0 黑 255 白），长度 w*h
     * @param text   这一框识别出的文字
     * @param spans  每个字的 CTC 比例区间（相对 crop 宽度），spans.size == text.length
     * @param hintTop/hintBottom 检测紧框的上下边（crop 像素，可为小数/越界）
     * @param contentLeft/contentRight 检测框左右边（crop 像素），用来限制横向找墨的范围
     */
    fun split(
        lum: IntArray,
        w: Int,
        h: Int,
        text: String,
        spans: List<FloatArray>,
        hintTop: Float,
        hintBottom: Float,
        contentLeft: Float,
        contentRight: Float,
        thr: Int = -1
    ): Split {
        val n = spans.size
        val cymid = ((hintTop + hintBottom) / 2f).coerceIn(0f, (h - 1).toFloat())
        val hh = max(2f, hintBottom - hintTop)

        // 退化输入：连 crop 都不够大，就按提示带 + 等分返回，绝不让上层拿到空数组
        if (w < 6 || h < 6 || n <= 0 || lum.size < w * h) {
            val t = cymid.toInt().coerceIn(0, h - 1)
            val xs = FloatArray(n + 1) { w.toFloat() * it / n }
            return Split(t, (t + 1).coerceAtMost(h), xs)
        }

        val t = if (thr in 1..254) thr else otsu(lum, w, h)

        // ---- 1. 行带：只在紧框附近找，避免吞邻行/表格线 ----
        val winLo = (hintTop - hh * 0.55f).toInt().coerceIn(0, h - 1)
        val winHi = (hintBottom + hh * 0.55f).roundToInt().coerceIn(winLo + 1, h)

        // 横向找墨只看检测框附近（±0.25 字高）：笔画常被检测框切掉一点要留余量，
        // 但也不能多到把相邻单元格的字算进来
        val mL = (contentLeft - hh * 0.25f).toInt().coerceIn(0, w - 1)
        val mR = (contentRight + hh * 0.25f).roundToInt().coerceIn(mL + 1, w)

        val rowInk = IntArray(h)
        for (y in winLo until winHi) {
            var c = 0
            var i = y * w + mL
            val end = y * w + mR
            while (i < end) {
                if (lum[i] < t) c++
                i++
            }
            rowInk[y] = c
        }
        val rowNeed = max(2, ((mR - mL) * 0.015f).roundToInt())

        var bandTop = hintTop.toInt().coerceIn(0, h - 1)
        var bandBottom = ceil(hintBottom).toInt().coerceIn(bandTop + 1, h)
        run {
            var bestScore = -1f
            var bestTop = -1
            var bestBot = -1
            var y = winLo
            while (y < winHi) {
                if (rowInk[y] < rowNeed) { y++; continue }
                var e = y
                while (e + 1 < winHi && rowInk[e + 1] >= rowNeed) e++
                val ry0 = y
                val ry1 = e + 1                      // [ry0, ry1)
                // 与紧框的重叠长度；完全不重叠时退化成「离紧框中心最近」
                val ov = min(ry1.toFloat(), hintBottom) - max(ry0.toFloat(), hintTop)
                val score = if (ov > 0f) ov * 10f + (ry1 - ry0)
                else 1f / (1f + abs((ry0 + ry1) / 2f - cymid))
                if (score > bestScore) {
                    bestScore = score
                    bestTop = ry0
                    bestBot = ry1
                }
                y = e + 1
            }
            if (bestTop >= 0) {
                val bh = bestBot - bestTop
                // 墨迹段太厚（可能是两条线粘在一起）就退回检测紧框，宁可保守
                if (bh >= hh * 0.45f && bh <= hh * 1.75f) {
                    bandTop = bestTop
                    bandBottom = bestBot
                }
            }
        }
        if (bandBottom <= bandTop) {
            bandTop = hintTop.toInt().coerceIn(0, h - 1)
            bandBottom = ceil(hintBottom).toInt().coerceIn(bandTop + 1, h)
        }

        // ---- 2. 横向：先定墨迹起止，再铺字边界 ----
        val bandH = bandBottom - bandTop
        val colInk = IntArray(w)
        for (y in bandTop until bandBottom) {
            val row = y * w
            for (x in 0 until w) if (lum[row + x] < t) colInk[x]++
        }
        // 只保留检测框附近的墨迹：贴边太远说明抓到的是旁边那一格的字
        val colNeed = max(1, (bandH * 0.06f).roundToInt())
        var inkL = -1
        var inkR = -1
        for (x in mL until mR) if (colInk[x] >= colNeed) { inkL = x; break }
        for (x in (mR - 1) downTo mL) if (colInk[x] >= colNeed) { inkR = x; break }

        if (inkL < 0 || inkR <= inkL || inkR - inkL + 1 < max(4, (mR - mL) / 6)) {
            inkL = mL
            inkR = mR - 1
        }
        val a = inkL.toFloat()
        // 至少留 1px，否则后面按 0 宽度分不出字
        val b = max((inkR + 1).toFloat(), a + 1f)
        // 每条边界之间至少要留的空隙；裁图特别窄时按比例缩，保证区间永远非空
        val step = min(0.5f, (b - a) / n)

        // 等宽文本（纯汉字/全角）按墨迹等分，比 CTC 比例稳得多
        val uniform = n >= 2 && text.none { it == ' ' } && text.all { isWide(it) }
        val base = FloatArray(n + 1)
        base[0] = a
        base[n] = b
        if (uniform) {
            for (k in 1 until n) base[k] = a + (b - a) * k / n
        } else {
            for (k in 1 until n) {
                val f = (spans[k - 1][1] + spans[k][0]) / 2f
                // 给后面每个边界留出最小间距，避免「越靠后越被顶到 b 上」导致区间反向
                val loK = base[k - 1] + step
                val room = b - (n - k) * step
                base[k] = if (room <= loK) loK else (f * w).coerceIn(loK, room)
            }
        }

        // ---- 3. 吸附到墨迹谷值：汉字之间那道白缝就是最可靠的切分位置 ----
        val xs = base.copyOf()
        val pitch = (b - a) / n
        val win = max(1, min((pitch * 0.42f).roundToInt(), (bandH * 0.5f).roundToInt()))
        for (k in 1 until n) {
            val lo = max(xs[k - 1] + step, base[k] - win).toInt().coerceIn(1, w - 1)
            val hi = min(base[k] + win, b - 1f).toInt().coerceIn(lo, w - 1)
            if (hi < lo) continue
            var vx = -1
            var vv = Int.MAX_VALUE
            for (x in lo..hi) {
                if (colInk[x] < vv) { vv = colInk[x]; vx = x }
            }
            val est = base[k].toInt().coerceIn(0, w - 1)
            val peak = max(colInk[est], 1)
            if (vx >= 0 && vv * 4 <= peak * 3) xs[k] = vx + 0.5f
        }

        // ---- 4. 收尾：严格单调、且不越过墨迹右端 ----
        xs[0] = a
        for (k in 1 until n) {
            val loK = xs[k - 1] + step
            val room = b - (n - k) * step
            xs[k] = if (room <= loK) loK else xs[k].coerceIn(loK, room)
        }
        xs[n] = max(b, xs[n - 1] + step)

        return Split(bandTop, bandBottom, xs)
    }

    /** Otsu 阈值：纸底与墨迹双峰，比固定阈值更能适应灰底/黄底扫描件 */
    fun otsu(lum: IntArray, w: Int, h: Int): Int {
        val hist = IntArray(256)
        var total = 0
        var sumAll = 0L
        val n = min(lum.size, w * h)
        for (i in 0 until n) {
            val v = lum[i].coerceIn(0, 255)
            hist[v]++
            total++
            sumAll += v
        }
        if (total == 0) return 128
        var sumB = 0L
        var wB = 0
        var best = 0.0
        var bestT = 128
        for (v in 0..255) {
            wB += hist[v]
            if (wB == 0) continue
            val wF = total - wB
            if (wF == 0) break
            sumB += v.toLong() * hist[v]
            val mB = sumB.toDouble() / wB
            val mF = (sumAll - sumB).toDouble() / wF
            val between = wB.toDouble() * wF * (mB - mF) * (mB - mF)
            if (between > best) {
                best = between
                bestT = v
            }
        }
        // 纸面几乎全白、只有极少墨点时 Otsu 会偏向极值，夹一下更稳
        return bestT.coerceIn(60, 200)
    }
}
