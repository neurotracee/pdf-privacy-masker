package com.neurotracee.pdfmask.core

import android.content.Context
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import com.tom_roush.pdfbox.text.TextPosition
import java.io.File

/**
 * 用 PDFBox 读出每页的文字与每字外框。
 *
 * PDFBox 的 TextPosition 给出的是「方向调整后」的坐标：原点在页面左上角，
 * 单位是 PDF 点（1/72 英寸），与 PdfRenderer 的页面尺寸同一坐标系，
 * 因此可以直接按「渲染像素 / 页面点」的比例映射到打码用的位图上。
 *
 * 这里不使用 PDFBox 的行切分结果，只收集字形，交给 [LineBuilder] 按基线重建行。
 */
object PdfTextExtractor {

    fun extract(context: Context, file: File): List<PageText> {
        PDFBoxResourceLoader.init(context.applicationContext)
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
