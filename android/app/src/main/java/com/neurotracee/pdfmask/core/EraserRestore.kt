package com.neurotracee.pdfmask.core

import android.graphics.Bitmap

/**
 * 橡皮擦的像素级实现：把「打码前备份的那一页」里某个小矩形贴回当前页。
 *
 * 规则（用户 2026-11-16 重申）：
 * - **只**恢复这一小块，不删除任何标记框，也不碰旁边的打码区；
 *   例如「公民身份证号：」里的前缀和冒号可以擦回来，后面那串数字仍是马赛克。
 * - 矩形越界时自动收紧到页面内，不会抛异常、也不会写坏别的行。
 *
 * 抽成独立函数是为了能单测：以前这段逻辑埋在 PdfMasker 的大循环里，
 * 没法验证「到底动了哪些像素」。
 */
object EraserRestore {

    /** 像素级容差：抗锯齿边缘多带回 1.5px，避免框边残留一圈灰 */
    private const val PAD_PX = 1.5f

    /**
     * @param target 已经打过码的页位图（会被就地修改）
     * @param backup 打码前的同一页位图
     * @param rect   用户划过的区域，单位是页面点
     * @param scaleX 页面点 → 位图像素（宽）
     * @param scaleY 页面点 → 位图像素（高）
     * @return 实际恢复的像素矩形（[x0, y0, x1, y1]），没有可恢复内容时返回 null
     */
    fun apply(
        target: Bitmap,
        backup: Bitmap,
        rect: Rect,
        scaleX: Float,
        scaleY: Float
    ): IntArray? {
        if (rect.width <= 0f || rect.height <= 0f) return null
        if (target.width <= 0 || target.height <= 0) return null
        if (backup.width != target.width || backup.height != target.height) return null

        val w = target.width
        val h = target.height
        val x0 = (rect.x0 * scaleX - PAD_PX).toInt().coerceIn(0, w - 1)
        val y0 = (rect.y0 * scaleY - PAD_PX).toInt().coerceIn(0, h - 1)
        val x1 = (rect.x1 * scaleX + PAD_PX).toInt().coerceIn(x0 + 1, w)
        val y1 = (rect.y1 * scaleY + PAD_PX).toInt().coerceIn(y0 + 1, h)
        val ww = x1 - x0
        val hh = y1 - y0
        if (ww <= 0 || hh <= 0) return null

        val px = IntArray(ww * hh)
        backup.getPixels(px, 0, ww, x0, y0, ww, hh)
        target.setPixels(px, 0, ww, x0, y0, ww, hh)
        return intArrayOf(x0, y0, x1, y1)
    }
}
