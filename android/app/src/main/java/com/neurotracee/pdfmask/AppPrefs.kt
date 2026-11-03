package com.neurotracee.pdfmask

import android.content.Context
import android.content.SharedPreferences
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/**
 * 全局偏好：语言、主题模式、保存位置。
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

    private var sp: SharedPreferences? = null

    fun init(ctx: Context) {
        if (sp != null) return
        val p = ctx.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)
        sp = p
        lang = if (p.getString("lang", "zh") == "en") "en" else "zh"
        themeMode = when (p.getString("themeMode", "system")) {
            "light", "dark" -> p.getString("themeMode", "system")!!
            else -> "system"
        }
        saveTreeUri = p.getString("saveTreeUri", null)
        rememberDir = p.getBoolean("rememberDir", true)
        noAsk = p.getBoolean("noAsk", false)
        askedSaveOnce = p.getBoolean("askedSaveOnce", false)
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

    fun markAsked() {
        askedSaveOnce = true
        sp?.edit()?.putBoolean("askedSaveOnce", true)?.apply()
    }

    /** 是否该弹「保存位置」对话框 */
    fun shouldAskSave(): Boolean = !noAsk || saveTreeUri == null

    val isEn: Boolean get() = lang == "en"
}

/** 非 Composable 环境（ViewModel / 工具函数）里取当前语言文案 */
fun tr(zh: String, en: String): String = if (AppPrefs.isEn) en else zh
