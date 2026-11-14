package com.neurotracee.pdfmask.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurotracee.pdfmask.AppPrefs
import com.neurotracee.pdfmask.ReleaseDigest
import com.neurotracee.pdfmask.Updater
import com.neurotracee.pdfmask.tr

/**
 * 更新弹窗里那两段文字（v1.4.4）：顶上一行 100 字以内的摘要，
 * 下面按 Windows / 安卓 列出详细条目，末尾一条「具体详见 Release 页面」。
 *
 * 「启动时自动检查」和「设置 → 检查更新」共用这一个组件，保证两处看到的东西一样。
 * 发布正文里没有摘要也没有条目时整块不渲染，界面回到原来的样子。
 */
@Composable
internal fun UpdateNotesBlock(
    r: Updater.Result,
    accent: Color,
    onOpenPage: () -> Unit
) {
    val n = r.digest?.pick(AppPrefs.isEn)
    val hasNotes = n != null && (n.brief.isNotBlank() || n.items.isNotEmpty())

    if (n != null && hasNotes) {
        if (n.brief.isNotBlank()) {
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = accent.copy(alpha = 0.07f),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(Modifier.padding(horizontal = 11.dp, vertical = 9.dp)) {
                    Text(
                        n.brief,
                        fontSize = 12.5.sp,
                        lineHeight = 19.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }

        if (n.items.isNotEmpty()) {
            Spacer(Modifier.height(4.dp))
            n.items.forEachIndexed { i, item ->
                if (i > 0) {
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.35f))
                    )
                }
                Column(Modifier.padding(vertical = 7.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        PlatformTag(item.platform)
                        Text(
                            item.title,
                            fontSize = 12.sp,
                            lineHeight = 17.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.padding(start = 6.dp)
                        )
                    }
                    if (item.lines.isNotEmpty()) {
                        Spacer(Modifier.height(2.dp))
                        Text(
                            item.lines.joinToString("\n"),
                            fontSize = 11.5.sp,
                            lineHeight = 17.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }

    InstallHint()

    if (hasNotes) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(top = 2.dp),
            horizontalArrangement = Arrangement.End
        ) {
            TextButton(onClick = onOpenPage) {
                Text(
                    tr("具体详见 Release 页面 →", "Full notes on the release page →"),
                    fontSize = 11.5.sp
                )
            }
        }
    }
}

/**
 * 侧载安装提示（2026-11 起）：OPPO / vivo / 小米 / 荣耀 会先弹「开发者身份未验证」，
 * 用户很容易以为下载的包坏了。更新弹窗是用户点「下载」前唯一一定会看到的地方，
 * 所以把怎么处理写在这里，而不是只写在文档里。
 *
 * 与发布正文无关，永远显示：正文为空时也必须看得到。
 */
@Composable
private fun InstallHint() {
    Spacer(Modifier.height(6.dp))
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(horizontal = 11.dp, vertical = 8.dp)) {
            Text(
                tr("装的时候若提示「开发者身份未验证」", "If the installer says \"unverified developer\""),
                fontSize = 11.5.sp,
                lineHeight = 17.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.height(2.dp))
            Text(
                tr(
                    "勾选「已知悉应用风险」，再点「仍然安装」就能装（个别机型还要输一次锁屏密码）。" +
                        "这是国内 OPPO / vivo / 小米 / 荣耀 从 2026 年 11 月起的侧载校验，" +
                        "安装包本身没有问题，功能也不受影响；每次更新都会再提示一次。",
                    "Tick \"I understand the risk\", then tap \"Install anyway\" (some phones ask " +
                        "for your screen-lock PIN). This is the mainland sideload check that OPPO / " +
                        "vivo / Xiaomi / HONOR introduced in November 2026 — the download itself is " +
                        "fine and nothing is lost in functionality. It reappears on every update."
                ),
                fontSize = 11.sp,
                lineHeight = 16.5.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/** Windows / 安卓 / 两端 的小标签，颜色只用来区分平台，不做好坏暗示 */
@Composable
private fun PlatformTag(platform: String) {
    val (label, fg, bg) = when (platform) {
        "win" -> Triple("Windows", Color(0xFF2B5BD0), Color(0xFFEEF4FF))
        "android" -> Triple(tr("安卓", "Android"), Color(0xFF1A7F45), Color(0xFFEAF7EE))
        else -> Triple(tr("两端", "Both"), Color(0xFF6B3FC4), Color(0xFFF3EEFE))
    }
    Surface(shape = RoundedCornerShape(999.dp), color = bg) {
        Text(
            label,
            Modifier.padding(horizontal = 6.dp, vertical = 1.dp),
            fontSize = 10.sp,
            fontWeight = FontWeight.Medium,
            color = fg
        )
    }
}

/** 供预览 / 测试直接拿一份「假结果」，不发网络请求 */
internal fun sampleResultForNotes(): Updater.Result = Updater.Result(
    ok = true,
    current = "1.4.3",
    latest = "1.4.4",
    hasUpdate = true,
    strong = false,
    digest = ReleaseDigest.of(
        "更新级别：建议\n\n" +
            "> **一句话**：注释和书签里的姓名地址不再漏打；安卓注释文字整块打码。\n\n" +
            "## 1. 修复：注释和书签里独自出现的姓名、地址会漏（Windows）\n\n" +
            "正文里没出现过的姓名、地址，现在也会被认出来。\n\n" +
            "## 2. 修复：安卓端注释里的文字会变成像素（安卓）\n\n" +
            "FreeText 注释在上一次渲染时变成了像素，现在整块盖马赛克。\n"
    )
)
