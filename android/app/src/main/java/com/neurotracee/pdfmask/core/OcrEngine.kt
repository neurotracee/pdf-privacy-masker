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
    private const val UNCLIP_MAX_RATIO = 0.12f
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

    /** 最近一次初始化失败的原因，供界面如实提示（空串表示没失败过） */
    @Volatile var lastError: String = ""
        private set

    /**
     * 最近一次 [augment] 的体检结果：渲染了几页、det 出几个框、识别出几行。
     *
     * 0 检出的三种情况必须能分开：「OCR 没跑起来」「跑了但一个字没认出来」
     * 「认出来了但规则没命中」。只报「没有识别到隐私信息」，用户和排查的人
     * 都只能靠猜。
     */
    @Volatile var lastStats: String = ""
        private set

    private var statPages = 0
    private var statBoxes = 0
    private var statLines = 0
    private var statFail = ""
    private var statPeak = 0f
    private var statFallback = 0
    private var statSample = ""

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
            // 记下原因：模型解压失败、内存不足、ABI 不匹配都会落到这里。
            // 以前是纯静默返回 false，用户只看到「没有识别到隐私信息」，
            // 分不清是「真没有」还是「OCR 根本没跑起来」。
            lastError = t.javaClass.simpleName + ": " + (t.message ?: "")
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
        var peak = 0f
        for (i in 0 until ph * pw) {
            val v = prob[i]
            if (v > peak) peak = v
            if (v > DET_THRESH) { mask[i] = true; any = true }
        }
        // 概率图峰值是判断「模型到底有没有被激活」的唯一直接证据：
        // 整页 0.02 说明喂进去的图模型不认识（输入/前处理错了），
        // 0.9 以上说明检测正常，问题出在后面的过滤或识别环节。
        if (peak > statPeak) statPeak = peak
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
            // unclip：按面积/周长外扩，把笔画框撑成整行框。两个方向需求正好相反：
            //   · 横向必须留够余量，否则行首行尾的字被切掉半个
            //     （「出生日期」读成「出生期」、末尾的「日」丢掉）；
            //   · 纵向绝不能大，长行按公式会扩到 0.8 倍行高，把上下相邻行
            //     吞进裁剪框，识别出来是「楼2单元…楼2执行人…」这种半截串。
            // 所以横向照公式扩，纵向只对细长行（bw >= 6*bh）压到 0.12 倍行高。
            // 与 Windows 端 pdfmask_ocr._detect 逐行对齐，两端同图同结果。
            val d = bw * bh * UNCLIP_RATIO / (2f * (bw + bh) + 1e-6f)
            val dx = d
            val dy = if (bw >= 6 * bh) min(d, bh * UNCLIP_MAX_RATIO) else d
            // 后两个值：外扩**之前**的上下边（就是笔画本身）。外扩是给识别留余量的，
            // 里面已经含了相邻行；字高只能取紧框，否则打码块会盖到上一行。
            boxes.add(floatArrayOf(
                (x0 - dx) * sx, (y0 - dy) * sy, (x1 + 1 + dx) * sx, (y1 + 1 + dy) * sy,
                y0 * sy, (y1 + 1) * sy
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
        val ids = IntArray(T) { argmax(it * C) }
        for (g in ctcGroups(ids)) {
            val c = g[0]
            val ch = if (c < dict.size) dict[c] else ""
            // 空白字符不进结果：spans 与文本必须严格 1:1，否则字和框会错位
            if (ch.isBlank()) continue
            sb.append(foldWidth(ch[0]))
            spans.add(floatArrayOf(g[1].toFloat() / T, g[2].toFloat() / T))
        }
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
        // 灰字 + 泛黄底 / 一边亮一边暗的扫描页，先拉黑白场、除掉光照再送进网络。
        // 不做这一步时，检测头对这类页面几乎不激活（实测整页 0 检出），
        // 与 Windows 端 OcrEngine 的 normalize_contrast / flatten_illumination 同源。
        //
        // 前处理只是「锦上添花」，绝不能让整页作废：以前它抛异常会一路冒到
        // augment 的 catch，整页直接判空，界面上还只显示「没有识别到隐私信息」。
        val work = try {
            OcrPreprocess.normalize(bitmap)
        } catch (t: Throwable) {
            if (statFail.isBlank()) statFail = "preprocess " + t.javaClass.simpleName
            null
        } ?: bitmap
        // 扫描件 / 拍照件几乎都带零点几度的歪，歪着送进检测网络会整行漏掉。
        // 与 Windows 端一样：先摆正再检测，最后把框转回原来的页面坐标。
        val skew = try { OcrPreprocess.estimateSkew(work) } catch (t: Throwable) { 0f }
        val aligned = if (skew != 0f) OcrPreprocess.rotate(work, skew) else work
        var lines: List<Line>
        try {
            lines = readPageInner(page, aligned, bw, bh, skew)
        } finally {
            if (aligned !== work) aligned.recycle()
            if (work !== bitmap) work.recycle()
        }
        // 加了前处理反而一个字都没认出来 → 退回原图再跑一次。
        // 前处理的判据是按页自适应的（对比度、光照），遇到「整页本来偏暗」
        // 或「彩色底纹」这类页面有可能把它拉坏；宁可多花一次检测，
        // 也不能因为一道可选的增强把整页判死。
        if (lines.isEmpty() && work !== bitmap) {
            statFallback++
            lines = readPageInner(page, bitmap, bw, bh, 0f)
        }
        return lines
    }

    /**
     * 一页的检测 + 识别，产出与文字层路径完全同构的 [Line]。
     *
     * 坐标有三层，必须分清（以前混在一起，倾斜页上的框就是从这里开始偏的）：
     *  - 检测图坐标：缩小图上的像素，box 里还带 det 的紧框上下边；
     *  - 摆正图坐标（aligned）：`bitmap` 本身，裁剪、识别、量墨迹都在这一层；
     *  - 原图/页面坐标：按 [skew] 逆变换回去，再乘页面缩放，才是真正要打码的位置。
     *
     * 裁剪一定要在**摆正图**上按**摆正图坐标**取；一旦先转成原图坐标再去裁，
     * 歪 1 度、离页心 500px 就差出十几像素——正好差半行，识别会读到邻行去。
     */
    private fun readPageInner(page: PageText, bitmap: Bitmap, bw: Int, bh: Int,
                              skew: Float = 0f): List<Line> {
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
        statBoxes += boxes.size
        if (boxes.isEmpty()) return emptyList()

        val inv = 1f / scale                      // 检测图 → 摆正图
        val scaleX = page.width / bw              // 摆正图 → 页面点
        val scaleY = page.height / bh
        val map = AlignMap(bw, bh, skew, page.width, page.height)
        fun toPage(r: Rect): Rect = map.toPage(r)

        // chars 是**页面坐标**下的逐字矩形；tol 是外扩框高度，只用于「同一行」的聚类容差
        class Item(val text: String, val chars: List<Rect>, val tol: Float) {
            fun band(): Rect {
                var r = chars[0]
                for (k in 1 until chars.size) r = r.union(chars[k])
                return r
            }
        }

        val items = ArrayList<Item>()
        for (b in boxes) {
            val X0 = (b[0] * inv).toInt().coerceIn(0, bw - 1)
            val Y0 = (b[1] * inv).toInt().coerceIn(0, bh - 1)
            val X1 = ((b[2] * inv).toInt() + 1).coerceIn(X0 + 1, bw)
            val Y1 = ((b[3] * inv).toInt() + 1).coerceIn(Y0 + 1, bh)
            // 检测框常常比字形窄一点，按字高比例补边：识别看得全，打码也盖得住
            val h = (Y1 - Y0).coerceAtLeast(1)
            // 0.45 时末位数字常被切掉半个，放宽到 0.85（与 Windows 端 PAD_RATIO 对齐）
            val padX = max(2, (h * PAD_RATIO).roundToInt())
            val padY = max(2, (h * 0.20f).roundToInt())
            val cx0 = (X0 - padX).coerceAtLeast(0)
            val cy0 = (Y0 - padY).coerceAtLeast(0)
            val cx1 = (X1 + padX).coerceAtMost(bw)
            val cy1 = (Y1 + padY).coerceAtMost(bh)
            val cw = cx1 - cx0
            val chh = cy1 - cy0
            if (cw < 6 || chh < 6) continue

            val crop = Bitmap.createBitmap(bitmap, cx0, cy0, cw, chh)
            val lum = IntArray(cw * chh)
            val rec: Rec
            try {
                crop.getPixels(lum, 0, cw, 0, 0, cw, chh)
                for (i in lum.indices) {
                    val c = lum[i]
                    lum[i] = ((((c shr 16) and 0xFF) * 299 +
                        ((c shr 8) and 0xFF) * 587 +
                        (c and 0xFF) * 114) / 1000)
                }
                rec = recognize(crop)
            } finally {
                crop.recycle()
            }
            val n = min(rec.text.length, rec.spans.size)
            if (n <= 0) continue

            // 字形的上下边 = 概率图里外扩前那一段（笔画本身）；再按墨迹实测校正，
            // 灰字/细笔画上概率图会偏矮，汉字的底下一横最容易漏。
            val hintTop = (b[4] * inv - cy0)
            val hintBottom = max(hintTop + 1f, (b[5] * inv - cy0))
            val split = CharLayout.split(
                lum, cw, chh, rec.text.substring(0, n), rec.spans.subList(0, n),
                hintTop, hintBottom,
                (X0 - cx0).toFloat(), (X1 - cx0).toFloat()
            )
            val top = (cy0 + split.top).toFloat()
            val bot = (cy0 + split.bottom).toFloat()
            val chars = ArrayList<Rect>(n)
            for (k in 0 until n) {
                chars.add(toPage(Rect(cx0 + split.xs[k], top, cx0 + split.xs[k + 1], bot)))
            }
            items.add(Item(rec.text.substring(0, n), chars, chh * scaleY))
        }
        if (items.isEmpty()) return emptyList()

        // 按本页行距封顶：墨迹实测后一般不会超标，这里只兜「两条线粘成一段」这类极端情况。
        // 90% 行距几乎不会切到字，却能把误吞的邻行挡在外面。
        run {
            val cys = items.map { val r = it.band(); (r.y0 + r.y1) / 2f }.sorted()
            val gaps = ArrayList<Float>()
            for (k in 1 until cys.size) {
                val g = cys[k] - cys[k - 1]
                if (g > 1f) gaps.add(g)
            }
            if (gaps.isNotEmpty()) {
                gaps.sort()
                val pitch = gaps[gaps.size / 2]
                val cap = pitch * 0.92f
                for (idx in items.indices) {
                    val band = items[idx].band()
                    if (band.height > cap) {
                        val c = (band.y0 + band.y1) / 2f
                        items[idx] = Item(
                            items[idx].text,
                            items[idx].chars.map { Rect(it.x0, c - cap / 2f, it.x1, c + cap / 2f) },
                            items[idx].tol
                        )
                    }
                }
            }
        }

        // 按纵向中心分行，与文字层路径的口径一致
        items.sortWith(compareBy({ val r = it.band(); (r.y0 + r.y1) / 2f }, { it.band().x0 }))
        val groups = ArrayList<MutableList<Item>>()
        val centers = ArrayList<Float>()
        val heights = ArrayList<Float>()
        for (it in items) {
            val r = it.band()
            val cy = (r.y0 + r.y1) / 2f
            var hit = -1
            for (g in groups.indices) {
                if (abs(centers[g] - cy) <= max(2f, max(heights[g], it.tol) * 0.30f)) { hit = g; break }
            }
            if (hit < 0) {
                groups.add(mutableListOf(it))
                centers.add(cy)
                heights.add(it.tol)
            } else {
                groups[hit].add(it)
                heights[hit] = max(heights[hit], it.tol)
            }
        }

        // 行带的上下各留一点抗锯齿余量，但绝不超过与邻行之间空隙的 45%，
        // 这样既不会留下一条灰边，也不会把上一行/下一行的字一起糊掉。
        fun bandOf(g: List<Item>): Rect {
            var r = g[0].band()
            for (k in 1 until g.size) r = r.union(g[k].band())
            return r
        }
        val order = groups.indices.sortedBy { centers[it] }
        val bands = groups.map { bandOf(it) }
        val padTop = FloatArray(groups.size)
        val padBot = FloatArray(groups.size)
        for ((oi, gi) in order.withIndex()) {
            val bnd = bands[gi]
            val bh2 = max(1f, bnd.height)
            val prev = if (oi > 0) bands[order[oi - 1]] else null
            val next = if (oi + 1 < order.size) bands[order[oi + 1]] else null
            val gapT = if (prev != null) max(0f, bnd.y0 - prev.y1) else bh2
            val gapB = if (next != null) max(0f, next.y0 - bnd.y1) else bh2
            padTop[gi] = max(0.6f, min(bh2 * 0.12f, gapT * 0.45f))
            padBot[gi] = max(0.6f, min(bh2 * 0.12f, gapB * 0.45f))
        }

        val out = ArrayList<Line>()
        for ((gi, g) in groups.withIndex()) {
            g.sortBy { it.band().x0 }
            val sb = StringBuilder()
            val boxesOut = ArrayList<CharBox?>()
            var prevX1 = Float.NaN
            var prevH = bands[gi].height
            for (it in g) {
                val band = it.band()
                val hgt = max(1f, band.height)
                // 两段之间空出半个字宽以上，才算一个空格（表格式排版常见）
                if (!prevX1.isNaN() && band.x0 - prevX1 > max(0.9f, min(prevH, hgt) * 0.42f)) {
                    sb.append(' ')
                    boxesOut.add(null)
                }
                for ((k, ch) in it.text.withIndex()) {
                    val r = it.chars[k]
                    sb.append(ch)
                    boxesOut.add(
                        CharBox(
                            ch,
                            Rect(r.x0, r.y0 - padTop[gi], r.x1, r.y1 + padBot[gi])
                        )
                    )
                }
                prevX1 = band.x1
                prevH = hgt
            }
            if (sb.isNotBlank()) out.add(Line(sb.toString(), boxesOut))
        }
        statLines += out.size
        if (statSample.isBlank() && out.isNotEmpty()) statSample = out.first().text
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
        statPages = 0
        statBoxes = 0
        statLines = 0
        statFail = ""
        statPeak = 0f
        statFallback = 0
        statSample = ""
        if (!ensure(ctx)) {
            lastStats = "模型未就绪"
            return pages
        }
        val need = pages.filter { it.lines.isEmpty() }
        if (need.isEmpty()) {
            lastStats = "无需 OCR"
            return pages
        }
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
                } catch (t: Throwable) {
                    noteFail("render", t)
                    null
                } ?: continue
                statPages++
                val lines = try {
                    readPage(p, bmp)
                } catch (t: Throwable) {
                    noteFail("ocr", t)
                    emptyList()
                } finally {
                    bmp.recycle()
                }
                if (lines.isNotEmpty()) result[p.index] = p.copy(lines = lines)
            }
        } catch (t: Throwable) {
            // 渲染不了就当没有 OCR，保持原样——但原因必须留下来，不能静默
            noteFail("open", t)
        } finally {
            try { renderer?.close() } catch (_: Throwable) {}
            try { pfd?.close() } catch (_: Throwable) {}
        }
        lastStats = "渲染 $statPages 页 · 检测框 $statBoxes 个 · 认出文字行 $statLines 行" +
            (if (statPages > 0) " · 峰值 ${String.format(java.util.Locale.US, "%.2f", statPeak)}" else "") +
            (if (statFallback > 0) " · 退回原图 $statFallback 页" else "") +
            (if (statSample.isNotBlank()) " · 首行「${statSample.take(16)}」" else "") +
            (if (statFail.isNotBlank()) " · 中断：$statFail" else "")
        // 打进 logcat，插上数据线就能看到这一份到底是「没渲染」「没出框」还是「没认出字」
        android.util.Log.i("PdfMaskOcr", lastStats)
        return result
    }

    /** 记下第一处异常：真正吞掉整份文档的，往往是内存不足而不是网络或模型 */
    private fun noteFail(where: String, t: Throwable) {
        if (statFail.isNotBlank()) return
        statFail = where + " " + t.javaClass.simpleName
        if (lastError.isBlank()) lastError = statFail + (t.message?.let { " ($it)" } ?: "")
        android.util.Log.e("PdfMaskOcr", "OCR 中断于 $where", t)
    }
}

/**
 * CTC 贪心解码：把「每帧的 argmax 字符索引」压成 `[字符索引, 起始帧, 结束帧)`。
 *
 * 抽成纯函数是为了能被单元测试覆盖。这里曾经出过一个把整份扫描件打成 0 检出的
 * 事故：CTC 的 blank 是 0，而「还没有上一个字符」用 -1 当哨兵，若把 -1 也送进
 * 字典查表就是 `ArrayIndexOutOfBoundsException: length=6625; index=-1`，
 * 异常又被上层 catch 吞成「这页没有文字」，界面上只显示「没有识别到隐私信息」。
 * 所以这里只收 > 0 的索引，0 与 -1 一律跳过。
 */
internal fun ctcGroups(ids: IntArray): List<IntArray> {
    val out = ArrayList<IntArray>()
    var prev = -1
    var t0 = 0
    for (t in ids.indices) {
        val c = ids[t]
        if (c == prev) continue
        if (prev > 0) out.add(intArrayOf(prev, t0, t))
        prev = c
        t0 = t
    }
    if (prev > 0) out.add(intArrayOf(prev, t0, ids.size))
    return out
}
