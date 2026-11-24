package com.neurotracee.pdfmask.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.neurotracee.pdfmask.BuildConfig
import com.neurotracee.pdfmask.LogStore
import com.neurotracee.pdfmask.tr
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.time.LocalDate
import java.time.ZoneOffset
import java.util.Date
import java.util.Locale

private val GITHUB_ISSUE = "https://github.com/neurotracee/pdf-privacy-masker/issues/new"
private val GITEE_ISSUE = "https://gitee.com/bio234/pdf-privacy-masker/issues/new"

/**
 * 应用日志：本次启动 / 历史日志（起止日期 + 起止时间）/ 复制 / 存 TXT / 按区间清除 / 反馈模板。
 *
 * 版面一律「先一张卡片，再一张卡片」，卡片是白底（暗色下是深灰底），
 * 底下一层浅灰页面色，靠这一层差把内容分块，不靠线框堆叠。
 * 颜色只用项目自己的蓝 + 中性灰阶，跟随系统明暗，不做彩色主题。
 */
@Composable
fun LogDialog(onClose: () -> Unit) {
    Dialog(
        onDismissRequest = onClose,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Box(
            Modifier.fillMaxSize().padding(horizontal = 12.dp, vertical = 22.dp),
            contentAlignment = Alignment.Center
        ) {
            Surface(
                shape = RoundedCornerShape(26.dp),
                color = MaterialTheme.colorScheme.background,
                shadowElevation = 12.dp
            ) {
                LogPanel(onClose)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogPanel(onClose: () -> Unit) {
    val ctx = LocalContext.current
    val cs = MaterialTheme.colorScheme
    val scope = rememberCoroutineScope()
    val maxH = (LocalConfiguration.current.screenHeightDp * 0.88f).dp

    val dateFmt = remember { SimpleDateFormat("yyyy-MM-dd", Locale.US) }
    // 日期选择器返回的是「UTC 零点」的毫秒，反解也要按 UTC，否则在负时区会差一天
    val utcDateFmt = remember {
        SimpleDateFormat("yyyy-MM-dd", Locale.US).apply { timeZone = java.util.TimeZone.getTimeZone("UTC") }
    }
    val today = remember { dateFmt.format(Date()) }
    // 卡片 / 底色 / 轨道色都从主题里取，浅色是白+浅灰，暗色是深灰+近黑
    val dark = cs.surface.luminance() < 0.45f
    val cardBorder = BorderStroke(1.dp, cs.outline.copy(alpha = if (dark) 0.6f else 0.45f))
    val warnBg = if (dark) Color(0xFF2A2318) else Color(0xFFFFF8E8)
    val warnBorder = if (dark) Color(0xFF4A3C1E) else Color(0xFFF0DFB8)
    val warnInk = if (dark) Color(0xFFE0B45E) else Color(0xFF8A5A00)

    var tab by remember { mutableIntStateOf(0) }                 // 0 本次启动 · 1 历史
    var sessionText by remember { mutableStateOf("") }
    var fromDay by remember { mutableStateOf(today) }
    var toDay by remember { mutableStateOf(today) }
    var fromTime by remember { mutableStateOf("") }
    var toTime by remember { mutableStateOf("") }
    var preview by remember { mutableStateOf("") }
    var days by remember { mutableStateOf<List<String>>(emptyList()) }
    var crashed by remember { mutableStateOf(LogStore.prevCrashed) }
    var timeTarget by remember { mutableIntStateOf(-1) }          // -1 关 · 0 起 · 1 止
    var dateTarget by remember { mutableIntStateOf(-1) }
    var confirmStage by remember { mutableIntStateOf(0) }
    var confirmText by remember { mutableStateOf("") }
    var stats by remember { mutableStateOf(0 to 0L) }

    fun toast(m: String) = Toast.makeText(ctx, m, Toast.LENGTH_SHORT).show()

    fun refreshLists() {
        sessionText = LogStore.sessionLines()
        days = LogStore.listDays()
    }

    fun reload() {
        val lo = fromDay.trim()
        val hi = toDay.trim()
        if (!validDate(lo) || !validDate(hi)) {
            toast(tr("日期要写成 2026-11-20 这样", "Dates must look like 2026-11-20")); return
        }
        if (hi < lo) { toast(tr("结束日期不能早于起始日期", "The end date is before the start date")); return }
        scope.launch {
            preview = withContext(Dispatchers.IO) {
                LogStore.readRange(lo, hi, fromTime.trim().ifBlank { null }, toTime.trim().ifBlank { null })
            }
            if (preview.isBlank()) toast(tr("这段时间没有日志", "No logs in that range"))
        }
    }

    LaunchedEffect(Unit) {
        days = withContext(Dispatchers.IO) { LogStore.listDays() }
        sessionText = withContext(Dispatchers.IO) { LogStore.sessionLines() }
    }

    // 存 TXT 时读的是「当前这一段」的内容，用 updatedState 保证不会抓到旧值
    val saveBody = rememberUpdatedState(if (tab == 0) sessionText else preview)
    val saveLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("text/plain")
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        val body = saveBody.value
        if (body.isBlank()) { toast(tr("没有可保存的内容", "Nothing to save")); return@rememberLauncherForActivityResult }
        scope.launch {
            val ok = withContext(Dispatchers.IO) { LogStore.writeToUri(ctx, uri, body) }
            toast(if (ok) tr("已保存为 TXT", "Saved as TXT") else tr("保存失败，换个目录试试", "Save failed — try another folder"))
        }
    }

    Column(
        Modifier
            .heightIn(max = maxH)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp)
            .padding(top = 16.dp, bottom = 22.dp)
    ) {
        // ---------- 标题：只有标题 + 一句说明 + 完成 ----------
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(
                    T("应用日志", "App logs"),
                    fontSize = 21.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = cs.onBackground
                )
                Spacer(Modifier.height(3.dp))
                Text(
                    T("最近 365 天 · 只在本机", "Last 365 days · stays on this device"),
                    fontSize = 11.sp,
                    color = cs.onSurfaceVariant
                )
            }
            Text(
                T("完成", "Done"),
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = cs.primary,
                modifier = Modifier.clickable { onClose() }.padding(8.dp)
            )
        }

        // ---------- 上次异常退出：压成一行，点「查看」就看本次启动 ----------
        if (crashed) {
            Spacer(Modifier.height(12.dp))
            Row(
                Modifier
                    .fillMaxWidth()
                    .background(warnBg, RoundedCornerShape(14.dp))
                    .border(1.dp, warnBorder, RoundedCornerShape(14.dp))
                    .padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        T("上次运行异常退出", "Last run ended unexpectedly"),
                        fontSize = 12.5.sp, fontWeight = FontWeight.SemiBold, color = warnInk
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        T("堆栈就在本次启动的日志里", "The stack trace is in this launch's log"),
                        fontSize = 11.sp, color = warnInk.copy(alpha = 0.85f)
                    )
                }
                Text(
                    T("查看", "View"),
                    fontSize = 12.sp, fontWeight = FontWeight.Medium, color = warnInk,
                    modifier = Modifier
                        .clickable {
                            LogStore.dismissCrash(); crashed = false
                            tab = 0
                            scope.launch { sessionText = withContext(Dispatchers.IO) { LogStore.sessionLines() } }
                        }
                        .padding(6.dp)
                )
            }
        }

        Spacer(Modifier.height(14.dp))
        Segmented(
            items = listOf(T("本次启动", "This launch"), T("历史日志", "History")),
            index = tab
        ) { i ->
            tab = i
            if (i == 1) reload()
        }

        Spacer(Modifier.height(12.dp))

        if (tab == 0) {
            // ---------- 本次启动：一块卡片，行数 + 日志 + 三个动作 ----------
            SheetCard(border = cardBorder) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        T("本次启动", "This launch"),
                        fontSize = 13.5.sp, fontWeight = FontWeight.SemiBold, color = cs.onSurface
                    )
                    Spacer(Modifier.weight(1f))
                    MetaText(T("${lineCount(sessionText)} 行", "${lineCount(sessionText)} lines"))
                }
                Spacer(Modifier.height(10.dp))
                LogBox(
                    text = sessionText,
                    hint = T("这次启动还没有日志", "No log lines yet"),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 190.dp, max = 340.dp)
                )
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    val m = Modifier.weight(1f)
                    PillButton(T("复制", "Copy"), primary = true, modifier = m) {
                        if (sessionText.isBlank()) toast(tr("还没有日志", "Nothing yet"))
                        else copyPlain(ctx, sessionText, tr("日志已复制", "Log copied"))
                    }
                    PillButton(T("存为 TXT", "Save TXT"), modifier = m) {
                        if (sessionText.isBlank()) toast(tr("还没有日志", "Nothing yet"))
                        else saveLauncher.launch(suggestName())
                    }
                    PillButton(T("刷新", "Refresh"), modifier = m) {
                        scope.launch {
                            sessionText = withContext(Dispatchers.IO) { LogStore.sessionLines() }
                            days = withContext(Dispatchers.IO) { LogStore.listDays() }
                        }
                    }
                }
            }
        } else {
            // ---------- 时间范围卡片：日期、时间都是点一下弹选择器 ----------
            SheetCard(border = cardBorder) {
                SectionHead(T("时间范围", "Time range"), T("点一下就能选", "Tap to pick"))
                Spacer(Modifier.height(12.dp))

                RangeRow(
                    edge = T("起", "From"),
                    day = fromDay,
                    time = fromTime,
                    onPickDay = { dateTarget = 0 },
                    onPickTime = { timeTarget = 0 },
                    onClearTime = { fromTime = "" }
                )
                Spacer(Modifier.height(8.dp))
                RangeRow(
                    edge = T("止", "To"),
                    day = toDay,
                    time = toTime,
                    onPickDay = { dateTarget = 1 },
                    onPickTime = { timeTarget = 1 },
                    onClearTime = { toTime = "" }
                )

                if (days.isNotEmpty()) {
                    Spacer(Modifier.height(14.dp))
                    Text(T("有日志的日期", "Days with logs"), fontSize = 10.5.sp, color = cs.onSurfaceVariant)
                    Spacer(Modifier.height(7.dp))
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        days.take(30).forEach { d ->
                            MiniChip(
                                text = d.substring(5),
                                selected = d == fromDay && d == toDay
                            ) {
                                fromDay = d; toDay = d; fromTime = ""; toTime = ""
                                reload()
                            }
                        }
                    }
                }

                Spacer(Modifier.height(14.dp))
                PillButton(
                    T("查询", "Search"),
                    primary = true,
                    modifier = Modifier.fillMaxWidth()
                ) { reload() }
            }

            Spacer(Modifier.height(10.dp))

            // ---------- 查询结果卡片 ----------
            SheetCard(border = cardBorder) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        T("查询结果", "Result"),
                        fontSize = 13.5.sp, fontWeight = FontWeight.SemiBold, color = cs.onSurface
                    )
                    Spacer(Modifier.weight(1f))
                    MetaText(
                        if (preview.isBlank()) T("未查询", "Not queried")
                        else T(
                            "${lineCount(preview)} 行 · ${preview.toByteArray().size / 1024} KB",
                            "${lineCount(preview)} lines · ${preview.toByteArray().size / 1024} KB"
                        )
                    )
                }
                Spacer(Modifier.height(10.dp))
                LogBox(
                    text = preview,
                    hint = T("选好范围后点「查询」", "Pick a range, then tap Search"),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 160.dp, max = 300.dp)
                )
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    val m = Modifier.weight(1f)
                    PillButton(T("复制", "Copy"), primary = true, modifier = m) {
                        if (preview.isBlank()) toast(tr("先查一下再复制", "Search first"))
                        else copyPlain(ctx, preview, tr("已复制", "Copied"))
                    }
                    PillButton(T("存为 TXT", "Save TXT"), modifier = m) {
                        if (preview.isBlank()) toast(tr("先查一下再保存", "Search first"))
                        else saveLauncher.launch(suggestName())
                    }
                }
            }

            Spacer(Modifier.height(6.dp))
            Text(
                T("清除这段日期的日志", "Delete logs in this range"),
                fontSize = 12.5.sp,
                color = cs.error,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable {
                        val lo = fromDay.trim()
                        val hi = toDay.trim()
                        if (!validDate(lo) || !validDate(hi) || hi < lo) {
                            toast(tr("先把日期范围选好", "Pick a valid date range first")); return@clickable
                        }
                        stats = LogStore.rangeStats(lo, hi)
                        if (stats.first == 0) { toast(tr("这段日期没有日志", "No logs in that range")); return@clickable }
                        confirmText = "$lo → $hi"
                        confirmStage = 1
                    }
                    .padding(horizontal = 12.dp, vertical = 12.dp)
            )
        }

        Spacer(Modifier.height(16.dp))
        FeedbackCard()
    }

    // ---------- 日期选择 ----------
    if (dateTarget >= 0) {
        val seedMs = runCatching {
            LocalDate.parse(if (dateTarget == 0) fromDay.trim() else toDay.trim())
                .atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli()
        }.getOrNull()
        val pickerState = rememberDatePickerState(initialSelectedDateMillis = seedMs)
        DatePickerDialog(
            onDismissRequest = { dateTarget = -1 },
            confirmButton = {
                TextButton(onClick = {
                    val ms = pickerState.selectedDateMillis
                    if (ms != null) {
                        val s = utcDateFmt.format(Date(ms))
                        if (dateTarget == 0) fromDay = s else toDay = s
                    }
                    dateTarget = -1
                }) { Text(T("确定", "OK"), color = cs.primary) }
            },
            dismissButton = {
                TextButton(onClick = { dateTarget = -1 }) {
                    Text(T("取消", "Cancel"), color = cs.onSurfaceVariant)
                }
            }
        ) {
            DatePicker(state = pickerState, title = null, headline = null, showModeToggle = false)
        }
    }

    // ---------- 时间滚轮 ----------
    if (timeTarget >= 0) {
        val cur = if (timeTarget == 0) fromTime else toTime
        val seedH = cur.substringBefore(':').toIntOrNull() ?: 9
        val seedM = cur.substringAfter(':', "").toIntOrNull() ?: 0
        WheelTimePickerDialog(
            initialHour = seedH,
            initialMinute = seedM,
            title = if (timeTarget == 0) T("起始时间", "From time") else T("结束时间", "To time"),
            onDismiss = { timeTarget = -1 },
            onConfirm = { h, m ->
                val v = "%02d:%02d".format(h, m)
                if (timeTarget == 0) fromTime = v else toTime = v
                timeTarget = -1
            }
        )
    }

    // ---------- 删除两段确认 ----------
    if (confirmStage == 1) {
        AlertDialog(
            onDismissRequest = { confirmStage = 0 },
            title = { Text(T("删除前的确认", "Before deleting"), fontSize = 17.sp) },
            text = {
                Text(
                    T(
                        "将要删除 $confirmText 的日志，共 ${stats.first} 天、约 ${stats.second / 1024} KB。\n删除后无法恢复。",
                        "This deletes logs for $confirmText — ${stats.first} file(s), about ${stats.second / 1024} KB.\nDeleted logs cannot be recovered."
                    ),
                    fontSize = 13.5.sp, lineHeight = 20.sp
                )
            },
            confirmButton = {
                TextButton(onClick = { confirmStage = 2 }) {
                    Text(T("继续", "Continue"), color = cs.error, fontWeight = FontWeight.Medium)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmStage = 0 }) {
                    Text(T("取消", "Cancel"), color = cs.onSurfaceVariant)
                }
            }
        )
    }
    if (confirmStage == 2) {
        AlertDialog(
            onDismissRequest = { confirmStage = 0 },
            title = { Text(T("再确认一次", "Confirm once more"), fontSize = 17.sp) },
            text = {
                Text(
                    T("确定永久删除 $confirmText 这些日志吗？这一步不能撤销。",
                        "Permanently delete the logs for $confirmText? This cannot be undone."),
                    fontSize = 13.5.sp, lineHeight = 20.sp
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    val lo = fromDay.trim()
                    val hi = toDay.trim()
                    scope.launch {
                        val n = withContext(Dispatchers.IO) { LogStore.deleteRange(lo, hi) }
                        toast(tr("已删除 $n 天的日志", "Deleted logs for $n day(s)"))
                        confirmStage = 0
                        preview = ""
                        days = withContext(Dispatchers.IO) { LogStore.listDays() }
                        sessionText = withContext(Dispatchers.IO) { LogStore.sessionLines() }
                        reload()
                    }
                }) { Text(T("永久删除", "Delete"), color = cs.error, fontWeight = FontWeight.Medium) }
            },
            dismissButton = {
                TextButton(onClick = { confirmStage = 0 }) {
                    Text(T("取消", "Cancel"), color = cs.onSurfaceVariant)
                }
            }
        )
    }
}

// ---------------- 卡片与小组件 ----------------

/** 卡片：靠底色差分层，只留一条极淡的描边收边 */
@Composable
private fun SheetCard(
    border: BorderStroke,
    content: @Composable ColumnScope.() -> Unit
) {
    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surface,
        border = border,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(14.dp), content = content)
    }
}

@Composable
private fun SectionHead(title: String, hint: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            title,
            fontSize = 13.5.sp, fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(Modifier.weight(1f))
        Text(hint, fontSize = 10.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun MetaText(text: String) {
    Text(text, fontSize = 10.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

/** 两档做成一个整体胶囊：里面滑块是卡片色，底下是浅轨道 */
@Composable
private fun Segmented(items: List<String>, index: Int, onSelect: (Int) -> Unit) {
    val cs = MaterialTheme.colorScheme
    Row(
        Modifier
            .fillMaxWidth()
            .background(cs.surfaceVariant.copy(alpha = 0.6f), RoundedCornerShape(13.dp))
            .padding(4.dp)
    ) {
        items.forEachIndexed { i, s ->
            val active = i == index
            Box(
                Modifier
                    .weight(1f)
                    .background(
                        if (active) cs.surface else Color.Transparent,
                        RoundedCornerShape(10.dp)
                    )
                    .clickable { onSelect(i) }
                    .padding(vertical = 9.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    s,
                    fontSize = 12.5.sp,
                    color = if (active) cs.onSurface else cs.onSurfaceVariant,
                    fontWeight = if (active) FontWeight.Medium else FontWeight.Normal
                )
            }
        }
    }
}

/** 胶囊按钮：主按钮实心蓝，次按钮白底细边；宽度由调用方给（Row 里传 weight） */
@Composable
private fun PillButton(
    text: String,
    primary: Boolean = false,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val cs = MaterialTheme.colorScheme
    val shape = RoundedCornerShape(11.dp)
    val bg = if (primary) cs.primary else cs.surface
    val fg = if (primary) cs.onPrimary else cs.onSurface
    Box(
        modifier
            .background(bg, shape)
            .border(1.dp, if (primary) cs.primary else cs.outline.copy(alpha = 0.55f), shape)
            .clickable { onClick() }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(text, fontSize = 12.5.sp, color = fg, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun EdgeLabel(text: String) {
    Text(
        text,
        fontSize = 10.5.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.width(14.dp)
    )
}

/** 「起 / 止」一行：日期格子 + 时间格子，都是点一下弹选择器 */
@Composable
private fun RangeRow(
    edge: String,
    day: String,
    time: String,
    onPickDay: () -> Unit,
    onPickTime: () -> Unit,
    onClearTime: () -> Unit
) {
    val cs = MaterialTheme.colorScheme
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        EdgeLabel(edge)
        Column(Modifier.weight(1f)) {
            Text(T("日期", "Date"), fontSize = 11.sp, color = cs.onSurfaceVariant)
            Spacer(Modifier.height(4.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .background(cs.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(11.dp))
                    .border(1.dp, cs.outline.copy(alpha = 0.45f), RoundedCornerShape(11.dp))
                    .clickable { onPickDay() }
                    .padding(horizontal = 12.dp, vertical = 11.dp)
            ) {
                Text(day, fontSize = 13.sp, color = cs.onSurface)
            }
        }
        Column(Modifier.weight(0.85f)) {
            Text(T("时间", "Time"), fontSize = 11.sp, color = cs.onSurfaceVariant)
            Spacer(Modifier.height(4.dp))
            Row(
                Modifier
                    .fillMaxWidth()
                    .background(cs.surface, RoundedCornerShape(11.dp))
                    .border(1.dp, cs.outline.copy(alpha = 0.45f), RoundedCornerShape(11.dp))
                    .clickable { onPickTime() }
                    .padding(horizontal = 12.dp, vertical = 11.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    if (time.isBlank()) T("整天", "Whole day") else time,
                    fontSize = 13.sp,
                    color = if (time.isBlank()) cs.onSurfaceVariant else cs.onSurface,
                    modifier = Modifier.weight(1f)
                )
                if (time.isNotBlank()) {
                    Text(
                        "×",
                        fontSize = 15.sp,
                        color = cs.onSurfaceVariant,
                        modifier = Modifier.clickable { onClearTime() }.padding(4.dp)
                    )
                } else {
                    Text("▾", fontSize = 12.sp, color = cs.onSurfaceVariant)
                }
            }
        }
    }
}

/** 有日志的日期小胶囊，横向滑，不占纵向版面 */
@Composable
private fun MiniChip(text: String, selected: Boolean, onClick: () -> Unit) {
    val cs = MaterialTheme.colorScheme
    Box(
        Modifier
            .background(if (selected) cs.primary else cs.surface, RoundedCornerShape(9.dp))
            .border(
                1.dp,
                if (selected) cs.primary else cs.outline.copy(alpha = 0.5f),
                RoundedCornerShape(9.dp)
            )
            .clickable { onClick() }
            .padding(horizontal = 10.dp, vertical = 7.dp)
    ) {
        Text(
            text,
            fontSize = 11.5.sp,
            color = if (selected) cs.onPrimary else cs.onSurface
        )
    }
}

/** 日志正文框：等宽字、浅底、可长按选中复制 */
@Composable
private fun LogBox(text: String, hint: String, modifier: Modifier) {
    val cs = MaterialTheme.colorScheme
    Box(
        modifier
            .background(cs.background, RoundedCornerShape(12.dp))
            .border(1.dp, cs.outline.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
    ) {
        SelectionContainer {
            Text(
                text.ifBlank { hint },
                fontSize = 10.5.sp,
                lineHeight = 16.sp,
                fontFamily = FontFamily.Monospace,
                color = if (text.isBlank()) cs.onSurfaceVariant else cs.onSurface,
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(12.dp)
            )
        }
    }
}

/** 反馈卡：默认只露一行说明，模板折叠，想看再展开 */
@Composable
private fun FeedbackCard() {
    val ctx = LocalContext.current
    val cs = MaterialTheme.colorScheme
    var expanded by remember { mutableStateOf(false) }
    val template = buildTemplate()

    SheetCard(border = BorderStroke(1.dp, cs.outline.copy(alpha = 0.45f))) {
        Row(
            Modifier.fillMaxWidth().clickable { expanded = !expanded },
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    T("遇到问题？去反馈", "Reporting a bug?"),
                    fontSize = 13.5.sp, fontWeight = FontWeight.SemiBold, color = cs.onSurface
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    T("版本号与机型已自动填好", "Version and device are pre-filled"),
                    fontSize = 11.sp, color = cs.onSurfaceVariant
                )
            }
            Text(
                if (expanded) T("收起", "Hide") else T("看模板", "Template"),
                fontSize = 11.5.sp, fontWeight = FontWeight.Medium, color = cs.primary,
                modifier = Modifier.padding(6.dp)
            )
        }

        if (expanded) {
            Spacer(Modifier.height(10.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .background(cs.background, RoundedCornerShape(10.dp))
                    .border(1.dp, cs.outline.copy(alpha = 0.4f), RoundedCornerShape(10.dp))
                    .padding(10.dp)
            ) {
                Text(
                    template,
                    fontSize = 10.5.sp,
                    lineHeight = 15.sp,
                    fontFamily = FontFamily.Monospace,
                    color = cs.onSurface
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val m = Modifier.weight(1f)
            PillButton(T("复制模板", "Copy template"), primary = true, modifier = m) {
                copyPlain(ctx, template, tr("模板已复制，记得把日志一起附上", "Template copied — attach the log too"))
            }
            PillButton("GitHub", modifier = m) {
                if (!openUrlInBrowser(ctx, GITHUB_ISSUE)) copyPlain(ctx, GITHUB_ISSUE, tr("链接已复制", "Link copied"))
            }
            PillButton("Gitee", modifier = m) {
                if (!openUrlInBrowser(ctx, GITEE_ISSUE)) copyPlain(ctx, GITEE_ISSUE, tr("链接已复制", "Link copied"))
            }
        }
    }
}

private fun lineCount(text: String): Int = text.lineSequence().count { it.isNotBlank() }

private fun validDate(s: String): Boolean {
    if (!Regex("^\\d{4}-\\d{2}-\\d{2}$").matches(s)) return false
    return runCatching { LocalDate.parse(s) }.isSuccess
}

private fun copyPlain(ctx: Context, text: String, msg: String) {
    val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager
    cm?.setPrimaryClip(ClipData.newPlainText("log", text))
    Toast.makeText(ctx, msg, Toast.LENGTH_SHORT).show()
}

private fun suggestName(): String {
    val d = SimpleDateFormat("yyyyMMdd-HHmm", Locale.US).format(Date())
    return "pdfmask-log-$d.txt"
}

private fun buildTemplate(): String {
    val ver = "v" + BuildConfig.VERSION_NAME
    val os = "Android ${android.os.Build.VERSION.RELEASE} · " +
        "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
    return tr(
        "版本号：$ver\n机型系统：$os\n问题一句话：一句话说清发生了什么\n\n" +
            "复现步骤：\n1. 打开 App，进入 …\n2. 点开 …\n3. 结果 …\n\n" +
            "实际看到：…\n预期结果：…\n\n" +
            "日志：已随本 Issue 附上 TXT（可在日志页「存为 TXT」导出）",
        "Version: $ver\nDevice: $os\nIn one sentence: what went wrong\n\n" +
            "Steps to reproduce:\n1. Open the app, go to …\n2. Tap …\n3. Result …\n\n" +
            "What I saw: …\nWhat I expected: …\n\n" +
            "Log: attach the TXT exported from the log screen"
    )
}
