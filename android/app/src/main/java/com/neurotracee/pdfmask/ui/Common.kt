package com.neurotracee.pdfmask.ui

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.window.layout.FoldingFeature
import androidx.window.layout.WindowInfoTracker

fun Context.findActivity(): Activity? {
    var c: Context = this
    while (c is ContextWrapper) {
        if (c is Activity) return c
        c = c.baseContext
    }
    return null
}

/** 折叠屏的铰链 / 折叠状态 */
data class FoldInfo(val separating: Boolean, val vertical: Boolean, val hingeWidthDp: Int)

@Composable
fun rememberFold(): FoldInfo {
    val ctx = LocalContext.current
    val activity = remember(ctx) { ctx.findActivity() }
    var info by remember { mutableStateOf(FoldInfo(false, true, 0)) }
    val density = LocalDensity.current
    LaunchedEffect(activity) {
        val act = activity ?: return@LaunchedEffect
        try {
            WindowInfoTracker.getOrCreate(ctx).windowLayoutInfo(act).collect { layout ->
                val f = layout.displayFeatures.filterIsInstance<FoldingFeature>().firstOrNull()
                info = if (f == null) {
                    FoldInfo(false, true, 0)
                } else {
                    val vertical = f.orientation == FoldingFeature.Orientation.VERTICAL
                    val wDp = with(density) { f.bounds.width().toDp().value.toInt() }
                    val hDp = with(density) { f.bounds.height().toDp().value.toInt() }
                    FoldInfo(
                        separating = f.isSeparating,
                        vertical = vertical,
                        hingeWidthDp = if (vertical) wDp else hDp
                    )
                }
            }
        } catch (_: Throwable) {
        }
    }
    return info
}

/** 左上角红色小标签（深浅色各自一套配色，保证对比度） */
@Composable
fun RedTag(text: String, modifier: Modifier = Modifier) {
    val dark = isSystemInDarkTheme()
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .background(if (dark) Color(0xFF52222A) else Color(0xFFFFEBEE))
            .padding(horizontal = 5.dp, vertical = 1.5.dp)
    ) {
        Text(
            text = text,
            color = if (dark) Color(0xFFFF9A9A) else Color(0xFFD32F2F),
            fontSize = 9.sp,
            lineHeight = 12.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1
        )
    }
}

@Composable
fun AmberChip(text: String, modifier: Modifier = Modifier) {
    val dark = isSystemInDarkTheme()
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(4.dp))
            .background(if (dark) Color(0xFF4A3418) else Color(0xFFFFF4E5))
            .padding(horizontal = 5.dp, vertical = 1.5.dp)
    ) {
        Text(
            text = text,
            color = if (dark) Color(0xFFFFC46B) else Color(0xFFB45309),
            fontSize = 9.sp,
            lineHeight = 12.sp,
            fontWeight = FontWeight.Medium,
            maxLines = 1
        )
    }
}

@Composable
fun SectionLabel(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelMedium,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}
