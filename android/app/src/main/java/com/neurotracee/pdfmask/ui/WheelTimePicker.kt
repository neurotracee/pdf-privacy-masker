package com.neurotracee.pdfmask.ui

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animate
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.roundToInt

/** 一格的高度；上下各露两格，所以总高 5 格 */
private val CELL = 40.dp
private const val VISIBLE_EACH_SIDE = 2

/** 松手后的吸附动画时长：用户指定 180ms */
private const val SNAP_MS = 180

/**
 * 单列滚轮：上下拖动数字跟着走，松手吸附到最近一格。
 * 轻点（没拖）可以弹出输入框直接打字。
 *
 * @param enabled false 时整列变灰且不可拖动（用于「分」在「时」被推过之前）
 */
@Composable
private fun WheelColumn(
    label: String,
    value: Int,
    maxValue: Int,
    enabled: Boolean,
    onValueChange: (Int) -> Unit,
    onTypeRequest: () -> Unit,
    modifier: Modifier = Modifier
) {
    val cellPx = with(LocalDensity.current) { CELL.toPx() }
    val scope = rememberCoroutineScope()

    // pos = 当前滚轮位置（以「格」为单位，浮点），value 是它四舍五入后的值
    var pos by remember { mutableFloatStateOf(value.toFloat()) }
    var dragging by remember { mutableStateOf(false) }
    var animJob by remember { mutableStateOf<Job?>(null) }

    fun commit(idx: Int) {
        val safe = idx.coerceIn(0, maxValue)
        if (safe != value) onValueChange(safe)
    }

    /** 吸附到最近一格，180ms */
    fun snap() {
        val target = pos.roundToInt().coerceIn(0, maxValue)
        commit(target)
        animJob?.cancel()
        animJob = scope.launch {
            val from = pos
            val to = target.toFloat()
            if (abs(from - to) < 0.01f) {
                pos = to
                return@launch
            }
            animate(
                initialValue = from,
                targetValue = to,
                animationSpec = tween(SNAP_MS, easing = FastOutSlowInEasing)
            ) { v, _ -> pos = v }
            pos = to
        }
    }

    // 外部改值（打字输入 / 解锁后同步）时，滚轮跟着滑过去
    LaunchedEffect(value, enabled) {
        if (!dragging && abs(pos - value) > 0.01f) {
            animJob?.cancel()
            val from = pos
            val to = value.toFloat()
            animate(from, to, animationSpec = tween(SNAP_MS, easing = FastOutSlowInEasing)) { v, _ ->
                pos = v
            }
            pos = to
        }
    }

    val accent = MaterialTheme.colorScheme.primary
    val ink = MaterialTheme.colorScheme.onSurface
    val inkDim = MaterialTheme.colorScheme.onSurfaceVariant

    Column(modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            label,
            fontSize = 11.sp,
            color = if (enabled) inkDim else inkDim.copy(alpha = 0.45f)
        )
        Spacer(Modifier.height(6.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(CELL * (VISIBLE_EACH_SIDE * 2 + 1))
                .clipToBounds()
                .pointerInput(enabled, maxValue) {
                    if (!enabled) return@pointerInput
                    awaitEachGesture {
                        val down = awaitFirstDown(requireUnconsumed = false)
                        var totalDy = 0f
                        var isDrag = false
                        val slop = viewConfiguration.touchSlop
                        while (true) {
                            val ev = awaitPointerEvent()
                            val ch = ev.changes.firstOrNull { it.id == down.id } ?: break
                            if (ch.pressed) {
                                val dy = ch.position.y - ch.previousPosition.y
                                totalDy += dy
                                if (!isDrag && abs(totalDy) > slop) {
                                    isDrag = true
                                    dragging = true
                                    animJob?.cancel()
                                }
                                if (isDrag) {
                                    ch.consume()
                                    val np = (pos - dy / cellPx).coerceIn(0f, maxValue.toFloat())
                                    pos = np
                                    // 推过一整格时值立刻更新
                                    commit(np.roundToInt())
                                }
                            } else {
                                break
                            }
                        }
                        if (isDrag) {
                            dragging = false
                            snap()
                        } else {
                            // 没拖动 = 轻点，走键盘输入
                            onTypeRequest()
                        }
                    }
                },
            contentAlignment = Alignment.Center
        ) {
            // 中间选中格的高亮外框
            Box(
                Modifier
                    .fillMaxWidth(0.86f)
                    .height(CELL)
                    .background(
                        accent.copy(alpha = if (enabled) 0.07f else 0.03f),
                        RoundedCornerShape(10.dp)
                    )
                    .border(
                        1.5.dp,
                        accent.copy(alpha = if (enabled) 0.75f else 0.25f),
                        RoundedCornerShape(10.dp)
                    )
            )

            for (i in 0..maxValue) {
                val d = i - pos
                if (abs(d) > VISIBLE_EACH_SIDE + 0.75f) continue
                val a = (1f - abs(d) * 0.42f).coerceIn(0.12f, 1f) * (if (enabled) 1f else 0.45f)
                val bold = abs(d) < 0.5f
                Text(
                    text = "%02d".format(i),
                    fontSize = 20.sp,
                    fontWeight = if (bold) FontWeight.SemiBold else FontWeight.Normal,
                    color = ink,
                    modifier = Modifier
                        .offset(y = CELL * d)
                        .graphicsLayer { alpha = a }
                )
            }
        }
    }
}

/**
 * 选时分的滚轮弹窗：左边小时、右边分钟，「确定」在右下角。
 */
@Composable
fun WheelTimePickerDialog(
    initialHour: Int,
    initialMinute: Int,
    title: String? = null,
    onDismiss: () -> Unit,
    onConfirm: (Int, Int) -> Unit
) {
    var hour by remember { mutableIntStateOf(initialHour.coerceIn(0, 23)) }
    var minute by remember { mutableIntStateOf(initialMinute.coerceIn(0, 59)) }
    // 「分」在「时」被推过之前锁住
    var minuteUnlocked by remember { mutableStateOf(false) }
    // 正在哪一列打字（null = 没在输入）
    var typeTarget by remember { mutableStateOf<String?>(null) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(20.dp)) {
                Text(
                    title ?: T("选择具体时间", "Pick a time"),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    T("上下推动滚轮，松手会自动对齐；轻点滚轮可以直接打字。",
                      "Drag to scroll, release to snap. Tap a wheel to type."),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(14.dp))

                Row(
                    Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    WheelColumn(
                        label = T("时", "Hour"),
                        value = hour,
                        maxValue = 23,
                        enabled = true,
                        onValueChange = { hour = it; minuteUnlocked = true },
                        onTypeRequest = { typeTarget = "hour" },
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        ":",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.offset(y = 8.dp)
                    )
                    WheelColumn(
                        label = T("分", "Minute"),
                        value = minute,
                        maxValue = 59,
                        enabled = minuteUnlocked,
                        onValueChange = { minute = it },
                        onTypeRequest = { typeTarget = "minute" },
                        modifier = Modifier.weight(1f)
                    )
                }

                if (!minuteUnlocked) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        T("先把「时」推一下，分钟才会解锁",
                          "Nudge the hour wheel first to unlock minutes"),
                        fontSize = 10.5.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(Modifier.height(12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onDismiss) {
                        Text(T("取消", "Cancel"), fontSize = 13.sp)
                    }
                    Spacer(Modifier.width(6.dp))
                    Button(
                        onClick = { onConfirm(hour, minute) },
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text(T("确定", "OK"), fontSize = 13.sp)
                    }
                }
            }
        }
    }

    // 轻点滚轮后的键盘输入
    typeTarget?.let { target ->
        val isHour = target == "hour"
        var buf by remember(target) {
            mutableStateOf((if (isHour) hour else minute).toString())
        }
        AlertDialog(
            onDismissRequest = { typeTarget = null },
            title = {
                Text(
                    if (isHour) T("输入小时（0–23）", "Enter hour (0–23)")
                    else T("输入分钟（0–59）", "Enter minute (0–59)"),
                    fontSize = 15.sp
                )
            },
            text = {
                OutlinedTextField(
                    value = buf,
                    onValueChange = { s -> buf = s.filter { it.isDigit() }.take(2) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    val n = buf.toIntOrNull()
                    if (n != null) {
                        if (isHour) {
                            hour = n.coerceIn(0, 23)
                            minuteUnlocked = true
                        } else {
                            minute = n.coerceIn(0, 59)
                        }
                    }
                    typeTarget = null
                }) { Text(T("确定", "OK")) }
            },
            dismissButton = {
                TextButton(onClick = { typeTarget = null }) { Text(T("取消", "Cancel")) }
            }
        )
    }
}
