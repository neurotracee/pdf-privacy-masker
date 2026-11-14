package com.neurotracee.pdfmask.core

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 端侧 OCR：给「没有文字层」的 PDF（扫描件、拍照件、纯图片页）补出文字与坐标。
 *
 * 和 Windows 端 `pdfmask_ocr.py` 是同一套算法、同一份模型：
 * PP-OCRv4 det（DB 网络，出文字区域概率图）+ rec（CRNN+CTC，出字符），
 * 推理用 onnxruntime 的 CPU 后端，模型随 apk 分发，**运行时不联网**。
 *
 * 关键点是「每字矩形」从哪来：通用 OCR 只给整行一个框，而打码需要知道
 * 「这行里的手机号是第几个字到第几个字」。rec 网络是 CTC 结构，输出 T 个时间步，
 * 把相邻同类的时间步合并成一组，那组的时间步区间就是该字在行内的横向比例。
 * 这样产出的 [Line] 与文字层路径完全同构，[Detector] 一行都不用改。
 */
object OcrEngine {

    private const val DET_MODEL = "ocr/ch_PP-OCRv4_det_infer.onnx"
    private const val REC_MODEL = "ocr/ch_PP-OCRv4_rec_infer.onnx"
    private const val REC_DICT = "ocr/ppocr_keys_v1.txt"

    /** 检测输入长边上限：越大越准也越慢，低端机取 1280 已经够用 */
    private const val DET_LIMIT = 1280
    private const val DET_THRESH = 0.30f
    private const val BOX_THRESH = 0.50f
    private const val UNCLIP_RATIO = 1.6f
    private const val MIN_BOX_SIDE = 3

    private const val REC_HEIGHT = 48
    private const val REC_MAX_W = 1280

    /** 渲染页面用的 DPI（180 相当于 2.5 倍缩放），识别裁剪要够清晰 */
    const val RENDER_DPI = 180
    const val PAD_RATIO = 0.85f

    private val MEAN = floatArrayOf(0.485f, 0.456f, 0.406f)
    private val STD = floatArrayOf(0.229f, 0.224f, 0.225f)

    @Volatile private var env: OrtEnvironment? = null
    @Volatile private var det: OrtSession? = null
    @Volatile private var rec: OrtSession? = null
    @Volatile private var chars: Array<String>? = null
    @Volatile private var failed = false

    /** 模型和推理库是否就绪；失败时整个 OCR 静默跳过，不影响其它功能 */
    fun available(ctx: Context): Boolean = ensure(ctx)

    @Synchronized
    private fun ensure(ctx: Context): Boolean {
        if (chars != null && det != null && rec != null) return true
        if (failed) return false
        return try {
            val e = OrtEnvironment.getEnvironment()
            val opts = OrtSession.SessionOptions().apply {
                // 低端机上别把核占满，留一个给界面线程
                setIntraOpNumThreads(max(1, min(4, Runtime.getRuntime().availableProcessors() - 1)))
                setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            }
            det = e.createSession(cacheModel(ctx, DET_MODEL), opts)
            rec = e.createSession(cacheModel(ctx, REC_MODEL), opts)
            chars = loadDict(ctx)
            env = e
            true
        } catch (t: Throwable) {
            failed = true
            false
        }
    }

    /** 模型放 assets 里，onnxruntime 只认文件路径，首次启动时解到私有目录 */
    private fun cacheModel(ctx: Context, asset: String): String {
        val out = File(ctx.filesDir, asset.replace('/', '_'))
        val needCopy = !out.exists() || runCatching {
            ctx.assets.open(asset).available().toLong() != out.length()
        }.getOrDefault(true)
        if (needCopy) {
            ctx.assets.open(asset).use { ins ->
                out.outputStream().use { outs -> ins.copyTo(outs) }
            }
        }
        return out.absolutePath
    }

    private fun loadDict(ctx: Context): Array<String> {
        val list = ArrayList<String>()
        list.add("")                                  // 0 = blank
        ctx.assets.open(REC_DICT).bufferedReader().useLines { seq ->
            seq.forEach { line -> list.add(line.trimEnd('\r', '\n')) }
        }
        list.add(" ")                                 // 末位 = 空格
        return list.toTypedArray()
    }

    // ------------------------------------------------------------------ 全角折半角

    /** 中文文档里全角数字/字母很常见，规则里的正则只认半角，这里 1:1 折过来 */
    fun foldWidth(c: Char): Char {
        val o = c.code
        if (o in 0xFF01..0xFF5E) return (o - 0xFEE0).toChar()
        if (o == 0x3000) return ' '
        return c
    }

    // ------------------------------------------------------------------ 推理

    private fun detTensor(bmp: Bitmap): Pair<FloatArray, IntArray> {
        val w = bmp.width
        val h = bmp.height
        val padW = (32 - w % 32) % 32
        val padH = (32 - h % 32) % 32
        val W = w + padW
        val H = h + padH
        val px = IntArray(w * h)
        bmp.getPixels(px, 0, w, 0, 0, w, h)
        val data = FloatArray(3 * H * W)
        val plane = H * W
        // 补边用白色（255），归一化后与训练时的 padding 一致
        for (c in 0 until 3) {
            val mean = MEAN[c]
            val std = STD[c]
            val base = c * plane
            for (i in 0 until plane) data[base + i] = ((255f / 255f) - mean) / std
        }
        for (y in 0 until h) {
            val row = y * w
            for (x in 0 until w) {
                val p = px[row + x]
                val dst = y * W + x
                data[dst] = ((((p shr 16) and 0xFF) / 255f) - MEAN[0]) / STD[0]
                data[plane + dst] = ((((p shr 8) and 0xFF) / 255f) - MEAN[1]) / STD[1]
                data[2 * plane + dst] = (((p and 0xFF) / 255f) - MEAN[2]) / STD[2]
            }
        }
        return data to intArrayOf(1, 3, H, W)
    }

    /** 返回检测图坐标系的框：[x0, y0, x1, y1] */
    private fun detectBoxes(bmp: Bitmap): List<FloatArray> {
        val e = env ?: return emptyList()
        val d = det ?: return emptyList()
        val (data, shape) = detTensor(bmp)
        val tensor = OnnxTensor.createTensor(e, FloatBuffer.wrap(data), longArrayOf(
            shape[0].toLong(), shape[1].toLong(), shape[2].toLong(), shape[3].toLong()
        ))
        val out = try {
            d.run(mapOf(d.inputNames.first() to tensor)).use { r ->
                val t = r[0] as OnnxTensor
                val s = t.info.shape              // [1, 1, H, W]
                val buf = t.floatBuffer
                val arr = FloatArray(s[0].toInt() * s[1].toInt() * s[2].toInt() * s[3].toInt())
                buf.get(arr)
                arr to intArrayOf(s[0].toInt(), s[1].toInt(), s[2].toInt(), s[3].toInt())
            }
        } finally {
            tensor.close()
        }
        val prob = out.first
        val ph = out.second[2]
        val pw = out.second[3]
        // 概率图与补齐后的输入同尺寸，换算回未补齐的检测图
        val sx = bmp.width.toFloat() / pw
        val sy = bmp.height.toFloat() / ph

        val mask = BooleanArray(ph * pw)
        var any = false
        for (i in 0 until ph * pw) {
            if (prob[i] > DET_THRESH) { mask[i] = true; any = true }
        }
        if (!any) return emptyList()

        val boxes = ArrayList<FloatArray>()
        val visited = BooleanArray(ph * pw)
        val queue = IntArray(ph * pw)
        for (start in 0 until ph * pw) {
            if (!mask[start] || visited[start]) continue
            var head = 0
            var tail = 0
            queue[tail++] = start
            visited[start] = true
            var x0 = pw; var y0 = ph; var x1 = 0; var y1 = 0
            var sum = 0f; var n = 0
            while (head < tail) {
                val idx = queue[head++]
                val y = idx / pw
                val x = idx % pw
                if (x < x0) x0 = x
                if (x > x1) x1 = x
                if (y < y0) y0 = y
                if (y > y1) y1 = y
                sum += prob[idx]; n++
                for (dy in -1..1) {
                    val ny = y + dy
                    if (ny < 0 || ny >= ph) continue
                    for (dx in -1..1) {
                        val nx = x + dx
                        if (nx < 0 || nx >= pw) continue
                        val ni = ny * pw + nx
                        if (mask[ni] && !visited[ni]) {
                            visited[ni] = true
                            queue[tail++] = ni
                        }
                    }
                }
            }
            val bw = x1 - x0 + 1
            val bh = y1 - y0 + 1
            if (bw < MIN_BOX_SIDE || bh < MIN_BOX_SIDE) continue
            if (sum / n < BOX_THRESH) continue
            // unclip：按面积/周长外扩，把笔画框撑成整行框
            val dd = bw * bh * UNCLIP_RATIO / (2f * (bw + bh) + 1e-6f)
            boxes.add(floatArrayOf(
                (x0 - dd) * sx, (y0 - dd) * sy, (x1 + 1 + dd) * sx, (y1 + 1 + dd) * sy
            ))
        }
        return boxes
    }

    /** 一行的识别结果：文本 + 每个字的 横向比例区间 [f0, f1] */
    private class Rec(val text: String, val spans: List<FloatArray>)

    private fun recognize(crop: Bitmap): Rec {
        val e = env ?: return Rec("", emptyList())
        val r = rec ?: return Rec("", emptyList())
        val w = crop.width
        val h = crop.height
        if (w < 2 || h < 2) return Rec("", emptyList())
        var nw = max(8, (w * REC_HEIGHT.toFloat() / h).roundToInt())
        nw = min(nw, REC_MAX_W)
        nw += (4 - nw % 4) % 4
        val scaled = Bitmap.createScaledBitmap(crop, nw, REC_HEIGHT, true)
        val px = IntArray(nw * REC_HEIGHT)
        scaled.getPixels(px, 0, nw, 0, 0, nw, REC_HEIGHT)
        if (scaled !== crop) scaled.recycle()

        val plane = REC_HEIGHT * nw
        val data = FloatArray(3 * plane)
        for (y in 0 until REC_HEIGHT) {
            val row = y * nw
            for (x in 0 until nw) {
                val p = px[row + x]
                val i = y * nw + x
                data[i] = ((((p shr 16) and 0xFF) / 255f) - 0.5f) / 0.5f
                data[plane + i] = ((((p shr 8) and 0xFF) / 255f) - 0.5f) / 0.5f
                data[2 * plane + i] = (((p and 0xFF) / 255f) - 0.5f) / 0.5f
            }
        }
        val tensor = OnnxTensor.createTensor(e, FloatBuffer.wrap(data),
            longArrayOf(1, 3, REC_HEIGHT.toLong(), nw.toLong()))
        val pred = try {
            r.run(mapOf(r.inputNames.first() to tensor)).use { res ->
                val t = res[0] as OnnxTensor
                val s = t.info.shape              // [1, T, C]
                val T = s[1].toInt()
                val C = s[2].toInt()
                val arr = FloatArray(T * C)
                t.floatBuffer.get(arr)
                arr to intArrayOf(T, C)
            }
        } finally {
            tensor.close()
        }
        val flat = pred.first
        val T = pred.second[0]
        val C = pred.second[1]
        val dict = chars ?: return Rec("", emptyList())

        fun argmax(off: Int): Int {
            var best = 0
            var bv = flat[off]
            for (c in 1 until C) {
                val v = flat[off + c]
                if (v > bv) { bv = v; best = c }
            }
            return best
        }

        // CTC 去重：相邻同类合并成一个字，同时记下时间步区间
        val sb = StringBuilder()
        val spans = ArrayList<FloatArray>()
        var prev = -1
        var t0 = 0
        var t1 = 0
        fun flush(c: Int) {
            if (c == 0) return
            val ch = if (c < dict.size) dict[c] else ""
            // 空白字符不进结果：spans 与文本必须严格 1:1，否则字和框会错位
            if (ch.isBlank()) return
            sb.append(foldWidth(ch[0]))
            spans.add(floatArrayOf(t0.toFloat() / T, t1.toFloat() / T))
        }
        for (t in 0 until T) {
            val c = argmax(t * C)
            if (c == prev) { t1 = t + 1; continue }
            flush(prev)
            prev = c
            t0 = t
            t1 = t + 1
        }
        flush(prev)
        return Rec(sb.toString(), spans)
    }

    // ------------------------------------------------------------------ 对外

    /**
     * 给一页补 OCR 结果。
     *
     * @param page 已经由 PDFBox 读出的页面（可能是空的 lines）
     * @param bitmap 该页渲染好的位图，坐标按 page.width / bitmap.width 换算
     */
    fun readPage(page: PageText, bitmap: Bitmap): List<Line> {
        val bw = bitmap.width
        val bh = bitmap.height
        // 检测在缩小图上跑（快），识别回到原图裁（准）
        val scale = min(1f, DET_LIMIT / max(bw, bh).toFloat())
        val small = if (scale < 1f) {
            Bitmap.createScaledBitmap(
                bitmap,
                max(1, (bw * scale).roundToInt()),
                max(1, (bh * scale).roundToInt()),
                true
            )
        } else bitmap
        val boxes = try {
            detectBoxes(small)
        } finally {
            if (small !== bitmap) small.recycle()
        }
        if (boxes.isEmpty()) return emptyList()

        val inv = 1f / scale                      // 检测图 → 原图
        val scaleX = page.width / bw              // 原图 → 页面点
        val scaleY = page.height / bh

        class Item(val text: String, val spans: List<FloatArray>,
                   val x0: Float, val y0: Float, val x1: Float, val y1: Float)

        val items = ArrayList<Item>()
        for (b in boxes) {
            var X0 = (b[0] * inv).toInt()
            var Y0 = (b[1] * inv).toInt()
            var X1 = (b[2] * inv).toInt() + 1
            var Y1 = (b[3] * inv).toInt() + 1
            // 检测框常常比字形窄一点，按字高比例补边：识别看得全，打码也盖得住
            val h = (Y1 - Y0).coerceAtLeast(1)
            // 0.45 时末位数字常被切掉半个，放宽到 0.85（与 Windows 端 PAD_RATIO 对齐）
            val padX = max(2, (h * PAD_RATIO).roundToInt())
            val padY = max(2, (h * 0.20f).roundToInt())
            val cx0 = (X0 - padX).coerceAtLeast(0)
            val cy0 = (Y0 - padY).coerceAtLeast(0)
            val cx1 = (X1 + padX).coerceAtMost(bw)
            val cy1 = (Y1 + padY).coerceAtMost(bh)
            if (cx1 - cx0 < 4 || cy1 - cy0 < 4) continue
            val crop = Bitmap.createBitmap(bitmap, cx0, cy0, cx1 - cx0, cy1 - cy0)
            val rec = try {
                recognize(crop)
            } finally {
                crop.recycle()
            }
            if (rec.text.isBlank()) continue
            items.add(Item(
                rec.text, rec.spans,
                (X0 - padX) * scaleX, (Y0 - padY) * scaleY,
                (X1 + padX) * scaleX, (Y1 + padY) * scaleY
            ))
        }
        if (items.isEmpty()) return emptyList()

        // 按纵向中心分行，与文字层路径的口径一致
        items.sortWith(compareBy({ (it.y0 + it.y1) / 2f }, { it.x0 }))
        val groups = ArrayList<MutableList<Item>>()
        val centers = ArrayList<Float>()
        val heights = ArrayList<Float>()
        for (it in items) {
            val cy = (it.y0 + it.y1) / 2f
            val hh = it.y1 - it.y0
            var hit = -1
            for (g in groups.indices) {
                if (abs(centers[g] - cy) <= max(2f, max(heights[g], hh) * 0.42f)) { hit = g; break }
            }
            if (hit < 0) {
                groups.add(mutableListOf(it))
                centers.add(cy)
                heights.add(hh)
            } else {
                groups[hit].add(it)
                heights[hit] = max(heights[hit], hh)
            }
        }

        val out = ArrayList<Line>()
        for (g in groups) {
            g.sortBy { it.x0 }
            val sb = StringBuilder()
            val boxesOut = ArrayList<CharBox?>()
            var prevX1 = Float.NaN
            for (it in g) {
                val hgt = it.y1 - it.y0
                if (!prevX1.isNaN() && it.x0 - prevX1 > max(0.9f, hgt * 0.42f)) {
                    sb.append(' ')
                    boxesOut.add(null)
                }
                val width = it.x1 - it.x0
                // 同一框内的字矩形首尾相接：CTC 区间是估计值，留缝会露白
                val n = it.spans.size
                // 单个字的区间容易偏窄，给一个按字高算的下限
                val minW = min(hgt * 0.42f, width * 0.6f)
                for (k in 0 until n) {
                    val f0 = it.spans[k][0]
                    val f1 = it.spans[k][1]
                    var b0 = if (k > 0) (it.spans[k - 1][1] + f0) / 2f else f0
                    var b1 = if (k + 1 < n) (f1 + it.spans[k + 1][0]) / 2f else f1
                    if (b1 <= b0) { b0 = f0; b1 = f1 }
                    var cx0 = it.x0 + width * b0
                    var cx1 = it.x0 + width * b1
                    if (cx1 - cx0 < minW) {
                        val mid = (cx0 + cx1) / 2f
                        cx0 = mid - minW / 2f
                        cx1 = mid + minW / 2f
                    }
                    val ch = it.text.getOrNull(k) ?: continue
                    sb.append(ch)
                    boxesOut.add(CharBox(ch, Rect(cx0, it.y0, cx1, it.y1)))
                }
                prevX1 = it.x1
            }
            if (sb.isNotBlank()) out.add(Line(sb.toString(), boxesOut))
        }
        return out
    }

    /**
     * 串起「哪些页要 OCR → 渲染 → 识别」。
     *
     * 判据与桌面端一致：这页几乎没有字，或者字很少但整页被图片盖住。
     * 任何一页出错都只跳过该页，不影响其它页和整体流程。
     */
    fun augment(
        ctx: Context,
        src: File,
        pages: List<PageText>,
        onProgress: (Int) -> Unit = {}
    ): List<PageText> {
        if (!ensure(ctx)) return pages
        val need = pages.filter { it.lines.isEmpty() }
        if (need.isEmpty()) return pages
        val result = pages.toMutableList()
        var pfd: ParcelFileDescriptor? = null
        var renderer: PdfRenderer? = null
        try {
            pfd = ParcelFileDescriptor.open(src, ParcelFileDescriptor.MODE_READ_ONLY)
            renderer = PdfRenderer(pfd)
            for ((i, p) in need.withIndex()) {
                onProgress(i + 1)
                if (p.index < 0 || p.index >= renderer.pageCount) continue
                val bmp = try {
                    renderer.openPage(p.index).use { pg ->
                        val scale = RENDER_DPI / 72f
                        val w = max(1, (pg.width * scale).roundToInt())
                        val h = max(1, (pg.height * scale).roundToInt())
                        val b = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                        // PdfRenderer 不铺底色，透明区会被当成黑色，先填白
                        Canvas(b).drawColor(Color.WHITE)
                        pg.render(b, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                        b
                    }
                } catch (_: Throwable) {
                    null
                } ?: continue
                val lines = try {
                    readPage(p, bmp)
                } catch (_: Throwable) {
                    emptyList()
                } finally {
                    bmp.recycle()
                }
                if (lines.isNotEmpty()) result[p.index] = p.copy(lines = lines)
            }
        } catch (_: Throwable) {
            // 渲染不了就当没有 OCR，保持原样
        } finally {
            try { renderer?.close() } catch (_: Throwable) {}
            try { pfd?.close() } catch (_: Throwable) {}
        }
        return result
    }
}
