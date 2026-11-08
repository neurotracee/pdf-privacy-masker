package com.neurotracee.pdfmask.ui

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurotracee.pdfmask.Updater
import com.neurotracee.pdfmask.UpdateApk
import com.neurotracee.pdfmask.tr
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.launch
import java.io.File

/**
 * 这次结果是从哪个通道读到的。发生自动切换时据实说明一句，
 * 免得用户以为「我明明默认 Gitee，怎么跑去 GitHub 了」。
 */
@Composable
internal fun SourceNote(r: Updater.Result) {
    if (r.channel.isBlank()) return
    val text = when {
        r.fallbackFrom.isNotBlank() -> T(
            r.fallbackFrom + " 这次没连上，已经自动改用 " + r.channel + " 了。",
            r.fallbackFrom + " could not be reached, so " + r.channel + " was used instead."
        )
        else -> T(
            "本次从 " + r.channel + " 读取。",
            "Read from " + r.channel + "."
        )
    }
    Text(
        text,
        fontSize = 10.5.sp,
        lineHeight = 15.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.75f)
    )
}

/**
 * 「立即更新」这一块：应用内下载 + 交给系统安装器。
 *
 * 以前是把下载地址扔给浏览器，结果 Gitee 的 APK 附件带着 `application/zip` 的
 * MIME，浏览器就把文件存成 `xxx.apk.zip`，用户点了装不上。现在一律先自己下，
 * 下完核对包名和版本号，再拉起系统安装器；浏览器那条路留着，作为最后的退路。
 *
 * 两个入口（启动时的自动检查、设置里的手动检查）共用这一个组件，
 * 保证两处行为一字不差。
 */
@Composable
internal fun UpdateActionBlock(
    r: Updater.Result,
    accent: Color,
    onOpenBrowser: () -> Unit,
    onCopyLink: () -> Unit,
    onDone: () -> Unit = {}
) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()

    var downloading by remember(r) { mutableStateOf(false) }
    var percent by remember(r) { mutableStateOf(0) }
    var needPerm by remember(r) { mutableStateOf(false) }
    var started by remember(r) { mutableStateOf(false) }
    var error by remember(r) { mutableStateOf("") }
    var apk by remember(r) { mutableStateOf<File?>(null) }

    fun begin() {
        downloading = true
        percent = 0
        error = ""
        needPerm = false
        scope.launch {
            val f = UpdateApk.fetchAndInstall(
                ctx = ctx,
                url = r.url,
                version = r.latest
            ) { done, total ->
                percent = if (total > 0) ((done * 100) / total).toInt().coerceIn(0, 100) else 0
            }
            apk = f.apk
            downloading = false
            when (val o = f.outcome) {
                is UpdateApk.Outcome.Started -> {
                    started = true
                    onDone()
                }
                is UpdateApk.Outcome.NeedPermission -> needPerm = true
                is UpdateApk.Outcome.Failed -> error = o.reason
            }
        }
    }

    fun resume() {
        val f = apk ?: run { begin(); return }
        when (val o = UpdateApk.retryInstall(ctx, f)) {
            is UpdateApk.Outcome.Started -> {
                started = true
                needPerm = false
                onDone()
            }
            is UpdateApk.Outcome.NeedPermission -> needPerm = true
            is UpdateApk.Outcome.Failed -> error = o.reason
        }
    }

    val lifecycle = LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle) {
        val obs = LifecycleEventObserver { _, event ->
            // 用户去系统设置开了「安装应用」再回来：不用再点一次「去允许安装」
            if (event == Lifecycle.Event.ON_RESUME && needPerm && UpdateApk.canInstall(ctx)) {
                needPerm = false
            }
        }
        lifecycle.addObserver(obs)
        onDispose { lifecycle.removeObserver(obs) }
    }

    Column(Modifier.fillMaxWidth()) {
        // ---- 状态说明 ----
        Text(
            when {
                downloading -> T(
                    "正在下载 v" + r.latest + "… " + percent + "%（不用离开这个页面，下完直接弹出安装）",
                    "Downloading v" + r.latest + "… " + percent + "% — stay here, the installer opens by itself"
                )
                needPerm -> T(
                    "安装包已经下好了，但系统还没允许本应用「安装应用」。点「继续安装」会带你去开那个开关，" +
                        "开完回到这里再点一次就好。",
                    "The file is downloaded, but Android has not allowed this app to install apps yet. " +
                        "“Continue” takes you to that switch; turn it on and tap again when you come back."
                )
                started -> T(
                    "已经打开系统安装界面。装完覆盖旧版即可，不用先卸载。",
                    "The system installer is open. Install over the old version — no need to uninstall first."
                )
                error.isNotBlank() -> error
                else -> T(
                    "点「立即更新」直接在这里下载并安装，不用经过浏览器，也不用自己去文件夹里找文件。",
                    "Tap “Update now” and the app downloads and installs it here — no browser, no hunting for the file."
                )
            },
            fontSize = 11.5.sp,
            lineHeight = 18.sp,
            color = if (error.isNotBlank() && !downloading) Color(0xFFE5484D)
            else MaterialTheme.colorScheme.onSurfaceVariant
        )

        if (downloading) {
            Spacer(Modifier.height(8.dp))
            LinearProgressIndicator(
                progress = { percent / 100f },
                modifier = Modifier.fillMaxWidth(),
                color = accent
            )
        }

        // ---- 按钮 ----
        Spacer(Modifier.height(6.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Button(
                enabled = !downloading,
                onClick = {
                    when {
                        // 已经开了「安装应用」就直接装；还没开才带用户去开
                        needPerm && UpdateApk.canInstall(ctx) -> resume()
                        needPerm -> {
                            UpdateApk.openInstallPermission(ctx)
                            Toast.makeText(
                                ctx,
                                tr("打开开关后回到这里点「继续安装」", "Turn it on, then come back and tap “Continue”"),
                                Toast.LENGTH_LONG
                            ).show()
                        }
                        apk != null -> resume()
                        else -> begin()
                    }
                },
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = accent)
            ) {
                Text(
                    when {
                        downloading -> T("下载中 " + percent + "%", "Downloading " + percent + "%")
                        needPerm -> T("继续安装", "Continue")
                        apk != null -> T("继续安装", "Continue")
                        error.isNotBlank() -> T("重试", "Retry")
                        else -> T("立即更新", "Update now")
                    },
                    fontSize = 12.5.sp
                )
            }
            TextButton(enabled = !downloading, onClick = onOpenBrowser) {
                Text(T("用浏览器下载", "Browser"), fontSize = 12.sp)
            }
            TextButton(onClick = onCopyLink) {
                Text(T("复制链接", "Copy link"), fontSize = 12.sp)
            }
        }

        // ---- 走浏览器那条退路的提醒 ----
        if (error.isNotBlank() || started) {
            Text(
                T(
                    "如果改用浏览器下载：Gitee 有时会把文件存成「…apk.zip」，把结尾的 .zip 删掉就能正常安装。",
                    "If you use a browser instead: Gitee sometimes saves the file as “…apk.zip” — delete the " +
                        "trailing .zip and it installs fine."
                ),
                fontSize = 10.5.sp,
                lineHeight = 15.sp,
                fontWeight = FontWeight.Normal,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.85f),
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}
