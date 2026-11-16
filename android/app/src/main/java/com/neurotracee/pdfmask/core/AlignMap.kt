package com.neurotracee.pdfmask.core

/**
 * 「摆正图坐标 → 页面坐标」的映射。
 *
 * OCR 是在摆正后的图上做的（歪 0.3~2 度的扫描件必须先把行摆平，否则整行漏检），
 * 所以检测出的每个框都要按同一个角度逆变换回去。这里把这一步单独抽出来，
 * 是因为它最容易写错方向：用正向矩阵代替逆矩阵，误差会变成 2θ，
 * 页面上越靠右的框偏得越多，看起来就是「打码块随文字从左向右上飘」。
 *
 * 独立成类还有个好处：单元测试可以直接拿真实扫描页的检测结果跑同一段代码。
 */
class AlignMap(
    private val bw: Int,
    private val bh: Int,
    private val skew: Float,
    private val pageW: Float,
    private val pageH: Float
) {
    private val scaleX = if (bw > 0) pageW / bw else 1f
    private val scaleY = if (bh > 0) pageH / bh else 1f
    private val cx = bw / 2f
    private val cy = bh / 2f

    /** 摆正图里的矩形 → 页面点坐标。歪页面取四角外接矩形，宁可多盖一点也不漏 */
    fun toPage(r: Rect): Rect {
        if (skew == 0f) {
            return Rect(r.x0 * scaleX, r.y0 * scaleY, r.x1 * scaleX, r.y1 * scaleY)
        }
        var x0 = Float.MAX_VALUE
        var y0 = Float.MAX_VALUE
        var x1 = -Float.MAX_VALUE
        var y1 = -Float.MAX_VALUE
        for ((px, py) in arrayOf(
            r.x0 to r.y0, r.x1 to r.y0, r.x1 to r.y1, r.x0 to r.y1
        )) {
            val q = OcrPreprocess.mapToSource(px, py, cx, cy, skew)
            if (q[0] < x0) x0 = q[0]
            if (q[1] < y0) y0 = q[1]
            if (q[0] > x1) x1 = q[0]
            if (q[1] > y1) y1 = q[1]
        }
        return Rect(x0 * scaleX, y0 * scaleY, x1 * scaleX, y1 * scaleY)
    }
}
