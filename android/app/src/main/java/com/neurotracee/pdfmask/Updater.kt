package com.neurotracee.pdfmask

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * 检查更新：只向 GitHub 读一次公开的发布列表，不发送任何本地内容。
 *
 * 用系统自带的 HttpURLConnection + org.json，不额外引依赖。
 * 版本号优先从安装包文件名里取（PDFPrivacyMasker-1.4.0-arm64.apk），
 * 文件名没带版本号时退回 release 的 tag（v1.4.0）。
 */
object Updater {

    private const val REPO = "neurotracee/pdf-privacy-masker"
    private const val API = "https://api.github.com/repos/$REPO/releases?per_page=20"

    /** 网络不通时唯一还能用的地址：发布页 */
    const val RELEASES_PAGE = "https://github.com/$REPO/releases/latest"

    /** 本平台安装包的后缀 */
    private const val ASSET_SUFFIX = ".apk"

    data class Result(
        val ok: Boolean,
        val current: String,
        val latest: String = "",
        val hasUpdate: Boolean = false,
        val url: String = RELEASES_PAGE,
        val detail: String = ""
    )

    fun check(current: String): Result {
        val cur = ver(current) ?: intArrayOf(0, 0, 0)
        val text = try {
            fetch()
        } catch (e: Exception) {
            return Result(
                ok = false,
                current = current,
                detail = tr("连不上 GitHub，可能是网络、代理或安全软件拦住了。",
                    "Cannot reach GitHub — network, proxy or security software may be blocking it.") +
                    "\n" + (e.message ?: e.javaClass.simpleName)
            )
        }

        val arr = try {
            JSONArray(text)
        } catch (e: Exception) {
            return Result(false, current, detail = "JSON: " + (e.message ?: "parse error"))
        }

        var bestVer: IntArray? = null
        var bestUrl = ""
        var tagVer: IntArray? = null
        var tagUrl = ""

        for (i in 0 until arr.length()) {
            val rel = arr.optJSONObject(i) ?: continue
            if (rel.optBoolean("draft")) continue
            val page = rel.optString("html_url").ifBlank { RELEASES_PAGE }

            ver(rel.optString("tag_name"))?.let { v ->
                val old = tagVer
                if (old == null || cmp(v, old) > 0) {
                    tagVer = v
                    tagUrl = page
                }
            }

            val assets = rel.optJSONArray("assets") ?: continue
            for (j in 0 until assets.length()) {
                val a = assets.optJSONObject(j) ?: continue
                val name = a.optString("name")
                if (!name.lowercase().endsWith(ASSET_SUFFIX)) continue
                val v = ver(name) ?: continue
                val old = bestVer
                if (old == null || cmp(v, old) > 0) {
                    bestVer = v
                    bestUrl = a.optString("browser_download_url").ifBlank { page }
                }
            }
        }

        bestVer?.let { v ->
            return Result(true, current, fmt(v), cmp(v, cur) > 0, bestUrl)
        }
        tagVer?.let { v ->
            return Result(true, current, fmt(v), cmp(v, cur) > 0, tagUrl)
        }
        return Result(
            ok = false,
            current = current,
            detail = tr("仓库里还没有适用于安卓的安装包，可以去发布页手动看看。",
                "No Android build in the releases yet — have a look at the releases page.")
        )
    }

    /** 取第一段 x.y.z；取不到返回 null */
    fun ver(text: String): IntArray? {
        val m = Regex("(\\d+)\\.(\\d+)(?:\\.(\\d+))?").find(text) ?: return null
        return intArrayOf(
            m.groupValues[1].toIntOrNull() ?: 0,
            m.groupValues[2].toIntOrNull() ?: 0,
            m.groupValues[3].toIntOrNull() ?: 0
        )
    }

    fun cmp(a: IntArray, b: IntArray): Int {
        for (i in 0 until 3) {
            val x = if (i < a.size) a[i] else 0
            val y = if (i < b.size) b[i] else 0
            if (x != y) return if (x > y) 1 else -1
        }
        return 0
    }

    fun fmt(v: IntArray): String = "${v[0]}.${v[1]}.${v[2]}"

    private fun fetch(): String {
        val conn = URL(API).openConnection() as HttpURLConnection
        conn.connectTimeout = 8000
        conn.readTimeout = 8000
        conn.requestMethod = "GET"
        conn.setRequestProperty("User-Agent", "PDFPrivacyMasker-Android")
        conn.setRequestProperty("Accept", "application/vnd.github+json")
        try {
            val code = conn.responseCode
            if (code !in 200..299) throw RuntimeException("HTTP $code")
            return conn.inputStream.bufferedReader().use { it.readText() }
        } finally {
            conn.disconnect()
        }
    }
}

/** 给测试用的假数据入口：解析一段 JSON 文本，不发网络请求 */
internal fun parseReleasesForTest(text: String, current: String): Updater.Result {
    val arr = JSONArray(text)
    var bestVer: IntArray? = null
    var bestUrl = ""
    for (i in 0 until arr.length()) {
        val rel: JSONObject = arr.optJSONObject(i) ?: continue
        val assets = rel.optJSONArray("assets") ?: continue
        for (j in 0 until assets.length()) {
            val a = assets.optJSONObject(j) ?: continue
            val name = a.optString("name")
            if (!name.lowercase().endsWith(".apk")) continue
            val v = Updater.ver(name) ?: continue
            val old = bestVer
            if (old == null || Updater.cmp(v, old) > 0) {
                bestVer = v
                bestUrl = a.optString("browser_download_url")
            }
        }
    }
    val cur = Updater.ver(current) ?: intArrayOf(0, 0, 0)
    bestVer?.let { return Updater.Result(true, current, Updater.fmt(it), Updater.cmp(it, cur) > 0, bestUrl) }
    return Updater.Result(false, current, detail = "no apk")
}
