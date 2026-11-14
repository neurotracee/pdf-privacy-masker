package com.neurotracee.pdfmask

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * 检查更新：Gitee / GitHub 双通道。
 *
 * 只向发布页读一次公开的发布列表，不发送任何本地内容。
 * 用系统自带的 HttpURLConnection + org.json，不额外引依赖（走系统默认的
 * TLS 校验，任何版本都不放宽证书）。
 *
 * 通道顺序由设置里的「更新源」决定：用户选了 Gitee / GitHub 就先走那个，
 * 留在「跟随系统」时看环境——简体中文的界面 + 简体中文的系统 → 先 Gitee
 * （国内直连稳定），其他语言 → 先 GitHub。指定的通道连不上会自动换另一个
 * 再试一次，两个都拿不到才报错。环境判断不出来时按中文用户兜底（Gitee）。
 *
 * 版本号优先从安装包文件名里取（PDFPrivacyMasker-1.4.0-arm64.apk），
 * 文件名没带版本号时退回 release 的 tag（v1.4.0）。
 *
 * 更新级别由发布正文决定，只有两档，都只是「建议」，用户永远能关掉：
 * - 正文里写「更新级别：强烈建议」→ 强烈建议更新（提醒更醒目，关掉前多说一句挽留）；
 * - 没写 / 写成「更新级别：建议」→ 普通建议更新。
 * 没有任何「不更新就不给用」的路径。
 */
object Updater {

    const val GITHUB_REPO = "neurotracee/pdf-privacy-masker"
    const val GITEE_REPO = "bio234/pdf-privacy-masker"

    /** 网络不通时唯一还能用的地址：发布页 */
    const val RELEASES_PAGE = "https://github.com/$GITHUB_REPO/releases/latest"
    const val GITEE_PAGE = "https://gitee.com/$GITEE_REPO/releases/latest"

    /** 本平台安装包的后缀 */
    private const val ASSET_SUFFIX = ".apk"

    /**
     * 允许的下载域名：GitHub 的发布资产走 objects./release-assets. 两个 CDN，
     * Gitee 的附件走 gitee.com 自身。白名单外的一律只给发布页。
     */
    val ALLOWED_HOSTS = listOf(
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "codeload.github.com",
        "gitee.com"
    )

    /** 一个更新通道 */
    data class Channel(val name: String, val label: String, val api: String, val page: String)

    val GITHUB = Channel(
        "github", "GitHub",
        "https://api.github.com/repos/$GITHUB_REPO/releases?per_page=20", RELEASES_PAGE
    )
    val GITEE = Channel(
        "gitee", "Gitee",
        "https://gitee.com/api/v5/repos/$GITEE_REPO/releases?per_page=20", GITEE_PAGE
    )

    data class Result(
        val ok: Boolean,
        val current: String,
        val latest: String = "",
        val hasUpdate: Boolean = false,
        val url: String = RELEASES_PAGE,
        val detail: String = "",
        /** 强烈建议：发布正文里标了「更新级别：强烈建议」。仍然可以关掉，只是关的时候多劝一句 */
        val strong: Boolean = false,
        /** 这次结果来自哪个通道：Gitee / GitHub */
        val channel: String = "",
        /** 发布正文拆出来的弹窗文案：一行摘要 + 按平台归类的详细条目 */
        val digest: ReleaseDigest.Digest? = null,
        /** 这个通道的发布页：详细说明都在那儿 */
        val page: String = RELEASES_PAGE,
        /**
         * 本来该走的是哪个通道，但它连不上、于是换了一个。
         * 空串表示没有发生切换；界面上据实说明一句，用户就不会以为「明明选了 Gitee 怎么用了 GitHub」。
         */
        val fallbackFrom: String = ""
    )

    /** 下载地址是否可信：必须 https，域名在白名单内（含其子域） */
    fun allowedDownload(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val host = try {
            URL(url).host?.lowercase() ?: return false
        } catch (e: Exception) {
            return false
        }
        if (!url.startsWith("https://", ignoreCase = true)) return false
        return ALLOWED_HOSTS.any { host == it || host.endsWith(".$it") }
    }

    /**
     * 默认源是不是 Gitee。
     *
     * 只看系统环境（启动时算好并缓存，见 [AppPrefs.envPrefersGitee]），**不看界面语言**：
     * 用户可能只是把界面切成英文，那不代表他在海外，不该因此把他引到连不上的 GitHub。
     * 默认就是 Gitee，只有系统语言明确非中文、时区也不在东八区时才用 GitHub；
     * 环境判断不出来时同样按 Gitee 兜底。
     */
    fun preferGitee(): Boolean = AppPrefs.envPrefersGitee

    /** 设置里的更新源解析成「是否优先 Gitee」 */
    fun resolve(source: String? = "auto"): Boolean = when ((source ?: "auto").lowercase()) {
        "gitee" -> true
        "github" -> false
        else -> preferGitee()
    }

    fun order(preferGitee: Boolean = preferGitee()): List<Channel> =
        if (preferGitee) listOf(GITEE, GITHUB) else listOf(GITHUB, GITEE)

    fun check(current: String, source: String = "auto"): Result {
        val errors = ArrayList<String>()
        var noAsset: Channel? = null
        val channels = order(resolve(source))
        val wanted = channels.first()

        for (ch in channels) {
            val text = try {
                fetch(ch.api)
            } catch (e: Exception) {
                errors.add(
                    ch.label + ": " + (e.message ?: e.javaClass.simpleName)
                )
                continue
            }
            val got = try {
                parse(text, current, ch.page)
            } catch (e: Exception) {
                errors.add(ch.label + ": JSON " + (e.message ?: "parse error"))
                continue
            }
            if (got == null) {
                errors.add(ch.label + ": " + tr("没有适用于安卓的安装包", "no Android build"))
                noAsset = ch
                continue
            }
            return got.copy(
                channel = ch.label,
                // 首选通道没成功才可能走到这里，如实记下来给界面用
                fallbackFrom = if (ch.label == wanted.label) "" else wanted.label
            )
        }

        val detail = errors.joinToString(" | ")
        if (noAsset != null) {
            return Result(
                ok = false,
                current = current,
                url = noAsset.page,
                detail = detail
            )
        }
        return Result(
            ok = false,
            current = current,
            detail = tr("连不上 Gitee 和 GitHub，可能是网络、代理或安全软件拦住了。",
                "Cannot reach Gitee or GitHub — network, proxy or security software may be blocking it.") +
                (if (detail.isBlank()) "" else "\n$detail")
        )
    }

    /**
     * 解析一段 releases JSON。返回 null 表示「没有本平台的安装包」。
     * pageFallback 是该通道的发布页，资产地址不在白名单时用它兜底。
     */
    fun parse(text: String, current: String, pageFallback: String): Result? {
        val cur = ver(current) ?: intArrayOf(0, 0, 0, 0)
        val arr = JSONArray(text)
        var bestVer: IntArray? = null
        var bestUrl = ""
        var bestStrong = false
        var bestBody = ""
        var tagVer: IntArray? = null
        var tagUrl = ""
        var tagStrong = false
        var tagBody = ""

        for (i in 0 until arr.length()) {
            val rel = arr.optJSONObject(i) ?: continue
            if (rel.optBoolean("draft")) continue
            val page = rel.optString("html_url").ifBlank { pageFallback }
                .let { if (allowedDownload(it)) it else pageFallback }
            val body = rel.optString("body")
            val strong = isStrongUpdate(body)

            ver(rel.optString("tag_name"))?.let { v ->
                val old = tagVer
                if (old == null || cmp(v, old) > 0) {
                    tagVer = v
                    tagUrl = page
                    tagStrong = strong
                    tagBody = body
                }
            }

            val assets = rel.optJSONArray("assets") ?: continue
            for (j in 0 until assets.length()) {
                val a = assets.optJSONObject(j) ?: continue
                val name = a.optString("name")
                if (!name.lowercase().endsWith(ASSET_SUFFIX)) continue
                val v = ver(name) ?: continue
                val raw = a.optString("browser_download_url")
                // 白名单外 → 只给发布页，绝不把用户送到陌生域名
                val url = if (allowedDownload(raw)) raw else page
                val old = bestVer
                if (old == null || cmp(v, old) > 0) {
                    bestVer = v
                    bestUrl = url
                    bestStrong = strong
                    bestBody = body
                }
            }
        }

        bestVer?.let { v ->
            return Result(true, current, fmt(v), cmp(v, cur) > 0, bestUrl, strong = bestStrong,
                digest = ReleaseDigest.of(bestBody), page = pageFallback)
        }
        tagVer?.let { v ->
            return Result(true, current, fmt(v), cmp(v, cur) > 0, tagUrl, strong = tagStrong,
                digest = ReleaseDigest.of(tagBody), page = pageFallback)
        }
        return null
    }

    /**
     * 发布正文里的更新级别标记。只认行首的两种写法：
     * - 单独一行「更新级别：强烈建议」（普通建议写「更新级别：建议」或干脆不写）
     * - 单独一行的旧注释 <!-- update:force -->（早期版本这么写，现在降级成「强烈建议」，不再锁人）
     * 刻意不认正文里出现的「强烈建议」几个字，避免正文举例时误判。
     */
    private val STRONG_RE = Regex(
        "^[ \\t]*(?:更新级别\\s*[：:]\\s*强烈建议|<!--\\s*update\\s*:\\s*force\\s*-->)",
        setOf(RegexOption.IGNORE_CASE, RegexOption.MULTILINE)
    )

    fun isStrongUpdate(body: String?): Boolean = !body.isNullOrBlank() && STRONG_RE.containsMatchIn(body)

    /** 取版本号的前四段（主.次.修订.补丁）；不足四段补 0，取不到返回 null */
    fun ver(text: String): IntArray? {
        val m = VER_RE.find(text) ?: return null
        return intArrayOf(
            m.groupValues[1].toIntOrNull() ?: 0,
            m.groupValues[2].toIntOrNull() ?: 0,
            m.groupValues[3].toIntOrNull() ?: 0,
            m.groupValues[4].toIntOrNull() ?: 0
        )
    }

    /** 四段版本号：主.次.修订.补丁。老的三段写法（1.4.6）在这里补 0，与 1.4.6.0 同版 */
    private val VER_RE = Regex("(\\d+)\\.(\\d+)(?:\\.(\\d+))?(?:\\.(\\d+))?")

    fun cmp(a: IntArray, b: IntArray): Int {
        for (i in 0 until 4) {
            val x = if (i < a.size) a[i] else 0
            val y = if (i < b.size) b[i] else 0
            if (x != y) return if (x > y) 1 else -1
        }
        return 0
    }

    fun fmt(v: IntArray): String = "${v[0]}.${v[1]}.${v[2]}.${v[3]}"

    private fun fetch(api: String): String {
        val conn = URL(api).openConnection() as HttpURLConnection
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

/** 给测试用的假数据入口：解析一段 JSON 文本，不发网络请求（按 GitHub 通道兜底） */
internal fun parseReleasesForTest(text: String, current: String): Updater.Result {
    return Updater.parse(text, current, Updater.RELEASES_PAGE)
        ?: Updater.Result(false, current, detail = "no apk")
}
