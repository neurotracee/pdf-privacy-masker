package com.neurotracee.pdfmask.core

/** 一个字符的原始位置信息，由具体的 PDF 库填充 */
data class TextToken(
    val ch: Char,
    val x0: Float,
    val y0: Float,
    val x1: Float,
    val y1: Float
)

/**
 * 把「一串字符位置」拼成视觉行：字距明显变大时插入一个虚拟空格，
 * 与桌面版把 span 拼接成行的做法保持一致。
 */
object LineAssembler {

    private const val GAP_RATIO = 0.35f

    fun fromTokens(tokens: List<TextToken>): Line? {
        if (tokens.isEmpty()) return null
        val sb = StringBuilder()
        val chars = ArrayList<CharBox?>(tokens.size)
        var prevX1 = Float.NaN
        for (t in tokens) {
            if (!prevX1.isNaN()) {
                val h = t.y1 - t.y0
                if (h > 0f && (t.x0 - prevX1) > h * GAP_RATIO) {
                    sb.append(' ')
                    chars.add(null)
                }
            }
            sb.append(t.ch)
            chars.add(CharBox(t.ch, Rect(t.x0, t.y0, t.x1, t.y1)))
            prevX1 = t.x1
        }
        val text = sb.toString()
        if (text.isBlank()) return null
        return Line(text, chars)
    }

    /** 由字体基线纵坐标与字号推算字符外框（与 PyMuPDF 的 bbox 对齐） */
    fun boxFromBaseline(x: Float, baselineY: Float, w: Float, fontSize: Float): Rect {
        val top = baselineY - fontSize * 1.05f
        val bottom = baselineY + fontSize * 0.25f
        return Rect(x, top, x + w, bottom)
    }
}

/** 一个字符在页面上的原始字形信息 */
data class RawGlyph(
    val ch: Char,
    val x0: Float,
    val x1: Float,
    val yBase: Float,
    val fontSize: Float
)

/**
 * 按基线把所有字形聚成视觉行。
 *
 * 不能用 PDFBox 自带的按行输出：它会把表格里横向拉开的两列判成两行，
 * 导致「姓名」和同一行的「身份证号」被拆散。这里按基线纵坐标聚类，
 * 同一基线的字符（不管来源是几个文本块）合并成一行，与桌面版一致。
 */
object LineBuilder {

    private const val Y_TOL_RATIO = 0.55f
    private const val X_BUCKET_RATIO = 0.5f

    private class Item(val g: RawGlyph, val seq: Int)

    fun build(glyphs: List<RawGlyph>): List<Line> {
        if (glyphs.isEmpty()) return emptyList()
        val items = ArrayList<Item>(glyphs.size)
        glyphs.forEachIndexed { i, g -> items.add(Item(g, i)) }

        // 按基线纵坐标聚类；同一基线的保持原始（内容流）顺序
        val sorted = items.sortedWith(compareBy({ it.g.yBase }, { it.seq }))
        val out = mutableListOf<Line>()
        var i = 0
        while (i < sorted.size) {
            val g0 = sorted[i]
            var maxFs = g0.g.fontSize
            var j = i + 1
            while (j < sorted.size) {
                val g = sorted[j].g
                val t = maxOf(1.5f, Y_TOL_RATIO * maxFs)
                if (kotlin.math.abs(g.yBase - g0.g.yBase) > t) break
                if (g.fontSize > maxFs) maxFs = g.fontSize
                j++
            }
            // 行内排序：只在「明显逆序」时才交换。
            // 中西文混排（如「0755-5866552江苏省」）里两段文字的 x 起点可能算出轻微重叠，
            // 一味按 x 排序会把字序打乱；带容差的冒泡只纠正真正的逆序，其余保持内容流顺序。
            val group = sorted.subList(i, j)
            val tol = maxOf(2f, g0.g.fontSize * 0.6f)
            val ordered = ArrayList<RawGlyph>(group.size)
            for (it in group) ordered.add(it.g)
            var swapped = true
            var guard = 0
            while (swapped && guard < 32) {
                swapped = false
                for (k in 0 until ordered.size - 1) {
                    if (ordered[k].x0 - ordered[k + 1].x0 > tol) {
                        val t = ordered[k]
                        ordered[k] = ordered[k + 1]
                        ordered[k + 1] = t
                        swapped = true
                    }
                }
                guard++
            }

            val tokens = ArrayList<TextToken>(ordered.size)
            for (g in ordered) {
                val top = g.yBase - g.fontSize * 1.05f
                val bottom = g.yBase + g.fontSize * 0.25f
                tokens.add(TextToken(g.ch, g.x0, top, g.x1, bottom))
            }
            LineAssembler.fromTokens(tokens)?.let { out.add(it) }
            i = j
        }
        return out
    }
}
