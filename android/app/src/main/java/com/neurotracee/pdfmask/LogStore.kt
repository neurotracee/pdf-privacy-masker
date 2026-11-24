package com.neurotracee.pdfmask

import android.content.Context
import java.io.File
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/**
 * 运行日志：启动即记录，崩溃自动留痕，按天分文件，只留 365 天。
 *
 * 隐私红线（这是隐私打码工具，日志绝不能反噬隐私）：
 *  - 绝不记录被处理的内容：不写 PDF 正文、不写识别出的证件号/手机号/姓名/地址。
 *  - 不写用户选择的文件名（只记扩展名、页数档位这类非隐私信息）。
 *  - 只记「发生了什么事件」：启动、导入、开始识别、识别完成（记条目数）、导出、异常堆栈。
 *  - 兜底脱敏：>=11 位连续数字打成 [数字]，邮箱打成 [邮箱]。
 *
 * 存储：filesDir/logs/YYYY-MM-DD.log（UTF-8，应用私有目录，其它应用读不到）。
 * 每次启动生成 8 位 session 短 ID，行内带 session，界面「本次打开」按它筛。
 */
object LogStore {

    private const val KEEP_DAYS = 365
    private const val DATE_FMT = "yyyy-MM-dd"

    @Volatile private var dir: File? = null
    @Volatile private var session: String = "--------"
    @Volatile private var appName: String = "App"
    @Volatile private var appVer: String = "0"
    @Volatile private var installed = false

    /** 上次运行是否是「真·崩溃」（有未捕获异常），启动时据此提示用户看日志。 */
    @Volatile var prevCrashed: Boolean = false
        private set

    @Volatile var prevSession: String = ""
        private set

    private val lock = Any()

    fun init(ctx: Context) {
        if (installed) return
        synchronized(lock) {
            if (installed) return
            val base = File(ctx.applicationContext.filesDir, "logs")
            if (!base.exists()) base.mkdirs()
            dir = base
            session = java.util.UUID.randomUUID().toString().replace("-", "").take(8)
            detectPrevCrash()
            installCrashHandler()
            cleanupOld()
            installed = true
        }
        info("启动 $appName v$appVer · Android ${android.os.Build.VERSION.RELEASE} · " +
            "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
    }

    fun bindVersion(name: String, version: String) {
        appName = name
        appVer = version
    }

    fun sessionId(): String = session

    fun logDir(): File? = dir

    private fun dayStr(offsetDays: Int = 0): String {
        val c = Calendar.getInstance()
        c.add(Calendar.DAY_OF_YEAR, offsetDays)
        return SimpleDateFormat(DATE_FMT, Locale.US).format(c.time)
    }

    private fun fileFor(day: String): File? = dir?.let { File(it, "$day.log") }

    private fun nowStamp(): String =
        SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(Date())

    /** 兜底脱敏 */
    private fun redact(msg: String): String {
        var s = msg
        s = Regex("\\b\\d{11,}\\b").replace(s, "[数字]")
        s = Regex("[\\w.+-]+@[\\w-]+\\.[\\w.-]+").replace(s, "[邮箱]")
        return s
    }

    private fun write(level: String, msg: String) {
        val d = dir ?: return
        try {
            val stamp = nowStamp()
            val prefix = "[$stamp] [$session] [$level] "
            val rows = redact(msg).split("\n")
            val chunk = buildString {
                for (r in rows) { append(prefix).append(r).append("\n") }
            }
            synchronized(lock) {
                if (!d.exists()) d.mkdirs()
                fileFor(dayStr())?.appendText(chunk, Charsets.UTF_8)
            }
        } catch (e: Throwable) {
            // 日志自身绝不能拖垮程序
        }
    }

    fun info(msg: String) = write("INFO", msg)
    fun warn(msg: String) = write("WARN", msg)
    fun error(msg: String) = write("ERROR", msg)

    fun exception(where: String, t: Throwable? = null) {
        val tb = t ?: Throwable("(no throwable)")
        write("ERROR", "异常@$where:\n" + android.util.Log.getStackTraceString(tb).trimEnd())
    }

    private fun installCrashHandler() {
        try {
            val old = Thread.getDefaultUncaughtExceptionHandler()
            Thread.setDefaultUncaughtExceptionHandler { thread, e ->
                try {
                    write("FATAL", "未捕获异常(线程 ${thread?.name}):\n" +
                        android.util.Log.getStackTraceString(e).trimEnd())
                } catch (_: Throwable) {}
                old?.uncaughtException(thread, e)
            }
        } catch (_: Throwable) {}
    }

    fun cleanupOld(): Int {
        val d = dir ?: return 0
        val cutoff = Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR, -KEEP_DAYS) }.time
        var removed = 0
        try {
            d.listFiles()?.forEach { f ->
                if (!f.name.endsWith(".log")) return@forEach
                val stem = f.nameWithoutExtension
                val parsed = try { SimpleDateFormat(DATE_FMT, Locale.US).parse(stem) } catch (e: Exception) { null }
                if (parsed != null && parsed.before(cutoff)) {
                    if (f.delete()) removed++
                }
            }
        } catch (_: Throwable) {}
        return removed
    }

    /** 启动前扫一遍上一个会话：只有出现 FATAL（未捕获异常）才算崩溃。 */
    private fun detectPrevCrash() {
        try {
            val day = dayStr()
            val f = fileFor(day) ?: return
            if (!f.exists()) return
            val pat = Regex("^\\[[^\\]]+]\\s+\\[([0-9a-f]{8})]\\s+\\[(INFO|WARN|ERROR|FATAL)]\\s?(.*)$")
            var lastSession = ""
            var hasFatal = false
            var curSession = ""
            f.forEachLine { line ->
                val m = pat.matchEntire(line.trimEnd()) ?: return@forEachLine
                val sid = m.groupValues[1]
                if (sid != curSession) { curSession = sid; hasFatal = false }
                if (m.groupValues[2] == "FATAL") hasFatal = true
                lastSession = sid
                if (hasFatal) prevCrashed = true
                // 记录每个 session 是否有 FATAL，最后判断最后那个
            }
            prevSession = lastSession
            prevCrashed = hasFatal && lastSession.isNotEmpty()
        } catch (_: Throwable) {}
    }

    // ---------- 读取 ----------

    fun sessionLines(): String {
        val f = fileFor(dayStr()) ?: return ""
        if (!f.exists()) return ""
        val out = StringBuilder()
        try {
            f.forEachLine { line ->
                if (line.contains("[$session]")) out.append(line).append("\n")
            }
        } catch (_: Throwable) {}
        return out.toString().trimEnd()
    }

    fun listDays(): List<String> {
        val d = dir ?: return emptyList()
        val fmt = SimpleDateFormat(DATE_FMT, Locale.US)
        return try {
            d.listFiles()
                ?.filter { it.name.endsWith(".log") }
                ?.mapNotNull { f ->
                    val stem = f.nameWithoutExtension
                    if (runCatching { fmt.parse(stem) }.getOrNull() != null) stem else null
                }
                ?.sortedDescending()
                ?: emptyList()
        } catch (e: Throwable) { emptyList() }
    }

    fun readDay(day: String): String {
        val f = fileFor(day) ?: return ""
        return try { if (f.exists()) f.readText(Charsets.UTF_8) else "" } catch (e: Throwable) { "" }
    }

    /**
     * 读 [fromDay, toDay] 之间的日志。
     * [fromHHmm] / [toHHmm] 形如 "09:30"，传 null 表示整天；只掐首尾两天，中间整天全留。
     */
    fun readRange(fromDay: String, toDay: String, fromHHmm: String? = null, toHHmm: String? = null): String {
        if (fromDay.isBlank() || toDay.isBlank()) return ""
        val lo = minOf(fromDay, toDay)
        val hi = maxOf(fromDay, toDay)
        val out = StringBuilder()
        listDays().filter { it in lo..hi }.sorted().forEach { day ->
            val body = readDay(day)
            if (body.isBlank()) return@forEach
            val kept = body.lineSequence().filter { line ->
                // 行首是 "[yyyy-MM-dd HH:mm:ss.SSS]"，12..16 正好是 HH:mm
                if (!line.startsWith("[") || line.length < 17) return@filter true
                val hm = line.substring(12, 17)
                (day != lo || fromHHmm == null || hm >= fromHHmm) &&
                    (day != hi || toHHmm == null || hm <= toHHmm)
            }.joinToString("\n")
            if (kept.isNotBlank()) {
                out.append("# ==== ").append(day).append(" ====\n").append(kept).append("\n")
            }
        }
        return out.toString().trimEnd()
    }

    /** 区间内有几天日志、一共多少字节（删除前给用户念一遍用）。 */
    fun rangeStats(fromDay: String, toDay: String): Pair<Int, Long> {
        if (fromDay.isBlank() || toDay.isBlank()) return 0 to 0L
        val lo = minOf(fromDay, toDay)
        val hi = maxOf(fromDay, toDay)
        var count = 0
        var bytes = 0L
        listDays().filter { it in lo..hi }.forEach { day ->
            val f = fileFor(day)
            if (f != null && f.exists()) { count++; bytes += f.length() }
        }
        return count to bytes
    }

    /** 用户已经看过崩溃提示，不再重复提醒。 */
    fun dismissCrash() { prevCrashed = false }

    /** 从指定时刻（含）到现在的日志行。 */
    fun readSince(y: Int, mo: Int, d: Int, h: Int, mi: Int): String {
        val cal = Calendar.getInstance().apply {
            set(Calendar.YEAR, y); set(Calendar.MONTH, mo - 1); set(Calendar.DAY_OF_MONTH, d)
            set(Calendar.HOUR_OF_DAY, h); set(Calendar.MINUTE, mi); set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        val since = cal.time
        val sinceDay = SimpleDateFormat(DATE_FMT, Locale.US).format(since)
        val df = SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US)
        val out = StringBuilder()
        listDays().filter { it >= sinceDay }.sorted().forEach { day ->
            readDay(day).lineSequence().forEach { line ->
                if (line.startsWith("[") && line.length > 24) {
                    val ts = runCatching { df.parse(line.substring(1, 24)) }.getOrNull()
                    if (ts != null && !ts.before(since)) out.append(line).append("\n")
                }
            }
        }
        return out.toString().trimEnd()
    }

    fun deleteRange(start: String, end: String): Int {
        var removed = 0
        listDays().filter { it in start..end }.forEach { day ->
            val f = fileFor(day)
            if (f != null && f.exists() && f.delete()) removed++
        }
        if (removed > 0) info("用户删除了 $start ~ $end 的日志，共 $removed 个文件")
        return removed
    }

    fun totalBytes(): Long {
        val d = dir ?: return 0
        return try {
            d.listFiles()?.filter { it.name.endsWith(".log") }?.sumOf { it.length() } ?: 0L
        } catch (e: Throwable) { 0L }
    }

    /** 供界面把日志写进用户选定的 SAF 文件。 */
    fun writeToUri(ctx: Context, uri: android.net.Uri, text: String): Boolean {
        return try {
            ctx.contentResolver.openOutputStream(uri, "wt")?.use { os ->
                os.write(text.toByteArray(Charsets.UTF_8)); os.flush()
            }
            true
        } catch (e: Throwable) {
            false
        }
    }
}
