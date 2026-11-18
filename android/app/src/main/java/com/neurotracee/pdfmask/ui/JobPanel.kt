package com.neurotracee.pdfmask.ui

import androidx.compose.animation.core.LinearEasing
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurotracee.pdfmask.AppViewModel
import kotlin.math.roundToInt

/**
 * 处理中的底部进度面板。
 *
 * 以前界面只有一个转圈：用户看不出在干什么、也不知道还要多久，更没法中途停下。
 * 这里做成贴在底部居中的一张卡：
 *
 *  - 第一行：阶段标题（读取文件 / 识别扫描页 / 打码）+ 「第 3 / 12 页」
 *  - 第二行：**当前页**进度条
 *  - 第三行：**整个文件**进度条（含百分比）
 *  - 第四行：暂停 / 停止（暂停后第一颗按钮变成「继续」）
 *
 * 为什么页条在上、总条在下：总进度是一直往右爬的那条，放最底下最贴近屏幕边缘，
 * 视线不用来回跳；当前页的条短、变化快，放在标题下面更容易看出「这一页正在动」。
 */
@Composable
fun JobOverlay(vm: AppViewModel) {
    Box(
        Modifier
            .fillMaxSize()
            // 遮罩不压太黑：处理期间底下还有文档预览，压黑了像卡死
            .background(Color(0x66101418)),
        contentAlignment = Alignment.BottomCenter
    ) {
        JobPanel(
            title = vm.jobTitle,
            note = vm.jobNote,
            page = vm.jobPage,
            pages = vm.jobPages,
            pageFrac = vm.jobPageFrac,
            overall = vm.jobOverall,
            paused = vm.jobPaused,
            onPause = { vm.pauseJob() },
            onResume = { vm.resumeJob() },
            onStop = { vm.stopJob() }
        )
    }
}

/** 无状态的面板本体：所有数字都由调用方给，方便单测 / 截图核对 */
@Composable
fun JobPanel(
    title: String,
    note: String,
    page: Int,
    pages: Int,
    pageFrac: Float,
    overall: Float,
    paused: Boolean,
    animate: Boolean = true,
    onPause: () -> Unit,
    onResume: () -> Unit,
    onStop: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(20.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 10.dp,
        tonalElevation = 2.dp,
        modifier = Modifier
            .padding(horizontal = 14.dp, vertical = 18.dp)
            .widthIn(max = 560.dp)
            .fillMaxWidth()
    ) {
        Column(Modifier.padding(horizontal = 18.dp, vertical = 16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(
                        if (paused) T("已暂停", "Paused") else title,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(Modifier.height(3.dp))
                    Text(
                        pageLine(page, pages, note),
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Spacer(Modifier.size(12.dp))
                Text(
                    "${(overall.coerceIn(0f, 1f) * 100).roundToInt()}%",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(Modifier.height(14.dp))
            BarRow(T("当前页", "This page"), pageFrac, paused, 8.dp, strong = false, animate = animate)
            Spacer(Modifier.height(10.dp))
            BarRow(T("整个文件", "Whole file"), overall, paused, 12.dp, strong = true, animate = animate)
            Spacer(Modifier.height(16.dp))

            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                JobButton(
                    label = if (paused) T("继续", "Resume") else T("暂停", "Pause"),
                    icon = if (paused) Glyph.PLAY else Glyph.PAUSE,
                    accent = MaterialTheme.colorScheme.primary,
                    filled = true,
                    onClick = if (paused) onResume else onPause
                )
                Spacer(Modifier.size(12.dp))
                JobButton(
                    label = T("停止", "Stop"),
                    icon = Glyph.STOP,
                    accent = MaterialTheme.colorScheme.error,
                    filled = false,
                    onClick = onStop
                )
            }
        }
    }
}

/** 「第 3 / 12 页」——页数为 0 时（刚起步）不摆假数字 */
@Composable
private fun pageLine(page: Int, total: Int, note: String): String {
    if (total <= 0) return T("正在准备…", "Getting ready…")
    val base = T("第 $page / $total 页", "Page $page of $total")
    return if (note.isBlank()) base else "$base · $note"
}

@Composable
private fun BarRow(
    label: String,
    frac: Float,
    paused: Boolean,
    height: Dp,
    strong: Boolean,
    animate: Boolean
) {
    val f = frac.coerceIn(0f, 1f)
    Column(Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(label, fontSize = 11.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.weight(1f))
            Text(
                "${(f * 100).roundToInt()}%",
                fontSize = 11.5.sp,
                fontWeight = if (strong) FontWeight.SemiBold else FontWeight.Normal,
                color = if (strong) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(Modifier.height(5.dp))
        ProgressBar(
            frac = f,
            paused = paused,
            animate = animate,
            height = height,
            fill = if (strong) {
                Brush.horizontalGradient(
                    listOf(MaterialTheme.colorScheme.primary, MaterialTheme.colorScheme.tertiary)
                )
            } else {
                Brush.horizontalGradient(
                    listOf(
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.55f),
                        MaterialTheme.colorScheme.primary.copy(alpha = 0.8f)
                    )
                )
            }
        )
    }
}

/**
 * 圆角进度条。两端都是半圆，填充走渐变；暂停时停掉流光，
 * 一眼就能看出「没卡住，是停着的」。
 */
@Composable
private fun ProgressBar(frac: Float, paused: Boolean, animate: Boolean, height: Dp, fill: Brush) {
    val track = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
    // 流光只在「真的在跑」时才建动画：无限动画会让界面测试里的 looper.idle()
    // 永远等不到空闲帧，截图测试会直接卡死（这也是 animate 参数存在的原因）。
    val phase: Float = if (animate && !paused) {
        val shimmer = rememberInfiniteTransition(label = "bar")
        shimmer.animateFloat(
            initialValue = -0.3f,
            targetValue = 1.3f,
            animationSpec = infiniteRepeatable(
                tween(1500, easing = LinearEasing),
                RepeatMode.Restart
            ),
            label = "phase"
        ).value
    } else 1.3f
    Canvas(
        Modifier
            .fillMaxWidth()
            .height(height)
    ) {
        val r = CornerRadius(size.height / 2f, size.height / 2f)
        drawRoundRect(color = track, cornerRadius = r)
        val w = (size.width * frac).coerceAtLeast(if (frac > 0f) size.height else 0f)
        if (w > 0.5f) {
            drawRoundRect(brush = fill, size = Size(w, size.height), cornerRadius = r)
            if (!paused && frac < 0.999f) {
                // 流光：只在还没跑完时出现，给「正在动」一个连续提示
                val x = size.width * phase
                drawRoundRect(
                    brush = Brush.horizontalGradient(
                        listOf(
                            Color.Transparent,
                            Color.White.copy(alpha = 0.34f),
                            Color.Transparent
                        ),
                        startX = x - size.height,
                        endX = x + size.height
                    ),
                    size = Size(w, size.height),
                    cornerRadius = r
                )
            }
        }
    }
}

enum class Glyph { PLAY, PAUSE, STOP }

/** 不引 material-icons-extended：三个图标三十行 Canvas 就够，粗细也好统一 */
@Composable
private fun GlyphIcon(kind: Glyph, color: Color) {
    Canvas(Modifier.size(13.dp)) {
        val w = size.width
        val h = size.height
        when (kind) {
            Glyph.PLAY -> drawPath(
                Path().apply {
                    moveTo(w * 0.24f, h * 0.10f)
                    lineTo(w * 0.88f, h * 0.5f)
                    lineTo(w * 0.24f, h * 0.90f)
                    close()
                },
                color
            )

            Glyph.PAUSE -> {
                val bw = w * 0.26f
                val c = CornerRadius(bw * 0.35f, bw * 0.35f)
                drawRoundRect(color, Offset(w * 0.18f, h * 0.13f), Size(bw, h * 0.74f), c)
                drawRoundRect(color, Offset(w * 0.56f, h * 0.13f), Size(bw, h * 0.74f), c)
            }

            Glyph.STOP -> drawRoundRect(
                color, Offset(w * 0.15f, h * 0.15f), Size(w * 0.70f, h * 0.70f),
                CornerRadius(w * 0.18f, w * 0.18f)
            )
        }
    }
}

@Composable
private fun JobButton(
    label: String,
    icon: Glyph,
    accent: Color,
    filled: Boolean,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        shape = CircleShape,
        color = if (filled) accent else accent.copy(alpha = 0.10f),
        modifier = Modifier.height(40.dp)
    ) {
        Row(
            Modifier.padding(horizontal = 22.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            GlyphIcon(icon, if (filled) MaterialTheme.colorScheme.onPrimary else accent)
            Spacer(Modifier.size(7.dp))
            Text(
                label,
                fontSize = 13.5.sp,
                fontWeight = FontWeight.SemiBold,
                color = if (filled) MaterialTheme.colorScheme.onPrimary else accent
            )
        }
    }
}
