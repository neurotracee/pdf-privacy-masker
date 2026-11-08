package com.neurotracee.pdfmask

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * 全局偏好：语言、主题模式、保存位置、更新检查方式与更新源。
 * 用 Compose 的 MutableState 承载，改动后界面立即重组，不需要重启。
 */
object AppPrefs {

    private const val FILE = "pdfmask"

    /** 语言：zh / en */
    var lang by mutableStateOf("zh")
        private set

    /** 主题：system / light / dark */
    var themeMode by mutableStateOf("system")
        private set

    /** 默认保存目录（SAF 树 Uri，带持久授权）；null 表示还没设置 */
    var saveTreeUri by mutableStateOf<String?>(null)
        private set

    /** 下次默认使用这个路径 */
    var rememberDir by mutableStateOf(true)
        private set

    /** 不再询问，直接存到默认目录 */
    var noAsk by mutableStateOf(false)
        private set

    /** 是否已经问过保存位置（首次两问只问一次） */
    var askedSaveOnce by mutableStateOf(false)
        private set

    /** 启动时自动检查更新；关掉就是纯手动 */
    var autoCheck by mutableStateOf(true)
        private set

    /** 更新源：auto（跟随环境）/ gitee / github */
    var updateSource by mutableStateOf("auto")
        private set

    /**
     * 「这台机器默认该走 Gitee 吗」——启动时算一次就固定，之后不再变。
     *
     * 为什么要在启动时算一次：之前每次调用都现读 [java.util.Locale.getDefault()]，
     * 而这个值在进程刚起来、系统配置还没应用时可能是 en，界面渲染完之后才变成 zh，
     * 于是同一个「自动」在启动瞬间判成 GitHub、过一会儿又变回 Gitee（用户就看到了
     * 更新窗口从 GitHub 拉、关掉窗口又显示 Gitee）。现在改成一次性算好，全程一致。
     *
     * 判断依据只有系统本身，不看界面语言——用户可能只是把界面切成英文，
     * 那不代表他在海外。默认永远是 Gitee，只有「语言明确不是中文 + 时区也不在东八区」
     * 这种明确的海外环境才改用 GitHub；任何一项取不到都按 Gitee 兜底。
     */
    var envPrefersGitee by mutableStateOf(true)
        private set

    private var sp: SharedPreferences? = null

    fun init(ctx: Context) {
        if (sp != null) return
        val p = ctx.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        sp = p
        envPrefersGitee = detectGiteePreference(ctx)
        lang = if (p.getString("lang", "zh") == "en") "en" else "zh"
        themeMode = when (p.getString("themeMode", "system")) {
            "light", "dark" -> p.getString("themeMode", "system")!!
            else -> "system"
        }
        saveTreeUri = p.getString("saveTreeUri", null)
        rememberDir = p.getBoolean("rememberDir", true)
        noAsk = p.getBoolean("noAsk", false)
        askedSaveOnce = p.getBoolean("askedSaveOnce", false)
        autoCheck = p.getBoolean("autoCheck", true)
        updateSource = p.getString("updateSource", "auto")
            ?.takeIf { it == "gitee" || it == "github" || it == "auto" } ?: "auto"
    }

    fun updateLang(v: String) {
        lang = if (v == "en") "en" else "zh"
        sp?.edit()?.putString("lang", lang)?.apply()
    }

    fun updateTheme(v: String) {
        themeMode = if (v == "light" || v == "dark") v else "system"
        sp?.edit()?.putString("themeMode", themeMode)?.apply()
    }

    fun updateSaveDir(v: String?) {
        saveTreeUri = v
        sp?.edit()?.putString("saveTreeUri", v)?.apply()
    }

    fun updateRememberDir(v: Boolean) {
        rememberDir = v
        sp?.edit()?.putBoolean("rememberDir", v)?.apply()
    }

    fun updateNoAsk(v: Boolean) {
        noAsk = v
        sp?.edit()?.putBoolean("noAsk", v)?.apply()
    }

    fun updateAutoCheck(v: Boolean) {
        autoCheck = v
        sp?.edit()?.putBoolean("autoCheck", v)?.apply()
    }

    /** "auto" 表示跟随环境，界面高亮时用 [resolvedUpdateSource] */
    fun updateUpdateSource(v: String) {
        updateSource = if (v == "gitee" || v == "github") v else "auto"
        sp?.edit()?.putString("updateSource", updateSource)?.apply()
    }

    /** 实际会走的源：显式选择优先；auto 时问环境，问不出来按 Gitee 兜底 */
    val resolvedUpdateSource: String
        get() = when (updateSource) {
            "gitee", "github" -> updateSource
            else -> if (Updater.preferGitee()) "gitee" else "github"
        }

    fun markAsked() {
        askedSaveOnce = true
        sp?.edit()?.putBoolean("askedSaveOnce", true)?.apply()
    }

    /** 是否该弹「保存位置」对话框 */
    fun shouldAskSave(): Boolean = !noAsk || saveTreeUri == null

    val isEn: Boolean get() = lang == "en"

    /**
     * 系统环境更该走 Gitee 吗。
     *
     * 只读系统资源里的语言配置（不是进程的 [java.util.Locale.getDefault]，
     * 后者在启动早期可能还没被系统配置覆盖），再结合时区。
     * 中文系统直接 Gitee；非中文语言但人在东八区（中国大陆、中国港澳台、新加坡等）
     * 也按国内网络走 Gitee；其余才算海外环境；任何一项取不到一律按 Gitee 兜底。
     */
    private fun detectGiteePreference(ctx: Context): Boolean {
        val language = try {
            ctx.resources.configuration.locales.get(0)?.language?.lowercase().orEmpty()
        } catch (e: Exception) {
            ""
        }
        if (language.isBlank()) return true
        if (language.startsWith("zh")) return true

        val offset = try {
            java.util.TimeZone.getDefault()?.getOffset(System.currentTimeMillis())
        } catch (e: Exception) {
            null
        } ?: return true
        // 东八区 = UTC+8；用偏移判断而不是时区名，跨机型更稳
        return offset == 8 * 60 * 60 * 1000
    }
}

/** 非 Composable 环境（ViewModel / 工具函数）里取当前语言文案 */
fun tr(zh: String, en: String): String = if (AppPrefs.isEn) en else zh
