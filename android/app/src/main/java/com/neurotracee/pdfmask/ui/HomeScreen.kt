package com.neurotracee.pdfmask.ui

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurotracee.pdfmask.core.DraftStore

@Composable
fun HomeScreen(
    loading: Boolean,
    onPick: () -> Unit,
    fold: FoldInfo,
    expanded: Boolean,
    draft: DraftStore.Meta?,
    onResumeDraft: () -> Unit,
    onDiscardDraft: () -> Unit
) {
    val maxW = if (expanded) 600.dp else 520.dp
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(
            modifier = Modifier
                .widthIn(max = maxW)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp, vertical = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            if (loading) LoadingCard() else PickerCard(onPick)
            // 上次没弄完的那份：放在选文件区下面，一眼能看到「接着编辑」，
            // 而不是只在退出那一刻提一句、下次打开就找不到了。
            if (!loading && draft != null) {
                Spacer(Modifier.height(12.dp))
                DraftCard(draft, onResumeDraft, onDiscardDraft)
            }
            Spacer(Modifier.height(16.dp))
            HintCard()
        }
    }
}

/**
 * 「上次没编辑完」卡片。
 *
 * 用户在处理页按返回时选了「临时保存」，下次打开就该在第一屏看到它——
 * 否则草稿存了等于没存。丢弃是不可逆操作，所以单独二次确认。
 */
@Composable
private fun DraftCard(meta: DraftStore.Meta, onResume: () -> Unit, onDiscard: () -> Unit) {
    var askDiscard by remember { mutableStateOf(false) }
    val mins = ((System.currentTimeMillis() - meta.savedAt) / 60000L).toInt().coerceAtLeast(0)
    val timeText = when {
        mins < 1 -> T("刚刚", "just now")
        mins < 60 -> T("$mins 分钟前", "$mins min ago")
        mins < 1440 -> T("${mins / 60} 小时前", "${mins / 60} h ago")
        else -> T("${mins / 1440} 天前", "${mins / 1440} d ago")
    }
    val detail = if (meta.pages > 0) {
        T(
            "${meta.marks} 处标记 · $timeText · 第 ${meta.current + 1}/${meta.pages} 页",
            "${meta.marks} marks · $timeText · page ${meta.current + 1}/${meta.pages}"
        )
    } else {
        T("${meta.marks} 处标记 · $timeText", "${meta.marks} marks · $timeText")
    }

    Surface(
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 1.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        // 文字整宽、按钮单独一行：360dp 窄屏上如果并排，文件名和明细都会被挤成省略号
        Column(Modifier.padding(start = 16.dp, end = 12.dp, top = 12.dp, bottom = 10.dp)) {
                Text(
                    T("上次没编辑完", "Unfinished"),
                    fontSize = 11.5.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(3.dp))
                Text(
                    meta.name,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    detail,
                    fontSize = 11.5.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            Spacer(Modifier.height(8.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = { askDiscard = true }) {
                    Text(T("丢弃", "Discard"), fontSize = 12.sp)
                }
                Spacer(Modifier.width(6.dp))
                Button(
                    onClick = onResume,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text(T("继续编辑", "Continue"), fontSize = 12.5.sp)
                }
            }
        }
    }

    if (askDiscard) {
        AlertDialog(
            onDismissRequest = { askDiscard = false },
            title = {
                Text(
                    T("丢弃这份草稿？", "Discard this draft?"),
                    fontSize = 15.5.sp,
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    T(
                        "草稿里的框选和擦除会一起删掉，无法恢复。原 PDF 文件不受影响。",
                        "The boxes and erasures saved in it will be deleted for good. Your original PDF is not affected."
                    ),
                    fontSize = 12.5.sp,
                    lineHeight = 20.sp
                )
            },
            confirmButton = {
                TextButton(onClick = { askDiscard = false; onDiscard() }) {
                    Text(T("丢弃", "Discard"))
                }
            },
            dismissButton = {
                TextButton(onClick = { askDiscard = false }) {
                    Text(T("取消", "Cancel"))
                }
            }
        )
    }
}

/** 大号文件选择区：整块可点，视觉上占据首页主要空间 */
@Composable
private fun PickerCard(onPick: () -> Unit) {
    Surface(
        onClick = onPick,
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().heightIn(min = 300.dp)
    ) {
        Column(
            Modifier.padding(horizontal = 22.dp, vertical = 30.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                Modifier
                    .size(88.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(Color(0xFF3B82F6), Color(0xFF7C3AED))
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                ShieldMark(Modifier.size(54.dp))
            }
            Spacer(Modifier.height(20.dp))
            Text(
                T("选择 PDF 文件", "Choose a PDF"),
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.height(8.dp))
            Text(
                T(
                    "从手机里挑一个文件，原文件不会被改动",
                    "Pick a file from your phone. The original stays untouched."
                ),
                fontSize = 13.sp,
                lineHeight = 19.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(22.dp))
            Box(
                Modifier
                    .clip(RoundedCornerShape(24.dp))
                    .background(MaterialTheme.colorScheme.primary)
                    .padding(horizontal = 26.dp, vertical = 11.dp)
            ) {
                Text(
                    T("选好了，去处理", "Pick a file"),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onPrimary
                )
            }
        }
    }
}

/** 盾牌 + 对勾，和桌面版图标同一造型 */
@Composable
private fun ShieldMark(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val shield = Path().apply {
            moveTo(w * 0.5f, h * 0.03f)
            lineTo(w * 0.93f, h * 0.20f)
            lineTo(w * 0.93f, h * 0.50f)
            cubicTo(w * 0.93f, h * 0.74f, w * 0.74f, h * 0.90f, w * 0.5f, h * 0.98f)
            cubicTo(w * 0.26f, h * 0.90f, w * 0.07f, h * 0.74f, w * 0.07f, h * 0.50f)
            lineTo(w * 0.07f, h * 0.20f)
            close()
        }
        drawPath(shield, Color.White)
        val tick = Path().apply {
            moveTo(w * 0.29f, h * 0.48f)
            lineTo(w * 0.44f, h * 0.63f)
            lineTo(w * 0.73f, h * 0.33f)
        }
        drawPath(
            tick,
            Color(0xFF3B3FD8),
            style = Stroke(
                width = w * 0.115f,
                cap = StrokeCap.Round,
                join = StrokeJoin.Round
            )
        )
    }
}

@Composable
private fun LoadingCard() {
    // 进度条和暂停按钮都在底部的 JobPanel 里，这里不再放第二个转圈：
    // 两个动画同时转，用户反而不知道该看哪个。
    Surface(
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth().heightIn(min = 300.dp)
    ) {
        Column(
            Modifier.padding(24.dp).fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Box(
                Modifier
                    .size(88.dp)
                    .clip(RoundedCornerShape(24.dp))
                    .background(
                        Brush.linearGradient(
                            listOf(Color(0xFF3B82F6), Color(0xFF7C3AED))
                        )
                    ),
                contentAlignment = Alignment.Center
            ) {
                ShieldMark(Modifier.size(54.dp))
            }
            Spacer(Modifier.height(20.dp))
            Text(
                T("正在处理这份文档", "Working on your document"),
                fontSize = 17.sp,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center
            )
            Spacer(Modifier.height(10.dp))
            Text(
                T(
                    "逐页读取文字并定位敏感信息，进度见下方，随时可以暂停或停止",
                    "Reading each page and locating sensitive data. Progress is shown below — pause or stop anytime."
                ),
                fontSize = 12.5.sp,
                lineHeight = 19.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}

/** 说明区，放在选择区下方 */
@Composable
private fun HintCard() {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(16.dp)) {
            SectionLabel(T("三点说明", "Good to know"))
            Spacer(Modifier.height(9.dp))
            TipLine(
                T(
                    "① 识别和打码全程在本机完成，文件不上传。唯一的网络权限只用于你手动点「检查更新」。",
                    "① Detection and masking run entirely on this device — files are never uploaded. " +
                        "The single network permission is only used when you tap Check for updates."
                )
            )
            TipLine(
                T(
                    "② 扫描件（整页是图片）会自动用本机 OCR 识别，同样离线；万一认不出，仍可在预览上手动画框。",
                    "② Scanned PDFs are read with on-device OCR, also fully offline — " +
                        "and you can still drag boxes by hand if anything is missed."
                )
            )
            TipLine(
                T(
                    "③ 打码后输出为图片型 PDF，文字不可复制，原文无法还原。",
                    "③ Output is an image-only PDF: text can't be copied and the original can't be recovered."
                )
            )
            Spacer(Modifier.height(10.dp))
            Row {
                Text(
                    T("能自动认出：", "Auto-detects: "),
                    fontSize = 11.5.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    T(
                        "手机号 / 身份证 / 银行卡 / 邮箱 / 姓名 / 座机 / 地址 / 生日 / 性别年龄",
                        "phone / ID / bank card / email / name / landline / address / birthday / gender & age"
                    ),
                    fontSize = 11.5.sp,
                    lineHeight = 17.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun TipLine(s: String) {
    Text(
        s,
        fontSize = 12.sp,
        lineHeight = 19.sp,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(bottom = 4.dp)
    )
}
