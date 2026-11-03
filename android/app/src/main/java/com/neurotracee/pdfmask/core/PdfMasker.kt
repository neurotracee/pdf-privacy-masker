package com.neurotracee.pdfmask.core

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.content.Context
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.graphics.image.JPEGFactory
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.OutputStream
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 打码并输出。
 *
 * 做法：把每一页按目标 DPI 渲染成位图 → 在命中位置做像素级马赛克 →
 * 整页重新压成 JPEG 组装成新的 PDF。
 *
 * 这样输出文件里只有图片，没有文字层：原文档的任何文字都不再存在，
 * 复制、搜文字都取不到原文，比「在原 PDF 上盖一个矩形」彻底。
 */
object PdfMasker {

    data class Options(val dpi: Int = 160, val quality: Int = 78)

    fun mask(
        context: Context,
        src: File,
        findings: List<Finding>,
        out: OutputStream,
        options: Options = Options(),
        onProgress: (Float) -> Unit = {}
    ): MaskSummary {
        PDFBoxResourceLoader.init(context.applicationContext)
        val pfd = ParcelFileDescriptor.open(src, ParcelFileDescriptor.MODE_READ_ONLY)
        val renderer = PdfRenderer(pfd)
        val total = renderer.pageCount
        val doc = PDDocument()
        val stats = LinkedHashMap<String, Int>()
        val hitPages = HashSet<Int>()
        var count = 0
        try {
            for (i in 0 until total) {
                val page = renderer.openPage(i)
                val pw = page.width.toFloat()
                val ph = page.height.toFloat()
                val scale = options.dpi / 72f
                val w = max(1, (pw * scale).roundToInt())
                val h = max(1, (ph * scale).roundToInt())

                val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                bmp.eraseColor(Color.WHITE)
                page.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                page.close()

                val items = findings.filter { it.page == i && !it.suspect }
                if (items.isNotEmpty()) {
                    hitPages.add(i)
                    count += items.size
                    for (f in items) {
                        val lab = if (com.neurotracee.pdfmask.AppPrefs.isEn) Kind.labelEn(f.type)
                        else Kind.label(f.type)
                        stats[lab] = (stats[lab] ?: 0) + 1
                    }
                    Mosaic.apply(bmp, items, w / pw, h / ph)
                }

                val bos = ByteArrayOutputStream()
                bmp.compress(Bitmap.CompressFormat.JPEG, options.quality, bos)
                bmp.recycle()
                val img = JPEGFactory.createFromStream(
                    doc, ByteArrayInputStream(bos.toByteArray())
                )
                val pdfPage = PDPage(PDRectangle(pw, ph))
                doc.addPage(pdfPage)
                PDPageContentStream(doc, pdfPage).use { cs ->
                    cs.drawImage(img, 0f, 0f, pw, ph)
                }
                onProgress((i + 1f) / total)
            }
            doc.save(out)
        } finally {
            try {
                doc.close()
            } catch (_: Exception) {
            }
            try {
                renderer.close()
            } catch (_: Exception) {
            }
            try {
                pfd.close()
            } catch (_: Exception) {
            }
        }
        return MaskSummary(total, count, stats, hitPages.size)
    }
}

/**
 * 真马赛克：块均值降采样 + 向区域均色压平 + 整体压暗 + 确定性噪声。
 * 块内的字形信息被直接丢弃，不是「盖一层半透明蒙版」那种能被还原的做法。
 */
object Mosaic {

    private const val FLATTEN = 0.30f
    private const val DARKEN = 0.62f

    fun apply(bmp: Bitmap, items: List<Finding>, sx: Float, sy: Float) {
        val W = bmp.width
        val H = bmp.height
        for (f in items) {
            val x0 = (f.rect.x0 * sx - 1.5f).toInt().coerceIn(0, W - 1)
            val y0 = (f.rect.y0 * sy - 1.5f).toInt().coerceIn(0, H - 1)
            val x1 = (f.rect.x1 * sx + 1.5f).toInt().coerceIn(x0 + 1, W)
            val y1 = (f.rect.y1 * sy + 1.5f).toInt().coerceIn(y0 + 1, H)
            val w = x1 - x0
            val h = y1 - y0
            if (w < 3 || h < 3) continue
            val px = IntArray(w * h)
            bmp.getPixels(px, 0, w, x0, y0, w, h)
            pixelate(px, w, h, x0, y0)
            bmp.setPixels(px, 0, w, x0, y0, w, h)
        }
    }

    /**
     * 在一个 ARGB 像素块上原地做马赛克（纯函数，便于单元测试）。
     * originX/originY 是这块像素在整页中的位置，只用于生成确定性噪声。
     */
    fun pixelate(px: IntArray, w: Int, h: Int, originX: Int = 0, originY: Int = 0) {
        if (w < 3 || h < 3 || px.size < w * h) return

        // 块大小：不小于 10px，且让区域高度只切成 2 块左右——块越粗，字形残留越少
        val block = max(10, (min(w, h) / 2.2f).toInt())

        // 区域均色，用于压平
        var tr = 0L
        var tg = 0L
        var tb = 0L
        for (c in px) {
            tr += (c shr 16) and 0xFF
            tg += (c shr 8) and 0xFF
            tb += c and 0xFF
        }
        val n = px.size
        val mr = (tr / n).toInt()
        val mg = (tg / n).toInt()
        val mb = (tb / n).toInt()

        var by = 0
        while (by < h) {
            val bh = min(block, h - by)
            var bx = 0
            while (bx < w) {
                val bw = min(block, w - bx)
                var sr = 0
                var sg = 0
                var sb = 0
                var cnt = 0
                for (yy in by until by + bh) {
                    var idx = yy * w + bx
                    for (xx in bx until bx + bw) {
                        val c = px[idx]
                        sr += (c shr 16) and 0xFF
                        sg += (c shr 8) and 0xFF
                        sb += c and 0xFF
                        cnt++
                        idx++
                    }
                }
                if (cnt == 0) cnt = 1
                var ar = sr / cnt
                var ag = sg / cnt
                var ab = sb / cnt
                // 向区域均色压平，抹掉块内残留的笔画灰度分布
                ar = (ar * (1 - FLATTEN) + mr * FLATTEN).toInt()
                ag = (ag * (1 - FLATTEN) + mg * FLATTEN).toInt()
                ab = (ab * (1 - FLATTEN) + mb * FLATTEN).toInt()
                // 整体压暗
                ar = (ar * DARKEN).toInt()
                ag = (ag * DARKEN).toInt()
                ab = (ab * DARKEN).toInt()
                // 确定性扰动：同一位置每次结果一致，但像素与原文无对应关系
                var seed = (originX + bx) * 73856093 xor (originY + by) * 19349663
                seed = seed xor (seed ushr 13)
                val jr = ((seed and 0x1F) - 16) / 2
                val jg = (((seed ushr 5) and 0x1F) - 16) / 2
                val jb = (((seed ushr 10) and 0x1F) - 16) / 2
                ar = (ar + jr).coerceIn(0, 255)
                ag = (ag + jg).coerceIn(0, 255)
                ab = (ab + jb).coerceIn(0, 255)
                val argb = (0xFF shl 24) or (ar shl 16) or (ag shl 8) or ab

                for (yy in by until by + bh) {
                    var idx = yy * w + bx
                    for (xx in bx until bx + bw) {
                        px[idx] = argb
                        idx++
                    }
                }
                bx += block
            }
            by += block
        }
    }
}
