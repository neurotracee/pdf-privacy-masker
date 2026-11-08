package com.neurotracee.pdfmask.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.neurotracee.pdfmask.AppPrefs
import com.neurotracee.pdfmask.BuildConfig
import com.neurotracee.pdfmask.Updater
import com.neurotracee.pdfmask.tr
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun SettingsDialog(
    onClose: () -> Unit,
    onPickSaveDir: () -> Unit,
    onShowAbout: () -> Unit
) {
    Dialog(onDismissRequest = onClose) {
        Surface(
            shape = RoundedCornerShape(18.dp),
            color = MaterialTheme.colorScheme.surface
        ) {
            SettingsPanel(onClose, onPickSaveDir, onShowAbout)
        }
    }
}

/** 设置面板本体（不含 Dialog 外壳，便于单独渲染） */
@Composable
fun SettingsPanel(
    onClose: () -> Unit,
    onPickSaveDir: () -> Unit,
    onShowAbout: () -> Unit
) {
    // 内容比早先多了「版本与更新」，按屏高给个上限，常见机型一屏能看全，小屏仍可滚动
    val maxH = (LocalConfiguration.current.screenHeightDp * 0.88f).dp
    Column(
        Modifier
            .heightIn(max = maxH)
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                T("设置", "Settings"),
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.weight(1f))
            TextButton(onClick = onClose) {
                Text(T("完成", "Done"), fontSize = 13.sp)
            }
        }

        Spacer(Modifier.height(6.dp))
        Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        Spacer(Modifier.height(14.dp))

        // ---- 语言 ----
        SectionLabel(T("界面语言", "Language"))
        Spacer(Modifier.height(8.dp))
        Segmented(
            options = listOf("中文" to "zh", "English" to "en"),
            selected = AppPrefs.lang,
            onSelect = { AppPrefs.updateLang(it) }
        )

        Spacer(Modifier.height(18.dp))

        // ---- 主题 ----
        SectionLabel(T("外观", "Appearance"))
        Spacer(Modifier.height(8.dp))
        Segmented(
            options = listOf(
                T("跟随系统", "System") to "system",
                T("浅色", "Light") to "light",
                T("深色", "Dark") to "dark"
            ),
            selected = AppPrefs.themeMode,
            onSelect = { AppPrefs.updateTheme(it) }
        )
        Spacer(Modifier.height(6.dp))
        Text(
            T(
                "选「跟随系统」时，会随手机的深色模式自动切换。",
                "With “System”, the app follows your phone's dark mode."
            ),
            fontSize = 11.5.sp,
            lineHeight = 17.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(18.dp))

        // ---- 保存位置 ----
        SectionLabel(T("保存位置", "Save location"))
        Spacer(Modifier.height(8.dp))
        Surface(
            shape = RoundedCornerShape(10.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        prettyTree(AppPrefs.saveTreeUri)
                            ?: T("未设置（每次都会问你）", "Not set — you'll be asked each time"),
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1
                    )
                    Text(
                        T("打码后的文件存到这里", "Masked PDFs are saved here"),
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(Modifier.width(8.dp))
                TextButton(onClick = onPickSaveDir) {
                    Text(T("选择", "Choose"), fontSize = 12.5.sp)
                }
            }
        }
        Spacer(Modifier.height(4.dp))
        CheckRow(
            checked = !AppPrefs.noAsk,
            label = T(
                "生成前先问我保存到哪里",
                "Ask me where to save before generating"
            ),
            onCheck = { AppPrefs.updateNoAsk(!it) }
        )
        Text(
            T(
                "取消勾选后，会直接静默保存到上面的文件夹；原 PDF 只读不改。",
                "Unchecked: files go straight to the folder above. The original PDF is never modified."
            ),
            fontSize = 11.sp,
            lineHeight = 16.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 2.dp)
        )

        Spacer(Modifier.height(18.dp))

        // ---- 版本与更新 ----
        UpdateSection()

        Spacer(Modifier.height(18.dp))
        Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        Spacer(Modifier.height(12.dp))
        Surface(
            onClick = onShowAbout,
            shape = RoundedCornerShape(10.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                Modifier.padding(horizontal = 12.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    T("关于与开源信息", "About & license"),
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.weight(1f))
                Text("›", fontSize = 16.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.height(6.dp))
    }
}

/**
 * 两三个选项的分段选择器。
 *
 * 选项文案长短不一时（例如「Gitee（建议中国大陆用户）」）会折成两行，
 * 所以这里统一：按钮等高、文字居中、行高放宽——不会出现一项顶对齐、
 * 一项底对齐的错位。
 */
@Composable
private fun Segmented(options: List<Pair<String, String>>, selected: String, onSelect: (String) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(3.dp),
        horizontalArrangement = Arrangement.spacedBy(3.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        options.forEach { (label, key) ->
            val on = key == selected
            Box(
                Modifier
                    .weight(1f)
                    .defaultMinSize(minHeight = 40.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(if (on) MaterialTheme.colorScheme.surface else Color.Transparent)
                    .clickable { onSelect(key) }
                    .padding(horizontal = 4.dp, vertical = 8.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    label,
                    fontSize = if (label.length > 10) 12.sp else 13.sp,
                    lineHeight = 16.sp,
                    textAlign = TextAlign.Center,
                    fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal,
                    color = if (on) MaterialTheme.colorScheme.onSurface
                    else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

/**
 * 竖排单选。文案较长（「Gitee（建议中国大陆用户）」、英文更长）时，
 * 一列放不下会折行，分段按钮又会被挤成两行不等高，所以单独用列表：
 * 每项一行、整行可点，选中的那项带主色边框和圆点。
 */
@Composable
private fun ChoiceList(options: List<Pair<String, String>>, selected: String, onSelect: (String) -> Unit) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        options.forEach { (label, key) ->
            val on = key == selected
            Surface(
                onClick = { onSelect(key) },
                shape = RoundedCornerShape(10.dp),
                color = if (on) MaterialTheme.colorScheme.primary.copy(alpha = 0.10f)
                else MaterialTheme.colorScheme.surfaceVariant,
                border = if (on) BorderStroke(1.dp, MaterialTheme.colorScheme.primary) else null,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    Modifier.padding(horizontal = 12.dp, vertical = 11.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    RadioButton(
                        selected = on,
                        onClick = { onSelect(key) },
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        label,
                        fontSize = 12.5.sp,
                        lineHeight = 17.sp,
                        fontWeight = if (on) FontWeight.SemiBold else FontWeight.Normal,
                        color = if (on) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

@Composable
private fun CheckRow(checked: Boolean, label: String, onCheck: (Boolean) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onCheck(!checked) }
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Checkbox(
            checked = checked,
            onCheckedChange = { onCheck(it) },
            modifier = Modifier.size(36.dp),
            colors = CheckboxDefaults.colors(
                checkedColor = MaterialTheme.colorScheme.primary,
                uncheckedColor = MaterialTheme.colorScheme.outline
            )
        )
        Spacer(Modifier.width(6.dp))
        Text(label, fontSize = 12.5.sp, color = MaterialTheme.colorScheme.onSurface)
    }
}

/** 把 SAF 的 tree uri 变成能看懂的名字 */
fun prettyTree(uri: String?): String? {
    if (uri.isNullOrBlank()) return null
    val decoded = Uri.decode(uri)
    val seg = decoded.substringAfter("tree/", "").substringAfterLast(":", "")
    val fallback = decoded.substringAfterLast('/')
    val name = seg.ifBlank { fallback }
    return name.ifBlank { null }
}

/**
 * 检查更新：只有手动点一下才会联网，只读 GitHub 上的版本号。
 * 有新版本直接用默认浏览器打开下载；跳不过去就给链接、复制按钮和排查清单。
 */
@Composable
private fun UpdateSection() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val current = BuildConfig.VERSION_NAME
    var busy by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<Updater.Result?>(null) }
    var opened by remember { mutableStateOf<Boolean?>(null) }

    fun openInBrowser(url: String): Boolean = try {
        ctx.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(url))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
        true
    } catch (e: Exception) {
        false
    }

    fun copyLink(url: String) {
        val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
        cm?.setPrimaryClip(ClipData.newPlainText("releases", url))
        Toast.makeText(
            ctx,
            tr("链接已复制，粘到浏览器里打开", "Link copied — paste it into your browser"),
            Toast.LENGTH_SHORT
        ).show()
    }

    // ---- 更新检查方式 ----
    SectionLabel(T("更新检查方式", "Update checking"))
    Spacer(Modifier.height(8.dp))
    Segmented(
        options = listOf(
            T("自动检查（启动时）", "Automatic") to "auto",
            T("手动检查", "Manual only") to "manual"
        ),
        selected = if (AppPrefs.autoCheck) "auto" else "manual",
        onSelect = { AppPrefs.updateAutoCheck(it == "auto") }
    )
    Spacer(Modifier.height(6.dp))
    Text(
        T(
            "自动：每次启动在后台静默查一次，没网就不响。手动：只有点下面的「检查更新」才联网。",
            "Automatic: one silent check at every launch, skipped when offline. Manual: only the button below goes online."
        ),
        fontSize = 11.sp,
        lineHeight = 16.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )

    Spacer(Modifier.height(14.dp))

    // ---- 更新源 ----
    SectionLabel(T("更新源", "Update source"))
    Spacer(Modifier.height(8.dp))
    ChoiceList(
        options = listOf(
            T("Gitee（建议中国大陆用户）", "Gitee (recommended in mainland China)") to "gitee",
            T("GitHub（海外用户）", "GitHub (outside mainland China)") to "github"
        ),
        selected = AppPrefs.resolvedUpdateSource,
        onSelect = { AppPrefs.updateUpdateSource(it) }
    )
    Spacer(Modifier.height(6.dp))
    Text(
        T(
            "默认按系统语言自动选（简体中文 → Gitee）。选中的源连不上会自动换另一个再试。",
            "Picked from your system language by default (Simplified Chinese → Gitee). If it is unreachable, the other one is tried."
        ),
        fontSize = 11.sp,
        lineHeight = 16.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )

    Spacer(Modifier.height(18.dp))

    SectionLabel(T("版本与更新", "Version & updates"))
    Spacer(Modifier.height(8.dp))
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(
                T("当前版本", "Current") + " v" + current,
                fontSize = 13.sp,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(
                T(
                    "查到的更新来自下面的更新源",
                    "Updates come from the source below"
                ),
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        TextButton(
            enabled = !busy,
            onClick = {
                busy = true
                result = null
                opened = null
                scope.launch {
                    val r = withContext(Dispatchers.IO) {
                        Updater.check(current, AppPrefs.updateSource)
                    }
                    result = r
                    if (r.ok && r.hasUpdate) opened = openInBrowser(r.url)
                    busy = false
                }
            }
        ) {
            Text(
                if (busy) T("检查中…", "Checking…") else T("检查更新", "Check"),
                fontSize = 12.5.sp
            )
        }
    }

    if (busy) {
        Row(
            Modifier.padding(top = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            CircularProgressIndicator(Modifier.size(14.dp), strokeWidth = 2.dp)
            Spacer(Modifier.width(8.dp))
            Text(
                T("正在连接更新源…", "Contacting the update source…"),
                fontSize = 11.5.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        return
    }

    val r = result ?: return
    Spacer(Modifier.height(10.dp))
    UpdateResultCard(
        r = r,
        opened = opened,
        onOpen = { url -> opened = openInBrowser(url) },
        onCopy = { url -> copyLink(url) }
    )
}

/** 检查结果卡片：最新 / 有新版 / 失败三种形态，独立出来便于单独渲染核对 */
@Composable
internal fun UpdateResultCard(
    r: Updater.Result,
    opened: Boolean?,
    onOpen: (String) -> Unit,
    onCopy: (String) -> Unit
) {
    val accent = when {
        !r.ok -> Color(0xFFE5484D)
        r.hasUpdate -> MaterialTheme.colorScheme.primary
        else -> Color(0xFF12A150)
    }
    Spacer(Modifier.height(10.dp))
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = accent.copy(alpha = 0.08f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(12.dp)) {
            Text(
                when {
                    !r.ok -> T("检查失败", "Check failed")
                    r.hasUpdate -> T("发现新版本 v" + r.latest, "New version v" + r.latest)
                    else -> T("已是最新版本", "Already up to date")
                },
                fontSize = 12.5.sp,
                fontWeight = FontWeight.SemiBold,
                color = accent
            )
            Spacer(Modifier.height(3.dp))
            Text(
                when {
                    !r.ok -> r.detail
                    r.hasUpdate -> if (opened == true)
                        T(
                            "当前 v" + r.current + "，已经让浏览器去下载了。",
                            "You have v" + r.current + "; your browser is fetching the new build."
                        )
                    else
                        T(
                            "当前 v" + r.current + "，但没能自动打开浏览器，点下面的按钮再试一次。",
                            "You have v" + r.current + ", but the browser did not open — try the buttons below."
                        )
                    else -> T(
                        "当前 v" + r.current + "，仓库里最新的也是这个版本。",
                        "You have v" + r.current + ", which is already the newest release."
                    )
                },
                fontSize = 11.5.sp,
                lineHeight = 17.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            // 有新版时：一行摘要 + 按 Windows / 安卓 分开的详细条目，
            // 和启动时自动检查弹出的窗口用的是同一套组件。
            if (r.hasUpdate) {
                Spacer(Modifier.height(8.dp))
                UpdateNotesBlock(
                    r = r,
                    accent = accent,
                    onOpenPage = { onOpen(r.page) }
                )
            }

            if (!r.ok || r.hasUpdate) {
                Row(
                    Modifier.padding(top = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(2.dp)
                ) {
                    if (r.hasUpdate) {
                        TextButton(onClick = { onOpen(r.url) }) {
                            Text(T("用浏览器下载", "Download"), fontSize = 12.sp)
                        }
                    }
                    TextButton(onClick = { onOpen(r.url) }) {
                        Text(T("打开发布页", "Open page"), fontSize = 12.sp)
                    }
                    TextButton(onClick = { onCopy(r.url) }) {
                        Text(T("复制链接", "Copy link"), fontSize = 12.sp)
                    }
                }
                Text(
                    T(
                        "跳不过去？按顺序看：\n" +
                            "① 网络：是不是开了飞行模式；校园网、公司网常会拦 GitHub。\n" +
                            "② 浏览器：设置 → 应用 → 默认应用，看看浏览器有没有被停用。\n" +
                            "③ 本应用的网络权限：个别安全软件会单独限制，去权限管理里放开。\n" +
                            "都不行就点「复制链接」自己粘到浏览器；最后还可以截屏这一屏，" +
                            "用微信「提取文字」把链接抠出来手动输入。",
                        "Still blocked? Check in order:\n" +
                            "① Network: is airplane mode on? Campus and corporate Wi-Fi often block GitHub.\n" +
                            "② Browser: Settings → Apps → Default apps — is a browser installed and enabled?\n" +
                            "③ This app's network permission: some security suites restrict it separately.\n" +
                            "Otherwise tap “Copy link” and paste it yourself — or screenshot this screen and " +
                            "use text recognition to pull the link out."
                    ),
                    fontSize = 11.sp,
                    lineHeight = 17.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}
