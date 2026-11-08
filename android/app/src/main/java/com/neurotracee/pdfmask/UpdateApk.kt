package com.neurotracee.pdfmask

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * 应用内下载新安装包并交给系统安装器。
 *
 * 为什么要自己下，而不是像以前那样交给浏览器：
 *
 * Gitee 的附件 CDN 对 .apk 返回的 Content-Type 是 `application/zip`（同一个仓库的
 * .exe 返回的是 application/vnd.microsoft.portable-executable，是正常的）。浏览器
 * 看到 MIME 是 zip，就把文件存成 `PDFPrivacyMasker-1.4.4-arm64.apk.zip`，用户点了
 * 装不上，还以为下坏了。这是服务器端的类型标注问题，我们改不了，只能不经过浏览器：
 * 自己把字节存成自己起的文件名，再走系统安装器。
 *
 * 顺带的好处：能当场校验下载到的确实是本应用的安装包（包名 + 版本号对得上），
 * 万一 CDN 抽风返回了一个错误页或者源码 zip，能立刻发现并按失败处理，而不是
 * 让用户去安装一个看不懂的文件。
 *
 * 隐私：只下载用户点击的那个安装包地址，不发任何本地内容；文件写在应用自己的
 * 缓存目录，装完或取消后清除。
 */
object UpdateApk {

    /** 与 AndroidManifest 里 FileProvider 的 authorities 保持一致 */
    const val AUTHORITY = "com.neurotracee.pdfmask.updatefile"

    private const val DIR = "update"
    private const val MAX_REDIRECTS = 5
    private const val MIN_BYTES = 2L * 1024 * 1024      // 正常安装包 14MB 左右，低于 2MB 肯定不对
    private const val MAX_BYTES = 300L * 1024 * 1024
    private const val PROGRESS_GAP_MS = 120L

    sealed class Outcome {
        /** 已经拉起系统安装界面 */
        object Started : Outcome()

        /** 系统还没允许本应用安装应用，需要用户去开一下 */
        object NeedPermission : Outcome()

        /** 下载或校验失败，reason 是给用户看的一句话 */
        data class Failed(val reason: String) : Outcome()
    }

    data class Fetched(val outcome: Outcome, val apk: File? = null)

    fun dir(ctx: Context): File = File(ctx.cacheDir, DIR).apply { if (!exists()) mkdirs() }

    /** 清掉上次留下的安装包，避免缓存目录越堆越大 */
    fun clean(ctx: Context, keep: File? = null) {
        dir(ctx).listFiles()?.forEach { f ->
            if (keep == null || f.canonicalPath != keep.canonicalPath) f.delete()
        }
    }

    /**
     * 下载 + 校验 + 拉起安装。整个过程在 IO 线程，进度回调切回主线程。
     *
     * @param version 期望的版本号（来自发布页），用来核对下载到的包确实是这一版
     */
    suspend fun fetchAndInstall(
        ctx: Context,
        url: String,
        version: String,
        onProgress: (done: Long, total: Long) -> Unit = { _, _ -> }
    ): Fetched {
        val apk = try {
            withContext(Dispatchers.IO) { download(ctx, url, version, onProgress) }
        } catch (e: Exception) {
            val msg = e.message?.takeIf { it.isNotBlank() }
                ?: tr("下载没完成", "The download did not finish")
            return Fetched(Outcome.Failed(msg))
        }
        return Fetched(install(ctx, apk), apk)
    }

    /** 已经下好了（比如上次卡在权限那步），直接再拉一次安装界面 */
    fun retryInstall(ctx: Context, apk: File): Outcome =
        if (apk.exists()) install(ctx, apk)
        else Outcome.Failed(tr("安装包已经不在了，请重新下载", "The file is gone — please download again"))

    /**
     * 下载安装包到缓存目录。完成时返回文件；任何一步不对都抛异常，由调用方转成提示。
     */
    fun download(
        ctx: Context,
        url: String,
        version: String,
        onProgress: (Long, Long) -> Unit
    ): File {
        // 只认白名单里的域名，绝不跟着任何陌生地址走
        if (!Updater.allowedDownload(url)) {
            throw IOException(tr("下载地址不在允许的范围内", "The download address is not allowed"))
        }

        clean(ctx)
        val part = File(dir(ctx), "download.part")
        part.delete()

        val conn = open(url)
        try {
            val total = conn.contentLengthLong
            if (total > MAX_BYTES) {
                throw IOException(tr("安装包比预期大得多，已中止", "The file is far larger than expected — stopped"))
            }

            val main = Handler(Looper.getMainLooper())
            var lastPush = 0L
            var done = 0L

            conn.inputStream.use { input ->
                part.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n <= 0) break
                        out.write(buf, 0, n)
                        done += n
                        if (done > MAX_BYTES) {
                            throw IOException(tr("安装包比预期大得多，已中止", "The file is far larger than expected — stopped"))
                        }
                        val now = System.currentTimeMillis()
                        if (now - lastPush >= PROGRESS_GAP_MS) {
                            lastPush = now
                            if (total > 0) main.post { onProgress(done, total) }
                        }
                    }
                }
            }
            if (total > 0) main.post { onProgress(done, total) }

            if (total > 0 && done != total) {
                throw IOException(
                    tr("下载不完整（" + done + " / " + total + " 字节）",
                        "Incomplete download (" + done + " / " + total + " bytes)")
                )
            }
            if (done < MIN_BYTES) {
                throw IOException(
                    tr("下载到的文件太小，可能下到了错误页", "The file is too small — an error page was probably saved")
                )
            }
            // APK 就是 zip 包，头 4 字节必须是 PK\x03\x04
            val head = ByteArray(4)
            part.inputStream().use { it.read(head) }
            if (!(head[0] == 0x50.toByte() && head[1] == 0x4B.toByte())) {
                throw IOException(
                    tr("下载到的不是安装包（可能被网络劫持或 CDN 出错）",
                        "What was downloaded is not an installer (network tampering or a CDN error)")
                )
            }

            // 认包名和版本，确认这就是本应用的这一版
            val info = packageInfo(ctx, part)
            if (info == null || info.first != ctx.packageName) {
                throw IOException(
                    tr("下载到的不是本应用的安装包", "The file is not this app's installer")
                )
            }
            val got = info.second
            if (got.isNotBlank() && version.isNotBlank()) {
                val a = Updater.ver(got)
                val b = Updater.ver(version)
                if (a != null && b != null && Updater.cmp(a, b) != 0) {
                    throw IOException(
                        tr("下载到的版本是 v$got，不是 v$version", "The file is v$got, not v$version")
                    )
                }
            }
        } finally {
            conn.disconnect()
        }

        val target = File(dir(ctx), "PDFPrivacyMasker-$version.apk")
        if (target.exists()) target.delete()
        if (!part.renameTo(target)) {
            // 个别机型缓存目录不支持改名，退回复制
            part.copyTo(target, overwrite = true)
            part.delete()
        }
        return target
    }

    /** 读 APK 里的包名与版本号；读不出来返回 null */
    @Suppress("DEPRECATION")
    private fun packageInfo(ctx: Context, apk: File): Pair<String, String>? {
        val pm = ctx.packageManager
        val info = pm.getPackageArchiveInfo(apk.absolutePath, 0) ?: return null
        return info.packageName to (info.versionName ?: "")
    }

    /** 系统是否已允许本应用安装应用（Android 8 起需要用户单独开一次） */
    fun canInstall(ctx: Context): Boolean = try {
        Build.VERSION.SDK_INT < Build.VERSION_CODES.O || ctx.packageManager.canRequestPackageInstalls()
    } catch (e: Exception) {
        false
    }

    /** 拉起系统安装界面；没权限时只返回 NeedPermission，让界面去引导 */
    fun install(ctx: Context, apk: File): Outcome {
        if (!canInstall(ctx)) {
            return Outcome.NeedPermission
        }
        val uri: Uri = try {
            FileProvider.getUriForFile(ctx, AUTHORITY, apk)
        } catch (e: Exception) {
            return Outcome.Failed(
                tr("没法把安装包交给系统（" + e.javaClass.simpleName + "）",
                    "Could not hand the file to the system (" + e.javaClass.simpleName + ")")
            )
        }
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return try {
            ctx.startActivity(intent)
            Outcome.Started
        } catch (e: Exception) {
            Outcome.Failed(
                tr("没能打开安装界面（" + e.javaClass.simpleName + "）",
                    "Could not open the installer (" + e.javaClass.simpleName + ")")
            )
        }
    }

    /** 跳到「允许安装未知应用」的本应用页面；个别机型没有这个页面时退回总设置 */
    fun openInstallPermission(ctx: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val direct = Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:" + ctx.packageName)
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            try {
                ctx.startActivity(direct)
                return
            } catch (e: Exception) {
                // 落到下面的通用设置
            }
            try {
                ctx.startActivity(
                    Intent(Settings.ACTION_SECURITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                )
            } catch (e: Exception) {
                // 什么都不做，用户自己去找
            }
        }
    }

    /** 发请求并手动跟重定向：每一跳都必须是 https + 白名单域名 */
    private fun open(url: String): HttpURLConnection {
        var current = url
        var hops = 0
        while (true) {
            val conn = URL(current).openConnection() as HttpURLConnection
            conn.instanceFollowRedirects = false
            conn.connectTimeout = 15000
            conn.readTimeout = 30000
            conn.requestMethod = "GET"
            conn.setRequestProperty("User-Agent", "PDFPrivacyMasker-Android")
            conn.setRequestProperty("Accept", "*/*")
            val code = conn.responseCode
            if (code in 300..399) {
                val loc = conn.getHeaderField("Location")
                conn.disconnect()
                if (loc.isNullOrBlank() || hops >= MAX_REDIRECTS) {
                    throw IOException(tr("下载地址跳转异常", "The download address redirects oddly"))
                }
                val next = URL(URL(current), loc).toString()
                if (!Updater.allowedDownload(next)) {
                    throw IOException(tr("下载被转到了不允许的地址", "The download was redirected to a disallowed address"))
                }
                current = next
                hops++
                continue
            }
            if (code !in 200..299) {
                conn.disconnect()
                throw IOException(tr("下载失败（HTTP " + code + "）", "Download failed (HTTP " + code + ")"))
            }
            return conn
        }
    }
}
