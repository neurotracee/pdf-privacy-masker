package com.neurotracee.pdfmask.core

import kotlin.math.min

/**
 * 预览页的缩放 / 平移状态换算。
 *
 * 约定：屏幕坐标 = 内容坐标 × zoom + pan；缩放以两指中心为锚点，
 * 缩放前后「上一帧两指中心下的那个内容点」必须仍落在本帧两指中心下。
 *
 * 2026-11-16 修的 bug：旧代码先把 pan 按锚点缩到新倍数（`c - (c - pan) * k`），
 * 又把两指中心的位移 `c - lastCentroid` 加了一次。两指中心在捏合过程中本来就会
 * 移动，于是每帧多出 `(Δc)(1 - k)` 的误差，累加起来就是「一放大画面就往右下抽」。
 * 正确做法是锚点直接用**上一帧**的中心：`pan' = c - (lastC - pan) * k`，
 * 这一次乘法同时完成了缩放和跟随平移，不会重复计算。
 */
object PageZoom {

    const val MAX = 6f

    /** 把平移量夹在「放大后内容的可移动范围」内；zoom 为 1 时只能是 0 */
    fun clampPan(zoom: Float, panX: Float, panY: Float, w: Float, h: Float): FloatArray {
        val maxX = (zoom - 1f) * w
        val maxY = (zoom - 1f) * h
        return floatArrayOf(
            panX.coerceIn(-maxX, 0f),
            panY.coerceIn(-maxY, 0f)
        )
    }

    /**
     * 一帧双指事件：先按距离比缩放，再让上一帧中心下的内容跟到本帧中心。
     *
     * @param prevCx/prevCy 上一帧两指中心（首帧传本帧中心，等价于只缩放不平移）
     * @param prevDist 上一帧两指间距；<= 1 时视为还没有基准，直接返回原值
     * @return [zoom, panX, panY]
     */
    fun pinch(
        zoom: Float,
        panX: Float,
        panY: Float,
        prevCx: Float,
        prevCy: Float,
        cx: Float,
        cy: Float,
        prevDist: Float,
        dist: Float,
        w: Float,
        h: Float
    ): FloatArray {
        if (prevDist <= 1f || dist <= 1f) {
            return floatArrayOf(zoom, panX, panY)
        }
        val nz = (zoom * (dist / prevDist)).coerceIn(1f, MAX)
        val k = nz / zoom
        // 上一帧中心下的内容点 p = (prevC - pan) / zoom，
        // 要求它在本帧落到 c：c = p * nz + pan'  →  pan' = c - (prevC - pan) * k
        val nx = cx - (prevCx - panX) * k
        val ny = cy - (prevCy - panY) * k
        val p = clampPan(nz, nx, ny, w, h)
        return floatArrayOf(nz, p[0], p[1])
    }

    /** 屏幕坐标 → 内容坐标 */
    fun toContent(px: Float, py: Float, zoom: Float, panX: Float, panY: Float): FloatArray =
        floatArrayOf((px - panX) / zoom, (py - panY) / zoom)

    /** 内容坐标 → 屏幕坐标（放大镜、虚线框回显用） */
    fun toScreen(px: Float, py: Float, zoom: Float, panX: Float, panY: Float): FloatArray =
        floatArrayOf(px * zoom + panX, py * zoom + panY)

    /**
     * 触摸点命中第几页的哪个框——留一点像素宽容，小字框也点得中。
     * 单位是页面点，与 [Finding.rect] 同一坐标系。
     */
    fun hitPadded(
        x: Float, y: Float,
        rect: Rect,
        padX: Float, padY: Float
    ): Boolean =
        x >= rect.x0 - padX && x <= rect.x1 + padX &&
            y >= rect.y0 - padY && y <= rect.y1 + padY

    /** 两个框的重叠面积占较小框的比例，用于判断「这个橡皮擦是否真的擦到了某个框」 */
    fun overlapRatio(a: Rect, b: Rect): Float {
        val x0 = maxOf(a.x0, b.x0)
        val y0 = maxOf(a.y0, b.y0)
        val x1 = min(a.x1, b.x1)
        val y1 = min(a.y1, b.y1)
        if (x1 <= x0 || y1 <= y0) return 0f
        val inter = (x1 - x0) * (y1 - y0)
        val small = min(a.area, b.area)
        return if (small <= 0f) 0f else (inter / small).coerceIn(0f, 1f)
    }
}
