package com.neurotracee.pdfmask

import android.app.Application
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.provider.DocumentsContract
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.neurotracee.pdfmask.core.Detector
import com.neurotracee.pdfmask.core.Finding
import com.neurotracee.pdfmask.core.Kind
import com.neurotracee.pdfmask.core.MaskSummary
import com.neurotracee.pdfmask.core.PageText
import com.neurotracee.pdfmask.core.PdfMasker
import com.neurotracee.pdfmask.core.OcrEngine
import com.neurotracee.pdfmask.core.PdfTextExtractor
import com.neurotracee.pdfmask.core.Rect
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

enum class Stage { HOME, LOADING, READY, MASKING, DONE }

/** 一次成功的打开：名字、缓存文件、页面文字、命中列表、文档身份 */
private data class Loaded(
    val name: String,
    val file: File,
    val pages: List<PageText>,
    val findings: List<Finding>,
    val key: String
)

class AppViewModel(app: Application) : AndroidViewModel(app) {

    var stage by mutableStateOf(Stage.HOME)
        private set
    var docName by mutableStateOf("")
        private set
    var docFile by mutableStateOf<File?>(null)
        private set
    var pages by mutableStateOf<List<PageText>>(emptyList())
        private set
    var findings by mutableStateOf<List<Finding>>(emptyList())
        private set
    var selected by mutableStateOf<Set<Int>>(emptySet())
        private set
    var current by mutableStateOf(0)
        private set
    var progress by mutableStateOf(0f)
        private set
    var message by mutableStateOf<String?>(null)
        private set
    var summary by mutableStateOf<MaskSummary?>(null)
        private set
    var savedName by mutableStateOf("")
        private set

    /** 保存目录记忆（SAF 授权过的树 Uri） */
    var saveTreeUri by mutableStateOf<String?>(null)
        private set

    private val thumbs = mutableStateMapOf<Int, Bitmap>()

    /** 手动框选的 id 从 -1 往下走，避开自动识别用的非负 id */
    private var nextManualId = -1

    /** 本次打开时成功用 OCR 读出文字的扫描页数（用于提示文案） */
    var ocrPages = 0
        private set

    /**
     * 本次 OCR 的体检数字（渲染几页 / 出几个框 / 认出几行）。
     *
     * 只在「一处都没检出来」时显示在标题下面，正常情况界面上不出现，
     * 这样万一哪天又整份 0 检出，截图本身就带着线索，不用再靠猜。
     */
    var ocrStats by mutableStateOf("")
        private set

    fun toast(msg: String) {
        message = msg
    }

    /**
     * 橡皮擦：只记「页面 pt 坐标的小矩形」，打码时把这些小块从打码范围里**减掉**。
     * 不删除任何标记框，也不会越过矩形边界——例如只恢复「公民身份证号：」
     * 这几个字，后面的号码仍保持打码。
     */
    var erasers by mutableStateOf<Map<Int, List<Rect>>>(emptyMap())
        private set

    /**
     * 当前文档身份（文件名 + 字节数）。换文件时 [load] 会换掉它，
     * 界面据此把「编辑模式」等临时状态归零，不会把上一份的模式带过来。
     */
    var docKey by mutableStateOf("")
        private set

    /** 上一份文档的编辑快照：只有勾了「保留上次编辑/橡皮擦状态」才会回填 */
    private var lastKey: String = ""
    private var lastErasers: Map<Int, List<Rect>> = emptyMap()
    private var lastManuals: List<Pair<Int, Rect>> = emptyList()
    private var lastDeselected: Set<String> = emptySet()

    /** 自动识别项的身份：同一份文档重新识别后 id 会重排，用内容 + 位置更稳 */
    private fun findingKey(f: Finding): String =
        "${f.page}|${f.type}|${f.text}|${f.rect.x0.toInt()}|${f.rect.y0.toInt()}"

    /** 离开/换文件前把这次的编辑留下来（不落盘，只活在本次进程里） */
    private fun snapshot() {
        if (findings.isEmpty() && erasers.isEmpty()) return
        lastKey = docKey
        lastErasers = erasers
        lastManuals = findings.filter { it.type == Kind.MANUAL }.map { it.page to it.rect }
        lastDeselected = findings
            .filter { it.type != Kind.MANUAL && it.id !in selected }
            .map { findingKey(it) }
            .toSet()
    }

    /**
     * 恢复到「刚识别完」的初始状态：擦除、手动框、取消掉的勾选全部复位。
     * @return 是否真的改动过（用于提示文案，没改就不说「已恢复」）
     */
    fun restoreDefaults(): Boolean {
        val hadEraser = erasers.isNotEmpty()
        val hadManual = findings.any { it.type == Kind.MANUAL }
        val hadOff = findings.any { it.type != Kind.MANUAL && it.id !in selected }
        if (!hadEraser && !hadManual && !hadOff) return false
        erasers = emptyMap()
        findings = findings.filter { it.type != Kind.MANUAL }
        selected = findings.filter { !it.suspect }.map { it.id }.toSet()
        return true
    }

    fun addEraser(page: Int, rect: Rect) {
        erasers = erasers + (page to (erasers[page].orEmpty() + rect))
    }

    fun undoEraser(page: Int) {
        val list = erasers[page].orEmpty()
        if (list.isNotEmpty()) erasers = erasers + (page to list.dropLast(1))
    }

    /** 加一个手动框选区域（rect 为页面 pt 坐标） */
    fun addManual(page: Int, rect: Rect): Int {
        val id = nextManualId--
        val f = Finding(
            page = page,
            type = Kind.MANUAL,
            text = "",
            rect = rect,
            note = tr("手动框选", "Manual"),
            suspect = false,
            id = id
        )
        findings = findings + f
        selected = selected + id
        return id
    }

    /** 删除某一条（含手动框选） */
    fun removeFinding(id: Int) {
        findings = findings.filter { it.id != id }
        selected = selected - id
    }

    fun clearManual(page: Int? = null) {
        val drop = findings.filter {
            it.type == Kind.MANUAL && (page == null || it.page == page)
        }.map { it.id }.toSet()
        if (drop.isEmpty()) return
        findings = findings.filter { it.id !in drop }
        selected = selected - drop
    }

    val manualCount: Int get() = findings.count { it.type == Kind.MANUAL }

    /** 建议的输出文件名 */
    fun suggestOutName(): String {
        val base = docName.substringBeforeLast('.', docName)
        return (if (base.isBlank()) tr("文档", "document") else base) +
            tr("_已打码.pdf", "_masked.pdf")
    }

    fun cancelMasking() {
        if (stage == Stage.MASKING) stage = Stage.READY
    }

    fun clearMessage() {
        message = null
    }

    fun thumb(page: Int): Bitmap? = thumbs[page]

    fun load(uri: Uri) {
        stage = Stage.LOADING
        progress = 0f
        thumbs.clear()
        // 换文档先归零：以前这里不清 erasers，上一份划过的擦除框会原地
        // 套到新文档的同一坐标上，看起来像「默认继承了上次的编辑」。
        erasers = emptyMap()
        nextManualId = -1
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    val name = queryName(ctx, uri) ?: (tr("文档", "document") + ".pdf")
                    val tmp = File(ctx.cacheDir, "src_" + System.currentTimeMillis() + ".pdf")
                    ctx.contentResolver.openInputStream(uri)?.use { ins ->
                        FileOutputStream(tmp).use { outs -> ins.copyTo(outs) }
                    } ?: error(tr("无法读取这个文件", "Cannot read this file"))
                    // 扫描件 / 拍照件没有文字层，PDFBox 读不出任何字形；
                    // 这类页面交给端侧 OCR 补出「文字 + 每字矩形」，后续规则完全复用
                    val rawText = PdfTextExtractor.extract(ctx, tmp)
                    val pageText = if (rawText.any { it.lines.isEmpty() })
                        OcrEngine.augment(ctx, tmp, rawText) else rawText
                    ocrPages = rawText.indices.count {
                        rawText[it].lines.isEmpty() && pageText[it].lines.isNotEmpty()
                    }
                    val found = Detector.detect(pageText)
                    Loaded(name, tmp, pageText, found, "$name|${tmp.length()}")
                }
            }.onSuccess { r ->
                val key = r.key
                docName = r.name
                docFile = r.file
                pages = r.pages
                findings = r.findings
                selected = r.findings.filter { !it.suspect }.map { it.id }.toSet()
                summary = null
                savedName = ""
                current = 0
                docKey = key
                // 默认永远是「刚识别完」的干净状态；只有用户显式勾了
                // 「保留上次编辑/橡皮擦状态」、且确实是同一份文档，才把上次的编辑接回来。
                if (AppPrefs.keepLastEdit && lastKey == key) {
                    erasers = lastErasers.filterKeys { it in pages.indices }
                    for ((p, rect) in lastManuals) if (p in pages.indices) addManual(p, rect)
                    if (lastDeselected.isNotEmpty()) {
                        val off = findings.filter { findingKey(it) in lastDeselected }.map { it.id }
                        selected = selected - off.toSet()
                    }
                    toast(tr("已恢复上次的编辑与擦除", "Restored your last edits"))
                }
                stage = Stage.READY
                ocrStats = OcrEngine.lastStats.let {
                    if (it == "无需 OCR" || it == "模型未就绪") "" else it
                }
                if (r.findings.isEmpty()) {
                    val ocrErr = OcrEngine.lastError
                    val stats = OcrEngine.lastStats
                    toast(
                        when {
                            // 有扫描页、但 OCR 没跑起来：必须说清楚，不能报「没有隐私信息」
                            ocrPages == 0 && ocrErr.isNotBlank() ->
                                tr("这一份是扫描件，需要本机 OCR 才能识别，但 OCR 没能完成（" +
                                        ocrErr + "）。" + stats +
                                        " 请确认安装的是完整安装包，重启应用再试。",
                                    "This is a scanned document and needs on-device OCR, but OCR did not finish (" +
                                        ocrErr + "). " + stats +
                                        " Make sure you installed the full package and reopen the app.")
                            ocrPages > 0 -> tr(
                                "扫描页已用本机 OCR 识别（" + stats + "），未发现敏感信息；可在预览上手动框选补充",
                                "Scanned pages were read with on-device OCR (" + stats +
                                    ") and nothing was found. Add boxes manually if needed."
                            )
                            // 跑了 OCR 却一行字都没认出来：把体检数字摊开，别再让人猜
                            stats.isNotBlank() && stats != "无需 OCR" -> tr(
                                "本机 OCR 跑完了（" + stats + "），没有认出文字，可在预览上手动框选",
                                "On-device OCR finished (" + stats +
                                    ") but read no text. You can drag boxes on the preview."
                            )
                            else -> tr(
                                "没有识别到隐私信息，可以在预览上手动框选",
                                "Nothing detected. You can drag boxes on the preview."
                            )
                        }
                    )
                }
            }.onFailure {
                docKey = ""
                erasers = emptyMap()
                stage = Stage.HOME
                toast(tr("打开失败：", "Open failed: ") + (it.message ?: tr("未知错误", "unknown error")))
            }
        }
    }

    fun toggle(id: Int) {
        selected = if (id in selected) selected - id else selected + id
    }

    fun selectAll(on: Boolean) {
        selected = if (on) findings.map { it.id }.toSet() else emptySet()
    }

    fun goPage(page: Int) {
        current = page.coerceIn(0, (pages.size - 1).coerceAtLeast(0))
    }

    fun reset() {
        // 先把这次的编辑记下来（勾了「保留上次编辑」的话，下次导入同一份还能接回来）
        snapshot()
        docFile?.let { runCatching { it.delete() } }
        stage = Stage.HOME
        docName = ""
        docKey = ""
        docFile = null
        pages = emptyList()
        findings = emptyList()
        selected = emptySet()
        erasers = emptyMap()
        nextManualId = -1
        thumbs.clear()
        summary = null
        current = 0
    }

    /** 渲染某一页缩略图（用于预览） */
    fun ensureThumb(page: Int, maxWidthPx: Int) {
        if (thumbs.containsKey(page)) return
        val f = docFile ?: return
        viewModelScope.launch {
            val bmp = withContext(Dispatchers.IO) { renderPage(f, page, maxWidthPx) }
            if (bmp != null) thumbs[page] = bmp
        }
    }

    fun writeTo(uri: Uri, onDone: (String) -> Unit) {
        val f = docFile ?: return
        stage = Stage.MASKING
        progress = 0f
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    val out = ctx.contentResolver.openOutputStream(uri)
                        ?: error(tr("无法写入这个位置", "Cannot write to this location"))
                    out.use { os ->
                        PdfMasker.mask(
                            ctx, f, findings.filter { it.id in selected }, os,
                            erasers = erasers
                        ) { p -> progress = p }
                    }
                    queryName(ctx, uri) ?: (tr("已打码", "masked") + ".pdf")
                }
            }.onSuccess { name ->
                savedName = name
                stage = Stage.DONE
                onDone(name)
            }.onFailure {
                stage = Stage.READY
                toast(tr("生成失败：", "Failed: ") + (it.message ?: tr("未知错误", "unknown error")))
            }
        }
    }

    fun copyTo(uri: Uri) {
        val f = docFile ?: return
        stage = Stage.MASKING
        progress = 0f
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    // 需要一个源文件：先写到缓存，再复制到用户选的位置
                    val tmp = File(ctx.cacheDir, "rerun_" + System.currentTimeMillis() + ".pdf")
                    FileOutputStream(tmp).use { os ->
                        PdfMasker.mask(
                            ctx, f, findings.filter { it.id in selected }, os,
                            erasers = erasers
                        ) { p -> progress = p }
                    }
                    ctx.contentResolver.openOutputStream(uri)?.use { os ->
                        tmp.inputStream().use { it.copyTo(os) }
                    }
                    tmp.delete()
                    queryName(ctx, uri) ?: (tr("已打码", "masked") + ".pdf")
                }
            }.onSuccess {
                savedName = it
                stage = Stage.DONE
            }.onFailure {
                stage = Stage.READY
                toast(tr("保存失败：", "Save failed: ") + (it.message ?: tr("未知错误", "unknown error")))
            }
        }
    }

    /** 直接保存到用户授权过的目录（不再弹系统保存框） */
    fun saveToTree(treeUri: Uri, onDone: (String) -> Unit) {
        val f = docFile ?: return
        stage = Stage.MASKING
        progress = 0f
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    val parentDocId = DocumentsContract.getTreeDocumentId(treeUri)
                    val parent = DocumentsContract.buildDocumentUriUsingTree(treeUri, parentDocId)
                    val name = uniqueName(ctx, treeUri, parentDocId, suggestOutName())
                    val docUri = DocumentsContract.createDocument(
                        ctx.contentResolver, parent, "application/pdf", name
                    ) ?: error(tr("无法在该目录创建文件", "Cannot create file in that folder"))
                    ctx.contentResolver.openOutputStream(docUri)?.use { os ->
                        PdfMasker.mask(
                            ctx, f, findings.filter { it.id in selected }, os,
                            erasers = erasers
                        ) { p -> progress = p }
                    } ?: error(tr("无法写入这个位置", "Cannot write to this location"))
                    name
                }
            }.onSuccess { name ->
                savedName = name
                stage = Stage.DONE
                onDone(name)
            }.onFailure {
                stage = Stage.READY
                toast(tr("保存失败：", "Save failed: ") + (it.message ?: tr("未知错误", "unknown error")))
            }
        }
    }

    /** 同目录下重名自动加序号 */
    private fun uniqueName(ctx: Context, treeUri: Uri, parentDocId: String, base: String): String {
        val stem = base.substringBeforeLast('.', base)
        val ext = base.substringAfterLast('.', "pdf")
        val names = HashSet<String>()
        runCatching {
            val children = DocumentsContract.buildChildDocumentsUriUsingTree(treeUri, parentDocId)
            ctx.contentResolver.query(
                children,
                arrayOf(DocumentsContract.Document.COLUMN_DISPLAY_NAME),
                null, null, null
            )?.use { c ->
                while (c.moveToNext()) c.getString(0)?.let { names.add(it) }
            }
        }
        if (base !in names) return base
        var i = 1
        while (i < 500) {
            val n = "$stem ($i).$ext"
            if (n !in names) return n
            i++
        }
        return base
    }

    private fun renderPage(file: File, page: Int, maxWidth: Int): Bitmap? {        return try {
            val pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
            val r = PdfRenderer(pfd)
            r.use {
                if (page !in 0 until r.pageCount) return null
                val p = r.openPage(page)
                val scale = maxWidth.toFloat() / p.width
                val w = maxWidth
                val h = (p.height * scale).toInt().coerceAtLeast(1)
                val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                bmp.eraseColor(Color.WHITE)
                p.render(bmp, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                p.close()
                bmp
            }
        } catch (e: Exception) {
            null
        }
    }

    /** 仅供界面截图测试：直接注入一份已识别结果，跳过真实的 PDF 解析 */
    fun seedForPreview(
        name: String,
        pageTexts: List<PageText>,
        found: List<Finding>,
        sel: Set<Int>,
        thumbBitmaps: Map<Int, Bitmap> = emptyMap()
    ) {
        docName = name
        docKey = name
        pages = pageTexts
        findings = found
        selected = sel
        summary = null
        savedName = ""
        current = 0
        stage = Stage.READY
        for ((k, v) in thumbBitmaps) thumbs[k] = v
    }

    private fun queryName(ctx: Context, uri: Uri): String? {        return try {
            ctx.contentResolver.query(uri, null, null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    val i = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                    if (i >= 0) c.getString(i) else null
                } else null
            }
        } catch (e: Exception) {
            null
        }
    }
}
