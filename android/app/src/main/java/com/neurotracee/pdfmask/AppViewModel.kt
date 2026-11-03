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
import com.neurotracee.pdfmask.core.PdfTextExtractor
import com.neurotracee.pdfmask.core.Rect
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

enum class Stage { HOME, LOADING, READY, MASKING, DONE }

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

    fun toast(msg: String) {
        message = msg
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
        viewModelScope.launch {
            runCatching {
                withContext(Dispatchers.IO) {
                    val ctx = getApplication<Application>()
                    val name = queryName(ctx, uri) ?: (tr("文档", "document") + ".pdf")
                    val tmp = File(ctx.cacheDir, "src_" + System.currentTimeMillis() + ".pdf")
                    ctx.contentResolver.openInputStream(uri)?.use { ins ->
                        FileOutputStream(tmp).use { outs -> ins.copyTo(outs) }
                    } ?: error(tr("无法读取这个文件", "Cannot read this file"))
                    val pageText = PdfTextExtractor.extract(ctx, tmp)
                    val found = Detector.detect(pageText)
                    Triple(name, tmp, pageText to found)
                }
            }.onSuccess { (name, tmp, pair) ->
                docName = name
                docFile = tmp
                pages = pair.first
                findings = pair.second
                selected = pair.second.filter { !it.suspect }.map { it.id }.toSet()
                summary = null
                savedName = ""
                current = 0
                stage = Stage.READY
                if (pair.second.isEmpty()) toast(tr("没有识别到隐私信息，可以在预览上手动框选", "Nothing detected. You can drag boxes on the preview."))
            }.onFailure {
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
        docFile?.let { runCatching { it.delete() } }
        stage = Stage.HOME
        docName = ""
        docFile = null
        pages = emptyList()
        findings = emptyList()
        selected = emptySet()
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
                            ctx, f, findings.filter { it.id in selected }, os
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
                            ctx, f, findings.filter { it.id in selected }, os
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
                            ctx, f, findings.filter { it.id in selected }, os
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
