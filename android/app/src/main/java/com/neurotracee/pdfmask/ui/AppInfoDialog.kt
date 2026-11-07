package com.neurotracee.pdfmask.ui

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.neurotracee.pdfmask.BuildConfig
import com.neurotracee.pdfmask.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun AppInfoDialog(onClose: () -> Unit) {
    Dialog(onDismissRequest = onClose) {
        Surface(
            shape = RoundedCornerShape(18.dp),
            color = MaterialTheme.colorScheme.surface
        ) {
            AboutPanel(onClose)
        }
    }
}

/** 关于面板本体（不含 Dialog 外壳，方便单独渲染与截图） */
@Composable
fun AboutPanel(
    onClose: () -> Unit,
    maxHeight: androidx.compose.ui.unit.Dp = 580.dp,
    /** 仅供测试注入：不为 null 时长按赞赏码只回调整，不真的写文件 */
    thanksOnLongPress: (() -> Unit)? = null
) {
    val dark = isSystemInDarkTheme()
    Column(
        Modifier
            .heightIn(max = maxHeight)
            .verticalScroll(rememberScrollState())
            .padding(22.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                T("PDF 隐私打码", "PDF Privacy Masker"),
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.width(8.dp))
            Text(
                "v" + BuildConfig.VERSION_NAME,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(4.dp))
        Text(
            T(
                "本地离线运行的 PDF 隐私信息自动打码工具",
                "Offline PDF privacy masking tool"
            ),
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(14.dp))
        Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        Spacer(Modifier.height(14.dp))

        InfoRow(
            T("指导作者", "Advisor"),
            T(
                "项目创作时为初中生。\n需求、识别规则的设计、验收测试全部由本人完成。",
                "Was a junior high school student when this project was created.\n" +
                    "Requirements, detection rule design, and acceptance testing were all completed by the author."
            )
        )
        InfoRow(T("开发", "Built by"), "腾讯 WorkBuddy × DeepSeek-V4.1-Flash")
        InfoRow(T("开源协议", "License"), "AGPL-3.0-or-later")
        InfoRow(T("原项目地址", "Upstream"), "github.com/neurotracee/pdf-privacy-masker")
        // 国内访问 GitHub 常被拦，声明里再给一个 Gitee 镜像，方便追溯来源
        InfoRow(T("镜像地址", "Mirror"), "gitee.com/bio234/pdf-privacy-masker")

        Spacer(Modifier.height(14.dp))
        Note(T("隐私", "Privacy"))
        Text(
            T(
                "没有存储权限，也没有后台联网。唯一的网络权限只用在检查更新：默认启动时自动查一次，" +
                    "也可以在设置里改成纯手动，那样只有你点「检查更新」才联网。联网时只向 Gitee（国内默认）" +
                    "或 GitHub 读一个公开的版本号，不传文件、不传任何个人信息。断网时直接跳过，不会卡住也不会提示。" +
                    "选文件走系统文件选择器，只拿到你挑中的那一个文件的临时读取权；" +
                    "保存时由你当场决定写到哪里。识别和打码全程本地完成。",
                "No storage permission, no background networking. The single network permission is used for the " +
                    "update check only — once at launch by default, or only when you tap Check for updates if you " +
                    "switch to manual in Settings. It just reads one public version number from Gitee (the default " +
                    "in mainland China) or GitHub: no files, no personal data. Offline, the check is skipped " +
                    "silently. Files come through the system picker, so the app only gets " +
                    "temporary read access to the one file you chose, and you decide where output is written. " +
                    "Detection and masking always run on-device."
            ),
            fontSize = 11.5.sp,
            lineHeight = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(12.dp))
        Note(T("输出说明", "Output"))
        Text(
            T(
                "打码后把每页重新渲染成图片、再组装成新的 PDF，所以输出文件里不含任何文字层；" +
                    "代价是文字不可复制、文件比原文件大。",
                "Each page is re-rendered as an image and rebuilt into a new PDF, so the output has no text " +
                    "layer at all. The trade-off: text can't be copied and the file is larger."
            ),
            fontSize = 11.5.sp,
            lineHeight = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(12.dp))
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(10.dp))
                .background(if (dark) Color(0xFF3B2F14) else Color(0xFFFFF7E8))
                .padding(12.dp)
        ) {
            val c = if (dark) Color(0xFFFFC46B) else Color(0xFF8A5A00)
            Column {
                Text(
                    T("二次开发 / 商用：三条硬要求", "Forks / commercial use: three requirements"),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = c
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    T(
                        "① 保留「指导作者：项目创作时为初中生」的署名，不得删改。\n" +
                            "② 在你的程序里标注原项目地址，让使用者看得见（关于页、页脚、帮助菜单均可）。\n" +
                            "③ 改动过的版本请注明「本程序基于该地址修改，非原作者发布」。",
                        "① Keep the credit “Advisor: was a junior high school student when this project was created”, unmodified.\n" +
                            "② Show the upstream URL somewhere users can see (about page, footer, help menu).\n" +
                            "③ Modified builds must state: “Based on that project, not released by the original author.”"
                    ),
                    fontSize = 11.5.sp,
                    lineHeight = 19.sp,
                    color = c
                )
            }
        }

        Spacer(Modifier.height(10.dp))
        Text(
            T(
                "维护节奏：我平时没有充足的时间和精力，大概一两个月才上来看一两次，" +
                    "所以回复不会很快，别指望秒回。代码全部公开，修不动的地方欢迎你自己改、自己接着用；" +
                    "协议允许商用，不用付钱也不用问我，照上面三条做就行。",
                "Maintenance: I don't usually have enough time or energy for this project, so I only drop by " +
                    "once every month or two — replies may be slow. " +
                    "The code is fully open, so please feel free to fix or extend it yourself. Commercial use is " +
                    "allowed: no payment, no permission needed, just follow the three points above."
            ),
            fontSize = 11.sp,
            lineHeight = 17.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(16.dp))
        Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
        Spacer(Modifier.height(14.dp))
        ThanksBlock(thanksOnLongPress)

        Spacer(Modifier.height(18.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            Button(
                onClick = onClose,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Text(T("知道了", "Got it"), fontSize = 13.sp)
            }
        }
    }
}

/** 赞赏码：白底本身是一张图，深浅色都放进同一张圆角白卡里，像一张贴纸 */
@Composable
private fun ThanksBlock(onLongPressOverride: (() -> Unit)? = null) {
    val ctx = LocalContext.current
    val haptic = LocalHapticFeedback.current
    val scope = rememberCoroutineScope()
    var saving by remember { mutableStateOf(false) }

    fun tip(msg: String) = Toast.makeText(ctx, msg, Toast.LENGTH_SHORT).show()

    // 8.0 / 9.0 没有相册写入权限，改用系统「保存到…」选择器，全程零权限
    val picker = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("image/png")
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        tip(
            if (ThanksQr.writeTo(ctx, uri)) t("已保存", "Saved")
            else t("保存失败，可以截屏后用微信提取文字", "Couldn't save — try a screenshot instead")
        )
    }

    fun saveQr() {
        if (onLongPressOverride != null) {
            onLongPressOverride()
            return
        }
        if (saving) return
        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
        if (!ThanksQr.canSaveToGallery()) {
            picker.launch(ThanksQr.FILE_NAME)
            return
        }
        saving = true
        scope.launch {
            val msg = try {
                val path = withContext(Dispatchers.IO) { ThanksQr.saveToGallery(ctx) }
                t("已保存到相册：$path", "Saved to gallery: $path")
            } catch (e: Exception) {
                t("保存失败，可以截屏后用微信提取文字", "Couldn't save — try a screenshot instead")
            }
            saving = false
            tip(msg)
        }
    }

    Column(Modifier.fillMaxWidth()) {
        Text(
            T("如果这个工具帮到了你", "If this tool helped you"),
            fontSize = 12.5.sp,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(Modifier.height(4.dp))
        Text(
            T(
                "本来就是顺手做的小工具，能派上用场就挺好。",
                "It began as a small side project, and I'm glad it's useful."
            ),
            fontSize = 11.5.sp,
            lineHeight = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        // ---- 点 Star：不打赏也能帮上忙的那条路 ----
        Spacer(Modifier.height(10.dp))
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
                        T("给仓库点个 Star", "Star the repository"),
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        T(
                            "不想花钱也没关系，点一颗 Star 就是最好的支持——别人搜得到，我才更有动力维护。",
                            "No money needed — a star is the best support: it helps others find the project, " +
                                "and it keeps me motivated."
                        ),
                        fontSize = 11.sp,
                        lineHeight = 16.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(Modifier.width(8.dp))
                TextButton(onClick = { openRepo(ctx) }) {
                    Text(T("去点 Star", "Star it"), fontSize = 12.5.sp)
                }
            }
        }

        Spacer(Modifier.height(12.dp))
        Text(
            T(
                "国内用户：愿意的话可以请我喝杯奶茶，完全自愿，不打赏也一样免费、功能不缺。",
                "In China? You can buy me a milk tea if you feel like it — entirely optional; the app stays " +
                    "free and fully functional either way."
            ),
            fontSize = 11.5.sp,
            lineHeight = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(8.dp))
        Box(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color.White)
                .padding(vertical = 12.dp)
                .pointerInput(Unit) {
                    detectTapGestures(onLongPress = { saveQr() })
                },
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(R.drawable.thanks_qr),
                contentDescription = T("赞赏码", "Tip QR code"),
                contentScale = ContentScale.Fit,
                modifier = Modifier
                    .width(302.dp)
                    .aspectRatio(1000f / 670f)
            )
        }
        Spacer(Modifier.height(6.dp))
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                T(
                    "微信扫码 · 金额随意 · 长按图片可保存",
                    "Scan in WeChat · any amount · long-press to save"
                ),
                fontSize = 10.5.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                textAlign = TextAlign.Center
            )
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
            TextButton(enabled = !saving, onClick = { saveQr() }) {
                Text(
                    if (saving) T("保存中…", "Saving…") else T("保存赞赏码", "Save the QR"),
                    fontSize = 12.sp
                )
            }
        }
    }
}

@Composable
private fun InfoRow(k: String, v: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(
            k,
            fontSize = 12.5.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.width(82.dp)
        )
        Text(
            v,
            fontSize = 12.5.sp,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.Medium,
            lineHeight = 18.sp,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun Note(t: String) {
    Text(
        t,
        fontSize = 12.sp,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.onSurface,
        modifier = Modifier.padding(bottom = 4.dp)
    )
}
