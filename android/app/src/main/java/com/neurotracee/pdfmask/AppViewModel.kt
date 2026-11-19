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
import com.neurotracee.pdfmask.core.DraftStore
import com.neurotracee.pdfmask.core.Finding
import com.neurotracee.pdfmask.core.JobCancelled
import com.neurotracee.pdfmask.core.JobControl
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

/** 当前跑的是哪一类长任务（决定底部面板的标题与按钮可用性） */
enum class JobKind { NONE, SCAN, MASK }

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

    // ------------------------------------------------------------ 任务进度面板
    //
    // 以前界面上只有个转圈，用户不知道在干什么、也不知道还要多久。现在统一成
    // 「文件总进度 + 当前页进度」两条，外加暂停 / 停止 / 继续三个按钮。
    // 数字全部由工作线程推进（IO 线程写 Compose 状态与 pdfmask 里既有的
    // `progress = p` 是同一做法），界面只负责画。
    var jobActive by mutableStateOf(false)
        private set
    var jobPaused by mutableStateOf(false)
        private set
    var jobKind by mutableStateOf(JobKind.NONE)
        private set
    var jobTitle by mutableStateOf("")
        private set

    /** 标题后的小字说明，例如「扫描页」——OCR 阶段页数只算要 OCR 的那几页 */
    var jobNote by mutableStateOf("")
        private set
    var jobPage by mutableStateOf(0)
        private set
    var jobPages by mutableStateOf(0)
        private set
    var jobPageFrac by mutableStateOf(0f)
        private set
    var jobOverall by mutableStateOf(0f)
        private set

    private var ctl: JobControl? = null

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

    // -------------------------------------------------------------- 任务控制

    private fun beginJob(kind: JobKind, title: String): JobControl {
        val c = JobControl()
        ctl = c
        jobKind = kind
        jobActive = true
        jobPaused = false
        jobTitle = title
        jobNote = ""
        jobPage = 0
        jobPages = 0
        jobPageFrac = 0f
        jobOverall = 0f
        return c
    }

    private fun endJob() {
        jobActive = false
        jobPaused = false
        jobKind = JobKind.NONE
        jobTitle = ""
        jobNote = ""
        ctl = null
    }

    fun pauseJob() {
        ctl?.pause()
        jobPaused = true
    }

    fun resumeJob() {
        ctl?.resume()
        jobPaused = false
    }

    /** 停止：工作线程在下一个安全点（页与页之间）抛 [JobCancelled] 退出 */
    fun stopJob() {
        ctl?.stop()
        jobPaused = false
    }

    /**
     * 上报进度。整个任务按「阶段权重」换算成一条总进度：
     * 例如「读取文字层」占 0.05~0.20，那么读到第 2/10 页时总进度就是 0.08。
     *
     * @param page0 当前页（从 0 开始）
     * @param total 本阶段的页数（OCR 阶段只算需要 OCR 的页）
     */
    private fun reportProgress(
        from: Float, to: Float, page0: Int, pageFrac: Float, total: Int,
        title: String? = null, note: String? = null
    ) {
        if (total <= 0) return
        val p = page0.coerceIn(0, total - 1)
        val f = pageFrac.coerceIn(0f, 1f)
        if (title != null) jobTitle = title
        if (note != null) jobNote = note
        jobPages = total
        jobPage = p + 1
        jobPageFrac = f
        jobOverall = (from + (to - from) * ((p + f) / total)).coerceIn(0f, 1f)
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
        if (stage == Stage.MASKING) {
            stopJob()
            stage = Stage.READY
        }
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
        val job = beginJob(JobKind.SCAN, tr("正在读取文件", "Reading file"))
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    val name = queryName(ctx, uri) ?: (tr("文档", "document") + ".pdf")
                    val tmp = File(ctx.cacheDir, "src_" + System.currentTimeMillis() + ".pdf")
                    // 拷文件也报进度：大文件在低端机上要几秒，不给数字就像卡死
                    val totalBytes = runCatching {
                        ctx.contentResolver.openFileDescriptor(uri, "r")?.use { it.statSize }
                    }.getOrNull() ?: -1L
                    ctx.contentResolver.openInputStream(uri)?.use { ins ->
                        FileOutputStream(tmp).use { outs ->
                            val buf = ByteArray(64 * 1024)
                            var done = 0L
                            while (true) {
                                job.checkpoint()
                                val n = ins.read(buf)
                                if (n < 0) break
                                outs.write(buf, 0, n)
                                done += n
                                if (totalBytes > 0) {
                                    jobTitle = tr("正在读取文件", "Reading file")
                                    jobOverall = 0.05f * (done.toFloat() / totalBytes).coerceAtMost(1f)
                                }
                            }
                        }
                    } ?: error(tr("无法读取这个文件", "Cannot read this file"))

                    // 扫描件 / 拍照件没有文字层，PDFBox 读不出任何字形；
                    // 这类页面交给端侧 OCR 补出「文字 + 每字矩形」，后续规则完全复用
                    val rawText = PdfTextExtractor.extract(ctx, tmp) { pno, n ->
                        reportProgress(0.05f, 0.20f, pno, 0f, n,
                            tr("正在读取文字层", "Reading text layer"), "")
                    }
                    val scanTotal = rawText.count { it.lines.isEmpty() }
                    var ocrAt = 0
                    val pageText = if (scanTotal > 0)
                        OcrEngine.augment(
                            ctx, tmp, rawText,
                            onProgress = { i ->
                                ocrAt = i - 1
                                reportProgress(0.20f, 0.90f, i - 1, 0f, scanTotal,
                                    tr("正在识别扫描页", "Reading scanned pages"),
                                    tr("扫描页", "scanned"))
                            },
                            job = job,
                            onPageFrac = { f ->
                                reportProgress(0.20f, 0.90f, ocrAt, f, scanTotal)
                            }
                        ) else rawText
                    ocrPages = rawText.indices.count {
                        rawText[it].lines.isEmpty() && pageText[it].lines.isNotEmpty()
                    }
                    val found = Detector.detect(
                        pageText,
                        onProgress = { i, n ->
                            reportProgress(0.90f, 1f, i - 1, 0f, n,
                                tr("正在定位敏感信息", "Locating sensitive data"), "")
                        },
                        job = job
                    )
                    Loaded(name, tmp, pageText, found, "$name|${tmp.length()}")
                }
            }.onSuccess { r ->
                endJob()
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
                endJob()
                docKey = ""
                erasers = emptyMap()
                stage = Stage.HOME
                // 用户自己点的「停止」不是失败，不要说成「打开失败」
                if (it is JobCancelled) {
                    toast(tr("已停止", "Stopped"))
                } else {
                    toast(tr("打开失败：", "Open failed: ") + (it.message ?: tr("未知错误", "unknown error")))
                }
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

    // ---------------------------------------------------------------- 临时保存
    //
    // 返回键给了三个出口：继续编辑 / 临时保存 / 直接离开。选「临时保存」时把
    // 源 PDF 和当前编辑状态一起落到私有目录，下次在首页点「继续编辑」接上。
    // 只留最近一份——这是临走前的收尾动作，不是多文档工作台。

    /** 首页卡片用；null 表示没有待续的草稿 */
    var draftMeta by mutableStateOf<DraftStore.Meta?>(null)
        private set

    fun refreshDraft() {
        draftMeta = DraftStore.meta(getApplication())
    }

    /** @return 是否真的写成功——失败时界面要说「没存上」，不能假装成功 */
    fun saveDraft(): Boolean {
        val f = docFile ?: return false
        val ctx = getApplication<Application>()
        val ok = DraftStore.save(ctx, f, docName, pages.size, findings, selected, erasers, current)
        refreshDraft()
        return ok
    }

    fun discardDraft() {
        DraftStore.clear(getApplication())
        refreshDraft()
    }

    /**
     * 恢复草稿。
     *
     * 只重新读文字层（`PdfTextExtractor`，纯解析、不跑 OCR），识别结果和编辑
     * 状态全部用草稿里的：重新 detect 既慢又可能因为模型/规则版本差异把用户
     * 手动删掉的框又冒出来，那就不叫「接着编辑」了。
     */
    fun resumeDraft() {
        val ctx = getApplication<Application>()
        val snap = DraftStore.load(ctx)
        if (snap == null) {
            toast(tr("草稿已失效", "This draft is no longer available"))
            refreshDraft()
            return
        }
        // 显式命名：smart-cast 进到协程 lambda 里会失效，直接写 snap.pdf 推断不出来
        val draft: DraftStore.Snapshot = snap
        stage = Stage.LOADING
        progress = 0f
        thumbs.clear()
        erasers = emptyMap()
        nextManualId = -1
        beginJob(JobKind.SCAN, tr("正在恢复编辑", "Restoring"))
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val tmp = File(ctx.cacheDir, "src_" + System.currentTimeMillis() + ".pdf")
                    draft.pdf.copyTo(tmp, overwrite = true)
                    val pageText = PdfTextExtractor.extract(ctx, tmp) { pno, n ->
                        reportProgress(0f, 1f, pno, 0f, n,
                            tr("正在读取文字层", "Reading text layer"), "")
                    }
                    Triple(tmp, pageText, draft)
                }
            }.onSuccess { r ->
                endJob()
                val (tmp, pageText, s) = r
                docName = s.name
                docFile = tmp
                pages = pageText
                // 页数对不上（换了文件、或草稿里的页被删）只保留仍然落在页内的框
                findings = s.findings.filter { it.page in pageText.indices }
                selected = s.selected.filter { id -> findings.any { it.id == id } }.toSet()
                erasers = s.erasers.filterKeys { it in pageText.indices }
                // 手动框的 id 从 -1 往下走，接着草稿里最小的那个继续
                nextManualId = ((findings.minOfOrNull { it.id } ?: 0).coerceAtMost(0)) - 1
                current = s.current.coerceIn(0, (pageText.size - 1).coerceAtLeast(0))
                summary = null
                savedName = ""
                docKey = "$docName|${tmp.length()}"
                stage = Stage.READY
                toast(tr("已恢复上次未完成的编辑", "Restored your unfinished edits"))
            }.onFailure {
                endJob()
                stage = Stage.HOME
                docKey = ""
                toast(tr("恢复失败：", "Restore failed: ") + (it.message ?: tr("未知错误", "unknown error")))
            }
        }
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

    /**
     * 真正干打码活的地方：三个保存入口（另存为 / 复制 / 直接存目录）都走这里，
     * 保证进度上报、暂停停止、擦除减法在三条路径上完全一致。
     */
    private fun maskInto(ctx: Context, src: File, os: java.io.OutputStream) {
        val total = pages.size.coerceAtLeast(1)
        val job = beginJob(JobKind.MASK, tr("正在打码", "Masking"))
        PdfMasker.mask(
            ctx, src, findings.filter { it.id in selected }, os,
            erasers = erasers,
            job = job,
            onPage = { i, fr -> reportProgress(0f, 1f, i, fr, total) },
            onProgress = { p -> progress = p }
        )
    }

    /** 渲染某一页缩略图（用于预览） */
    fun ensureThumb(page: Int, maxWidthPx: Int) {        if (thumbs.containsKey(page)) return
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
                    out.use { os -> maskInto(ctx, f, os) }
                    queryName(ctx, uri) ?: (tr("已打码", "masked") + ".pdf")
                }
            }.onSuccess { name ->
                endJob()
                savedName = name
                stage = Stage.DONE
                onDone(name)
            }.onFailure {
                endJob()
                stage = Stage.READY
                if (it is JobCancelled) toast(tr("已停止", "Stopped"))
                else toast(tr("生成失败：", "Failed: ") + (it.message ?: tr("未知错误", "unknown error")))
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
                    FileOutputStream(tmp).use { os -> maskInto(ctx, f, os) }
                    ctx.contentResolver.openOutputStream(uri)?.use { os ->
                        tmp.inputStream().use { it.copyTo(os) }
                    }
                    tmp.delete()
                    queryName(ctx, uri) ?: (tr("已打码", "masked") + ".pdf")
                }
            }.onSuccess {
                endJob()
                savedName = it
                stage = Stage.DONE
            }.onFailure {
                endJob()
                stage = Stage.READY
                if (it is JobCancelled) toast(tr("已停止", "Stopped"))
                else toast(tr("保存失败：", "Save failed: ") + (it.message ?: tr("未知错误", "unknown error")))
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
                        maskInto(ctx, f, os)
                    } ?: error(tr("无法写入这个位置", "Cannot write to this location"))
                    name
                }
            }.onSuccess { name ->
                endJob()
                savedName = name
                stage = Stage.DONE
                onDone(name)
            }.onFailure {
                endJob()
                stage = Stage.READY
                if (it is JobCancelled) toast(tr("已停止", "Stopped"))
                else toast(tr("保存失败：", "Save failed: ") + (it.message ?: tr("未知错误", "unknown error")))
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
