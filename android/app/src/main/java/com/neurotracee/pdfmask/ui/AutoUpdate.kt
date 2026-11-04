package com.neurotracee.pdfmask.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.neurotracee.pdfmask.BuildConfig
import com.neurotracee.pdfmask.Updater
import com.neurotracee.pdfmask.tr
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.withTimeoutOrNull

/** 网络慢到什么程度才值得弹一个「正在检查」——快的时候连提示都不闪 */
private const val SLOW_HINT_MS = 1_200L

/** 自动检查的总预算：超了就当成网络不通，静默放行 */
private const val AUTO_BUDGET_MS = 12_000L

/**
 * 启动时的自动检查更新。和「设置 → 检查更新」走同一套 [Updater]，
 * 只是把结果做成一个可以先关掉的全屏对话框。
 *
 * 行为约定（对应 v1.4.2 的需求）：
 * - 断网 / 超时 / 已是最新：什么都不显示，直接进主程序；
 * - 检查超过 1.2 秒还没回来：显示「正在检查」，右上角有关闭按钮，随时能跳过；
 * - 发现新版本：自动用默认浏览器打开发布页，同时给「用浏览器下载」和「复制链接」两条路；
 * - 发布正文标了「更新级别：强烈建议」：提醒更醒目，但还是能关；
 * - 用户点「暂不更新」：先劝一次（挽留），点「仍然用旧版」就真的放行，不再纠缠。
 */
@Composable
fun AutoUpdateGate() {
    val ctx = LocalContext.current
    var checking by remember { mutableStateOf(false) }
    var skipped by remember { mutableStateOf(false) }
    var stuck by remember { mutableStateOf(false) }
    var result by remember { mutableStateOf<Updater.Result?>(null) }
    var opened by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val job = async(Dispatchers.IO) { Updater.check(BuildConfig.VERSION_NAME) }

        // 第一段：1.2 秒内就完成的，一律不打扰
        var r = withTimeoutOrNull(SLOW_HINT_MS) { job.await() }
        if (r == null) {
            checking = true
            val left = AUTO_BUDGET_MS - SLOW_HINT_MS
            r = withTimeoutOrNull(left) { job.await() }
            checking = false
        }

        // 拿不到结果 = 超时；ok=false = 断网 / 没包。两种情况都静默，不进主程序之外的东西
        val res = r ?: run { stuck = true; return@LaunchedEffect }
        if (!res.ok || !res.hasUpdate) return@LaunchedEffect
        // 用户已经在「正在检查」里点了跳过，就不再拦他
        if (skipped) return@LaunchedEffect

        opened = openUrlInBrowser(ctx, res.url)
        result = res
    }

    if (checking && !skipped && result == null) {
        UpdateDialog(
            title = T("正在检查更新", "Checking for updates"),
            body = T(
                "正在向 GitHub 读一次版本号，不传任何文件。\n网络慢的话可以直接关掉，不影响使用。",
                "Reading the latest version number from GitHub. No files are sent.\nIf the network is slow, just close this — the app works fine without it."
            ),
            busy = true,
            onClose = { skipped = true }
        )
    }

    if (stuck && !skipped && result == null) {
        UpdateDialog(
            title = T("检查更新没有回应", "Update check timed out"),
            body = T(
                "网络似乎不通，已经跳过了这次检查，可以直接使用。\n" +
                    "想再试一次：设置 → 版本与更新 → 检查更新。",
                "The network looks unreachable, so the check was skipped — you can go ahead.\n" +
                    "To retry later: Settings → Version & updates → Check."
            ),
            busy = false,
            onClose = { skipped = true }
        )
    }

    val res = result
    if (res != null) {
        AutoUpdateResult(
            r = res,
            opened = opened,
            onOpen = { opened = openUrlInBrowser(ctx, res.url) },
            onClose = { result = null }
        )
    }
}

/** 发现新版本时的窗口。两档都只是「建议」：永远留着关闭，只在真关之前劝一次 */
@Composable
private fun AutoUpdateResult(
    r: Updater.Result,
    opened: Boolean,
    onOpen: () -> Unit,
    onClose: () -> Unit
) {
    val ctx = LocalContext.current
    val strong = r.strong
    val accent = if (strong) Color(0xFFE5484D) else MaterialTheme.colorScheme.primary

    // 第一次想关：先换成挽留界面；再点一次「仍然用旧版」就真的放行，不再纠缠
    var pleading by remember(r) { mutableStateOf(false) }
    val tryClose: () -> Unit = { if (pleading) onClose() else pleading = true }

    Dialog(
        onDismissRequest = tryClose,
        properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = true)
    ) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                Modifier
                    .heightIn(max = (LocalConfiguration.current.screenHeightDp * 0.8f).dp)
                    .verticalScroll(rememberScrollState())
                    .padding(22.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        when {
                            pleading && strong -> T("再看一眼，好吗？", "One more look?")
                            pleading -> T("确定先不更新吗？", "Skip this update?")
                            strong -> T("强烈建议更新到 v" + r.latest, "Strongly suggested: v" + r.latest)
                            else -> T("发现新版本 v" + r.latest, "New version v" + r.latest)
                        },
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (pleading) MaterialTheme.colorScheme.onSurface else accent,
                        modifier = Modifier.weight(1f)
                    )
                    TextButton(onClick = tryClose) {
                        Text(
                            if (pleading) T("关闭", "Close") else T("以后再说", "Later"),
                            fontSize = 12.5.sp
                        )
                    }
                }

                if (!pleading) {
                    Spacer(Modifier.height(6.dp))
                    Surface(shape = RoundedCornerShape(999.dp), color = accent.copy(alpha = 0.12f)) {
                        Text(
                            if (strong) T("强烈建议更新", "Strongly suggested")
                            else T("建议更新", "Suggested"),
                            Modifier.padding(horizontal = 9.dp, vertical = 3.dp),
                            fontSize = 11.sp,
                            color = accent
                        )
                    }
                }

                Spacer(Modifier.height(9.dp))
                Text(
                    when {
                        pleading && strong -> T(
                            "这个版本修的是一上手就会碰到的问题——旧版里那些反复出错、只能一遍遍重来的地方，" +
                                "新版已经处理好了。花一分钟换上，往后能省下不少时间。\n\n" +
                                "当然，换不换还是你说了算：点「我还是要用旧版」就能继续用，" +
                                "下次打开只会再提醒你一次而已。",
                            "This release fixes the things you run into as soon as you start using it — the " +
                                "repeated failures and retries are gone. One minute to install saves you a lot " +
                                "of hassle later.\n\nIt is still your call: tap “I'll stay on the old version” " +
                                "to keep using it. You will just be reminded once next time."
                        )
                        pleading -> T(
                            "不更新也能照常用，只是新版顺手修了几个小毛病，用起来更稳。\n\n" +
                                "下次打开还会再提醒一次，到时候想换也来得及。",
                            "The app works fine without it — the new build just tidies up a few rough edges " +
                                "and is steadier.\n\nYou will be reminded once more next time, so you can " +
                                "always switch later."
                        )
                        strong -> T(
                            "当前是 v" + r.current + "。这一版修了一直在影响使用的问题，强烈建议尽快换上——" +
                                "更新只要一分钟，原来的功能都在，文件也始终留在你的手机里。",
                            "You are on v" + r.current + ". This build fixes problems that keep getting in the " +
                                "way, so updating is strongly suggested — it takes a minute, everything keeps " +
                                "working, and your files never leave your phone."
                        )
                        else -> T(
                            "当前是 v" + r.current + "。新版修了几个已知问题，也让你少踩点坑——" +
                                "不更新也能继续用，但新版更稳。",
                            "You are on v" + r.current + ". The new build fixes a few known problems and is more " +
                                "reliable — you can keep using this version, but updating is worth it."
                        )
                    },
                    fontSize = 12.5.sp,
                    lineHeight = 20.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                if (!pleading) {
                    Spacer(Modifier.height(12.dp))
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = accent.copy(alpha = 0.08f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            Text(
                                if (opened) T(
                                    "已经让浏览器去下载了。下载完点开安装，覆盖安装即可，不用先卸载。",
                                    "Your browser is fetching the new build. When it finishes, just install it over " +
                                        "the old one — no need to uninstall first."
                                ) else T(
                                    "没能自动打开浏览器。点下面的「用浏览器下载」再试一次，或者复制链接自己粘到浏览器。",
                                    "The browser did not open. Try “Download in browser” below, or copy the link " +
                                        "and paste it into a browser yourself."
                                ),
                                fontSize = 11.5.sp,
                                lineHeight = 18.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Row(
                                Modifier.padding(top = 6.dp),
                                horizontalArrangement = Arrangement.spacedBy(2.dp)
                            ) {
                                TextButton(onClick = onOpen) {
                                    Text(T("用浏览器下载", "Download in browser"), fontSize = 12.sp)
                                }
                                TextButton(onClick = { copyLinkToClipboard(ctx, r.url) }) {
                                    Text(T("复制链接", "Copy link"), fontSize = 12.sp)
                                }
                            }
                            Text(
                                r.url,
                                fontSize = 10.5.sp,
                                lineHeight = 15.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f)
                            )
                        }
                    }
                }

                Spacer(Modifier.height(14.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = if (pleading) onClose else tryClose) {
                        Text(
                            when {
                                pleading && strong -> T("我还是要用旧版", "I'll stay on the old version")
                                pleading -> T("先这样，下次再说", "Skip for now")
                                else -> T("暂不更新", "Not now")
                            },
                            fontSize = 13.sp
                        )
                    }
                    Spacer(Modifier.width(6.dp))
                    Button(
                        onClick = {
                            onOpen()
                            // 挽留里点了「现在就更新」：回到正常的下载说明，让用户看到「已经让浏览器去下载了」
                            if (pleading) pleading = false
                        },
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = accent)
                    ) {
                        Text(
                            if (pleading) T("好，现在更新", "Okay, update now")
                            else T("立即更新", "Update now"),
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }
}

/** 通用的「一条标题 + 一段话 + 一个关闭」窗口，供检查中 / 超时两种状态使用 */
@Composable
private fun UpdateDialog(
    title: String,
    body: String,
    busy: Boolean,
    onClose: () -> Unit
) {
    Dialog(
        onDismissRequest = onClose,
        properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = true)
    ) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(22.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        title,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.weight(1f)
                    )
                    if (busy) {
                        CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    }
                }
                Spacer(Modifier.height(8.dp))
                Text(
                    body,
                    fontSize = 12.5.sp,
                    lineHeight = 20.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(14.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    Button(
                        onClick = onClose,
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text(
                            if (busy) T("跳过，先进入", "Skip and continue")
                            else T("进入主程序", "Continue"),
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }
    }
}

/** 用系统默认浏览器打开；打不开返回 false，交给界面给备选路径 */
internal fun openUrlInBrowser(ctx: Context, url: String): Boolean = try {
    ctx.startActivity(
        Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    )
    true
} catch (e: Exception) {
    false
}

internal fun copyLinkToClipboard(ctx: Context, url: String) {
    val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
    cm?.setPrimaryClip(ClipData.newPlainText("releases", url))
    Toast.makeText(
        ctx,
        tr("链接已复制，粘到浏览器里打开", "Link copied — paste it into your browser"),
        Toast.LENGTH_SHORT
    ).show()
}

/** 供首页/关于页复用的「去仓库点 Star」地址 */
internal const val REPO_URL = "https://github.com/neurotracee/pdf-privacy-masker"

internal fun openRepo(ctx: Context) {
    if (!openUrlInBrowser(ctx, REPO_URL)) copyLinkToClipboard(ctx, REPO_URL)
}
