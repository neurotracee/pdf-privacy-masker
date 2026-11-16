package com.neurotracee.pdfmask.core

import kotlin.math.max
import kotlin.math.min

/**
 * 橡皮擦 = 从打码区域里「减掉」一小块，而不是把原文像素贴回来。
 *
 * 为什么改成减法：以前的做法是「先打码 → 再从备份里把这块原像素贴回去」。
 * 贴的时候要靠取整把页面点换算成像素，同一块被反复划、层层叠起来时，
 * 每次贴回的缩放比例都略有不同，于是同一行字被贴出好几个略错位的副本，
 * 看起来就像「框选后又复制了一层内容」。叠得越多，重影越明显。
 *
 * 改成减法之后：
 *  - 打码区域先减去擦除矩形，只对剩下的部分做马赛克；
 *  - 被擦掉的地方**根本没有被写入过**，显示的就是原始像素，不可能出现副本；
 *  - 预览和导出调用的是同一个 [subtract]，所见即所得；
 *  - 擦除只影响与它真正相交的打码块，旁边的号码照样是马赛克。
 */
object MaskRegion {

    /** 判断两个矩形是否真的相交（边缘相切不算） */
    private fun overlaps(a: Rect, b: Rect): Boolean =
        a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1

    /** [rect] 减去一个 [cut]，最多产生 4 块（上、下、左、右） */
    fun cutOne(rect: Rect, cut: Rect): List<Rect> {
        if (!overlaps(rect, cut)) return listOf(rect)
        val out = ArrayList<Rect>(4)
        // 上带
        if (cut.y0 > rect.y0) out.add(Rect(rect.x0, rect.y0, rect.x1, min(cut.y0, rect.y1)))
        // 下带
        if (cut.y1 < rect.y1) out.add(Rect(rect.x0, max(cut.y1, rect.y0), rect.x1, rect.y1))
        // 中间段去掉左右两截
        val my0 = max(rect.y0, cut.y0)
        val my1 = min(rect.y1, cut.y1)
        if (my1 > my0) {
            if (cut.x0 > rect.x0) out.add(Rect(rect.x0, my0, min(cut.x0, rect.x1), my1))
            if (cut.x1 < rect.x1) out.add(Rect(max(cut.x1, rect.x0), my0, rect.x1, my1))
        }
        return out.filter { it.width > 0f && it.height > 0f }
    }

    /**
     * [rect] 依次减去所有 [cuts]，返回剩余的若干矩形。
     *
     * 结果互不重叠、并集 = 原矩形 − 擦除区。擦除掉整块时返回空列表，
     * 上层据此判断「这一处已经被完全擦掉，不要再打码」。
     */
    fun subtract(rect: Rect, cuts: List<Rect>): List<Rect> {
        if (cuts.isEmpty()) return listOf(rect)
        var parts = listOf(rect)
        for (c in cuts) {
            if (c.width <= 0f || c.height <= 0f) continue
            if (!overlaps(rect, c)) continue
            val next = ArrayList<Rect>(parts.size + 2)
            for (p in parts) next.addAll(cutOne(p, c))
            parts = next
            if (parts.isEmpty()) return emptyList()
        }
        return parts
    }
}
