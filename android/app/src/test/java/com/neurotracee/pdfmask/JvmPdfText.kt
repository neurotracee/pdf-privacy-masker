package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.LineBuilder
import com.neurotracee.pdfmask.core.PageText
import com.neurotracee.pdfmask.core.RawGlyph
import org.apache.pdfbox.pdmodel.PDDocument
import org.apache.pdfbox.text.PDFTextStripper
import org.apache.pdfbox.text.TextPosition
import java.io.File

/** 单元测试用的 PDF 文字提取器：与 Android 版同构，只是换了 PDFBox 的实现方 */
object JvmPdfText {

    fun extract(file: File): List<PageText> {
        val doc = PDDocument.load(file)
        try {
            val count = doc.numberOfPages
            val glyphs = HashMap<Int, MutableList<RawGlyph>>()

            val stripper = object : PDFTextStripper() {
                override fun processTextPosition(text: TextPosition) {
                    val uni = text.unicode
                    if (uni != null && uni.isNotEmpty()) {
                        val fs = text.fontSizeInPt
                        if (fs > 0.1f) {
                            val pno = currentPageNo - 1
                            val base = text.yDirAdj
                            val per = if (uni.length == 1) text.widthDirAdj else text.widthDirAdj / uni.length
                            var x = text.xDirAdj
                            val list = glyphs.getOrPut(pno) { mutableListOf() }
                            for (c in uni) {
                                if (c.isWhitespace()) {
                                    x += per
                                    continue
                                }
                                list.add(RawGlyph(c, x, x + per, base, fs))
                                x += per
                            }
                        }
                    }
                    super.processTextPosition(text)
                }
            }
            stripper.sortByPosition = true
            stripper.getText(doc)

            val out = ArrayList<PageText>(count)
            for (i in 0 until count) {
                val page = doc.getPage(i)
                val box = page.cropBox
                var pw = box.width
                var ph = box.height
                val rot = page.rotation
                if (rot == 90 || rot == 270) {
                    val t = pw
                    pw = ph
                    ph = t
                }
                out.add(PageText(i, pw, ph, LineBuilder.build(glyphs[i] ?: emptyList())))
            }
            return out
        } finally {
            doc.close()
        }
    }
}
