package com.neurotracee.pdfmask.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
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
import kotlinx.coroutines.launch

/**
 * 更新弹窗里的说明区（v1.4.4 起，v1.4.6.5 加跨版本翻页）。
 *
 * 两种情况：
 * - 只落后一个版本（绝大多数情况）：平铺这一版的摘要 + 分平台条目；
 * - 落后好几个版本（例如当前 1.4.6.2，仓库已有 1.4.6.3、1.4.6.4）：变成可翻页的
 *   说明浏览器，一页一版，顶部先说明「共 N 个版本未更新」。
 *
 * 翻页方向上刻意做成「相反逻辑」：**向右滑 → 上一页（更早的版本）**，
 * 向左滑 → 下一页（更新的版本）。页面顺序是「旧 → 新」，默认停在最后一页。
 *
 * 翻页只影响「看哪一版说明」：[Updater.Result.url] 永远是最大版本，
 * 下载/安装走的是它，底部的「下载目标」也固定写最新版版本号。
 *
 * 「启动时自动检查」和「设置 → 检查更新」共用这一个组件，保证两处样子一致。
 */
@Composable
internal fun UpdateNotesBlock(
    r: Updater.Result,
    accent: Color,
    /** 仅供预览/截图用：指定从第几页开始（-1 = 默认，停在最新版那一页） */
    initialPage: Int = -1,
    onOpenPage: () -> Unit
) {
    val pages = r.pending
    if (pages.size > 1) {
        VersionPages(r, pages, accent, onOpenPage, initialPage)
        return
    }

    val hasNotes = hasNotes(r.digest)
    NotesBody(r.digest, accent)
    InstallHint()
    if (hasNotes) MoreLink(onOpenPage)
}

/**
 * 跨版本说明浏览器：一页一版，默认停在最新版那一页（最后一页）。
 *
 * 下载目标与翻页完全解耦：不管停在哪一页，底部那行都写着最新版版本号，
 * 按钮也在页面外、永远指向 `r.url`。
 */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun VersionPages(
    r: Updater.Result,
    pages: List<Updater.PendingNote>,
    accent: Color,
    onOpenPage: () -> Unit,
    initialPage: Int = -1
) {
    // 页面按「旧 → 新」排，默认从最后一页（最新版）开始
    val start = if (initialPage in pages.indices) initialPage else pages.lastIndex
    val pager = rememberPagerState(initialPage = start) { pages.size }
    val scope = rememberCoroutineScope()
    val idx = pager.currentPage.coerceIn(0, pages.lastIndex)
    val cur = pages[idx]

    // ① 先告诉用户「你落后了几个版本」
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = accent.copy(alpha = 0.08f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(horizontal = 11.dp, vertical = 8.dp)) {
            Text(
                tr(
                    "共 ${pages.size} 个版本未更新（当前 v${r.current} → 最新 v${r.latest}）",
                    "${pages.size} versions behind (v${r.current} → v${r.latest})"
                ),
                fontSize = 12.sp,
                lineHeight = 17.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.height(2.dp))
            Text(
                tr(
                    "下面一页一版，正在看 v${cur.ver}（第 ${idx + 1} / ${pages.size} 页）· " +
                        "向右滑看更早的版本，向左滑看更新的版本",
                    "One version per page — viewing v${cur.ver} (${idx + 1} / ${pages.size}) · " +
                        "swipe right for older, left for newer"
                ),
                fontSize = 11.sp,
                lineHeight = 16.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }

    Spacer(Modifier.height(6.dp))

    // ② 可左右滑的说明页
    HorizontalPager(
        state = pager,
        modifier = Modifier.fillMaxWidth(),
        pageSpacing = 12.dp
    ) { page ->
        Column(Modifier.fillMaxWidth()) {
            NotesBody(pages[page].digest, accent)
        }
    }

    // ③ 页码 + 箭头（方向与手势一致：左边=更早，右边=更新）
    Row(
        Modifier
            .fillMaxWidth()
            .padding(top = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        TextButton(
            onClick = {
                scope.launch { pager.animateScrollToPage((pager.currentPage - 1).coerceAtLeast(0)) }
            },
            enabled = pager.currentPage > 0
        ) {
            Text(tr("‹ 更早版本", "‹ Older"), fontSize = 11.5.sp)
        }
        Text(
            "${idx + 1} / ${pages.size}",
            fontSize = 11.5.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        TextButton(
            onClick = {
                scope.launch {
                    pager.animateScrollToPage((pager.currentPage + 1).coerceAtMost(pages.lastIndex))
                }
            },
            enabled = pager.currentPage < pages.lastIndex
        ) {
            Text(tr("更新版本 ›", "Newer ›"), fontSize = 11.5.sp)
        }
    }

    // ④ 固定写明下载目标：翻到旧版本也不会改变
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = Color(0xFFF2FBF4),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(horizontal = 11.dp, vertical = 8.dp)) {
            Text(
                tr(
                    "下载目标始终是：最新版 v${r.latest}",
                    "Download target is always v${r.latest}, the newest"
                ),
                fontSize = 11.5.sp,
                lineHeight = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFF14501F)
            )
            Spacer(Modifier.height(2.dp))
            Text(
                tr(
                    "左右滑动只是换着看说明，不会改变要装的版本；翻到 v${cur.ver} 这一页点下载，" +
                        "装上的仍然是 v${r.latest}。",
                    "Swipe only changes which notes you read. Tapping download while viewing v${cur.ver} " +
                        "still installs v${r.latest}."
                ),
                fontSize = 10.5.sp,
                lineHeight = 15.sp,
                color = Color(0xFF2C6B3B)
            )
        }
    }

    InstallHint()
    MoreLink(onOpenPage)
}

/** 一版说明的正文：摘要 + 按平台归类的条目。没有内容时什么也不渲染。 */
@Composable
private fun NotesBody(digest: ReleaseDigest.Digest?, accent: Color) {
    val n = digest?.pick(AppPrefs.isEn) ?: return
    if (n.brief.isBlank() && n.items.isEmpty()) return

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

private fun hasNotes(digest: ReleaseDigest.Digest?): Boolean {
    val n = digest?.pick(AppPrefs.isEn) ?: return false
    return n.brief.isNotBlank() || n.items.isNotEmpty()
}

@Composable
private fun MoreLink(onOpenPage: () -> Unit) {
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

/** 供预览用：落后三个版本的假结果（跨版本翻页的样子） */
internal fun sampleResultForPager(): Updater.Result = Updater.Result(
    ok = true,
    current = "1.4.6.2",
    latest = "1.4.6.4",
    hasUpdate = true,
    strong = false,
    url = "https://gitee.com/bio234/pdf-privacy-masker/releases/download/v1.4.6.4/PDFPrivacyMasker-1.4.6.4-arm64.apk",
    digest = ReleaseDigest.of(
        "> **一句话**：住址不再漏打，乡村地址与跨行折断的地址都能认出来。\n\n" +
            "## 1. 住址漏打\n\n- 乡村地址、跨行地址、地址尾部都修好了。\n"
    ),
    pending = listOf(
        Updater.PendingNote(
            ver = "1.4.6.3",
            digest = ReleaseDigest.of(
                "> **一句话**：扫描件识别大幅变准。\n\n## 1. 三个通用缺陷\n\n- 长句整行被判死、外扩吞邻行、没有对比度处理。\n"
            ),
            strong = false,
            page = "https://gitee.com/bio234/pdf-privacy-masker/releases/tag/v1.4.6.3"
        ),
        Updater.PendingNote(
            ver = "1.4.6.4",
            digest = ReleaseDigest.of(
                "> **一句话**：住址不再漏打，乡村地址与跨行折断的地址都能认出来。\n\n" +
                    "## 1. 住址漏打\n\n- 乡村地址、跨行地址、地址尾部都修好了。\n"
            ),
            strong = false,
            page = "https://gitee.com/bio234/pdf-privacy-masker/releases/tag/v1.4.6.4"
        )
    )
)
