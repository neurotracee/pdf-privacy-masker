package com.neurotracee.pdfmask.ui

import android.graphics.Bitmap

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.Image
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.clipPath
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.neurotracee.pdfmask.AppViewModel
import com.neurotracee.pdfmask.Stage
import com.neurotracee.pdfmask.core.Finding
import com.neurotracee.pdfmask.core.Kind
import com.neurotracee.pdfmask.core.Rect
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

@Composable
fun WorkScreen(
    vm: AppViewModel,
    expanded: Boolean,
    fold: FoldInfo,
    onPickAnother: () -> Unit,
    onGenerate: () -> Unit,
    onOpenFile: (String) -> Unit,
    /** 仅截图测试用：让识别结果面板一开始就是展开的 */
    initialListOpen: Boolean = false,
    /** 仅截图测试用：把拖拽框选定格在某个归一化位置（0~1），用来截放大镜 */
    testDragAt: Offset? = null
) {
    var fullPreview by remember { mutableStateOf(false) }
    // 识别结果面板：默认收起，把屏幕让给预览，需要勾选时再展开
    var listOpen by remember { mutableStateOf(initialListOpen) }
    val hinge = if (fold.separating && fold.vertical) fold.hingeWidthDp.dp else 0.dp

    Box(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize()) {
            DocHeader(vm, onPickAnother)
            WorkHintBar()
            Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))

            if (expanded) {
                Row(Modifier.weight(1f)) {
                    FindingList(vm, Modifier.weight(0.34f))
                    if (hinge > 0.dp) {
                        Box(
                            Modifier
                                .width(hinge)
                                .fillMaxSize()
                                .background(MaterialTheme.colorScheme.background)
                        )
                    } else {
                        Box(
                            Modifier
                                .width(1.dp)
                                .fillMaxSize()
                                .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.35f))
                        )
                    }
                    Column(Modifier.weight(0.66f).fillMaxSize()) {
                        PreviewPane(vm, Modifier.fillMaxSize(), onExpand = { fullPreview = true }, testDragAt = testDragAt)
                    }
                }
            } else {
                // 单栏：预览占满内容区（屏高的 ~80%），低头就能看清字、能精确框选；
                // 自动识别结果收进底部折叠条，点开才浮上来，随时可以收回
                BoxWithConstraints(Modifier.weight(1f)) {
                    val panelH = (maxHeight * 0.66f).coerceAtLeast(220.dp)
                    Column(Modifier.fillMaxSize()) {
                        PreviewPane(
                            vm,
                            Modifier
                                .fillMaxWidth()
                                .weight(1f),
                            onExpand = { fullPreview = true },
                            testDragAt = testDragAt
                        )
                        CollapseBar(vm, open = listOpen, onToggle = { listOpen = !listOpen })
                    }
                    // 抽成独立组件，避免命中外层 ColumnScope 的 AnimatedVisibility 重载
                    FindingOverlay(
                        vm = vm,
                        open = listOpen,
                        panelHeight = panelH,
                        onClose = { listOpen = false }
                    )
                }
            }

            BottomBar(vm, onGenerate)
        }

        if (vm.stage == Stage.MASKING) {
            MaskingOverlay(vm.progress)
        }

        if (vm.stage == Stage.DONE) {
            DoneDialog(vm) { onOpenFile(vm.savedName) }
        }

        if (fullPreview) {
            FullPreviewDialog(vm) { fullPreview = false }
        }
    }
}

@Composable
private fun DocHeader(vm: AppViewModel, onPickAnother: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onPickAnother, modifier = Modifier.size(36.dp)) {
            Icon(
                Icons.Filled.ArrowBack, T("换一个文件", "Change file"),
                modifier = Modifier.size(20.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Column(Modifier.weight(1f)) {
            Text(
                vm.docName,
                fontSize = 13.5.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 1,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                T(
                    "${vm.pages.size} 页 · 识别到 ${vm.findings.size} 处 · 已选 ${vm.selected.size} 处",
                    "${vm.pages.size} pages · ${vm.findings.size} found · ${vm.selected.size} selected"
                ),
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/** 顶部精简提示：告诉用户能拖、能双击取消，省得自己摸索 */
@Composable
private fun WorkHintBar() {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp)
            .padding(bottom = 7.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.07f))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            Icons.Filled.Info,
            contentDescription = null,
            modifier = Modifier.size(13.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        Spacer(Modifier.width(6.dp))
        Text(
            T(
                "拖动可框选 · 双击方框取消或恢复打码",
                "Drag to box-select · double-tap a box to toggle masking"
            ),
            fontSize = 11.5.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

/** 浮层宿主：独立成函数，避免外层 ColumnScope 的 AnimatedVisibility 重载抢占解析 */
@Composable
private fun FindingOverlay(
    vm: AppViewModel,
    open: Boolean,
    panelHeight: Dp,
    onClose: () -> Unit
) {
    Box(Modifier.fillMaxSize()) {
        AnimatedVisibility(
            visible = open,
            enter = slideInVertically(tween(200)) { it } + fadeIn(tween(200)),
            exit = slideOutVertically(tween(160)) { it } + fadeOut(tween(160)),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 48.dp)
        ) {
            FindingPanel(vm, height = panelHeight, onClose = onClose)
        }
    }
}

/** 底部折叠条：平时只占 48dp，把屏幕让给预览；点一下展开识别结果 */
@Composable
private fun CollapseBar(vm: AppViewModel, open: Boolean, onToggle: () -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 4.dp) {
        Row(
            Modifier
                .fillMaxWidth()
                .height(48.dp)
                .clickable { onToggle() }
                .padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                T("自动识别结果", "Detected"),
                fontSize = 12.5.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(Modifier.width(7.dp))
            Text(
                T(
                    "${vm.findings.size} 处 · 已选 ${vm.selected.size}",
                    "${vm.findings.size} found · ${vm.selected.size} on"
                ),
                fontSize = 11.5.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.weight(1f))
            Text(
                if (open) T("收起", "Hide") else T("展开", "Show"),
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.primary
            )
            Icon(
                if (open) Icons.Filled.KeyboardArrowDown else Icons.Filled.KeyboardArrowUp,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
                tint = MaterialTheme.colorScheme.primary
            )
        }
    }
}

/** 识别结果浮层面板：从折叠条上方升起，覆盖预览下半部分，不影响底部按钮 */
@Composable
private fun FindingPanel(vm: AppViewModel, height: Dp, onClose: () -> Unit) {
    Surface(
        Modifier
            .fillMaxWidth()
            .height(height),
        shape = RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 16.dp
    ) {
        Column(Modifier.fillMaxSize()) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .clickable { onClose() }
                    .padding(start = 16.dp, end = 12.dp, top = 10.dp, bottom = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        T("自动识别结果", "Detected items"),
                        fontSize = 13.5.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        T(
                            "已选 ${vm.selected.size} / ${vm.findings.size} 处",
                            "${vm.selected.size} / ${vm.findings.size} selected"
                        ),
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                TextButton(
                    onClick = {
                        val all = vm.selected.size == vm.findings.size && vm.findings.isNotEmpty()
                        vm.selectAll(!all)
                    },
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp)
                ) {
                    Text(
                        if (vm.selected.size == vm.findings.size && vm.findings.isNotEmpty())
                            T("全不选", "None") else T("全选", "All"),
                        fontSize = 12.sp
                    )
                }
                Icon(
                    Icons.Filled.KeyboardArrowDown,
                    contentDescription = T("收起", "Hide"),
                    modifier = Modifier.size(22.dp),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.35f))
            FindingList(vm, Modifier.weight(1f))
        }
    }
}

@Composable
private fun FindingList(vm: AppViewModel, modifier: Modifier) {
    val state = rememberLazyListState()
    val grouped = remember(vm.findings) {
        Kind.ORDER.mapNotNull { k ->
            val list = vm.findings.filter { it.type == k }
            if (list.isEmpty()) null else k to list
        }
    }
    LazyColumn(modifier.fillMaxWidth(), state = state) {
        grouped.forEach { (k, list) ->
            item(key = "h_$k") {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.background)
                        .padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        if (com.neurotracee.pdfmask.AppPrefs.isEn) Kind.labelEn(k) else Kind.label(k),
                        fontSize = 11.5.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        "${list.size}",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                    )
                    if (k == Kind.MANUAL) {
                        Spacer(Modifier.weight(1f))
                        Text(
                            T("清除全部", "Clear all"),
                            fontSize = 11.5.sp,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.clickable { vm.clearManual() }
                        )
                    }
                }
            }
            items(list, key = { it.id }) { f ->
                FindingRow(
                    f = f,
                    checked = f.id in vm.selected,
                    onToggle = { vm.toggle(f.id) },
                    onClick = { vm.goPage(f.page) },
                    onDelete = { vm.removeFinding(f.id) }
                )
            }
        }
        item { Spacer(Modifier.height(10.dp)) }
    }
}

@Composable
private fun FindingRow(
    f: Finding,
    checked: Boolean,
    onToggle: () -> Unit,
    onClick: () -> Unit,
    onDelete: () -> Unit
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(start = 12.dp, end = 14.dp, top = 2.dp, bottom = 2.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Checkbox(
            checked = checked,
            onCheckedChange = { onToggle() },
            modifier = Modifier.size(38.dp),
            colors = CheckboxDefaults.colors(
                checkedColor = MaterialTheme.colorScheme.primary,
                uncheckedColor = MaterialTheme.colorScheme.outline
            )
        )
        Spacer(Modifier.width(4.dp))
        Column(Modifier.weight(1f)) {
            Text(
                if (f.type == Kind.MANUAL) T("手动框选区域", "Manual region")
                else maskPreview(f.type, f.text),
                fontSize = 13.5.sp,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1
            )
            Text(
                T("第 ${f.page + 1} 页", "Page ${f.page + 1}") +
                    if (f.note.isNotEmpty()) " · ${f.note}" else "",
                fontSize = 10.5.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1
            )
        }
        if (f.suspect) AmberChip(T("疑似", "Likely"))
        if (f.type == Kind.MANUAL) {
            TextButton(
                onClick = { onDelete() },
                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 8.dp),
                modifier = Modifier.size(width = 42.dp, height = 34.dp)
            ) {
                Text(T("删除", "Del"), fontSize = 11.5.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun PreviewPane(
    vm: AppViewModel,
    modifier: Modifier,
    onExpand: () -> Unit,
    testDragAt: Offset? = null
) {
    val page = vm.current
    val pageText = vm.pages.getOrNull(page)
    BoxWithConstraints(
        modifier.background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f))
    ) {
        val density = LocalDensity.current
        val widthPx = with(density) { maxWidth.toPx() }.toInt()
        LaunchedEffect(page, widthPx) {
            vm.ensureThumb(page, widthPx.coerceIn(320, 1500))
        }
        val bmp = vm.thumb(page)
        if (bmp == null || pageText == null) {
            Box(
                Modifier.fillMaxSize().clickable { onExpand() },
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(22.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        } else {
            // 页面等比例「完整放进」预览区：不裁切、不变形
            val wh = if (pageText.height > 0f) pageText.width / pageText.height else 0.707f
            val pad = 8.dp
            val navH = if (maxHeight > 170.dp) 44.dp else 0.dp
            val availW = (maxWidth - pad * 2).coerceAtLeast(40.dp)
            val availH = (maxHeight - pad * 2 - navH).coerceAtLeast(40.dp)
            var bw = availW
            var bh = bw / wh
            if (bh > availH) {
                bh = availH
                bw = bh * wh
            }
            val boxWpx = with(density) { bw.toPx() }
            val boxHpx = with(density) { bh.toPx() }
            val scaleX = if (boxWpx > 0f) boxWpx / pageText.width else 1f
            val scaleY = if (boxHpx > 0f) boxHpx / pageText.height else 1f

            var dragFrom by remember(page) {
                mutableStateOf(testDragAt?.let { Offset(it.x * boxWpx, it.y * boxHpx) })
            }
            var dragTo by remember(page) {
                mutableStateOf(
                    testDragAt?.let {
                        Offset((it.x + 0.10f) * boxWpx, (it.y + 0.12f) * boxHpx)
                    }
                )
            }
            val dash = remember { PathEffect.dashPathEffect(floatArrayOf(9f, 6f)) }
            val pageBmp = remember(bmp) { bmp.asImageBitmap() }
            // 双击命中：按页面坐标判断，另加 10dp 宽容，小字框也点得中
            val touchPadPx = with(density) { 10.dp.toPx() }
            // 提示文案在组合期取好，双击回调里不能调 @Composable
            val msgMaskOff = T("已取消这处打码", "Mask removed")
            val msgMaskOn = T("已恢复这处打码", "Mask restored")
            val hitTest: (Offset) -> Finding? = { pos ->
                val x = pos.x / scaleX
                val y = pos.y / scaleY
                val padX = if (scaleX > 0f) touchPadPx / scaleX else 0f
                val padY = if (scaleY > 0f) touchPadPx / scaleY else 0f
                vm.findings.lastOrNull {
                    it.page == page &&
                        x >= it.rect.x0 - padX && x <= it.rect.x1 + padX &&
                        y >= it.rect.y0 - padY && y <= it.rect.y1 + padY
                }
            }

            Column(
                Modifier
                    .fillMaxSize()
                    .padding(pad),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Box(
                    Modifier
                        .size(bw, bh)
                        .clip(RoundedCornerShape(4.dp))
                        // 轻点 = 放大查看；双击方框 = 取消/恢复该处打码；拖拽 = 手动框选
                        .pointerInput(page, scaleX, scaleY) {
                            detectTapGestures(
                                onTap = { onExpand() },
                                onDoubleTap = { pos ->
                                    val hit = hitTest(pos)
                                    if (hit != null) {
                                        val wasOn = hit.id in vm.selected
                                        vm.toggle(hit.id)
                                        vm.toast(if (wasOn) msgMaskOff else msgMaskOn)
                                    }
                                }
                            )
                        }
                        .pointerInput(page, scaleX, scaleY) {
                            detectDragGestures(
                                onDragStart = { o -> dragFrom = o; dragTo = o },
                                onDragEnd = {
                                    val a = dragFrom
                                    val b = dragTo
                                    dragFrom = null
                                    dragTo = null
                                    if (a != null && b != null) {
                                        val l = min(a.x, b.x)
                                        val t = min(a.y, b.y)
                                        val w = kotlin.math.abs(b.x - a.x)
                                        val h = kotlin.math.abs(b.y - a.y)
                                        if (w > 12f && h > 12f && scaleX > 0f && scaleY > 0f) {
                                            vm.addManual(
                                                page,
                                                Rect(l / scaleX, t / scaleY, (l + w) / scaleX, (t + h) / scaleY)
                                            )
                                        }
                                    }
                                },
                                onDragCancel = { dragFrom = null; dragTo = null }
                            ) { change, _ ->
                                dragTo = change.position
                                change.consume()
                            }
                        }
                ) {
                    Image(
                        bitmap = pageBmp,
                        contentDescription = T("第 ${page + 1} 页预览", "Page ${page + 1} preview"),
                        contentScale = ContentScale.FillBounds,
                        modifier = Modifier.fillMaxSize()
                    )
                    Canvas(Modifier.fillMaxSize()) {
                        val sx = size.width / pageText.width
                        val sy = size.height / pageText.height
                        for (f in vm.findings) {
                            if (f.page != page) continue
                            val on = f.id in vm.selected
                            val tl = Offset(f.rect.x0 * sx, f.rect.y0 * sy)
                            val sz = Size(
                                (f.rect.width * sx).coerceAtLeast(1f),
                                (f.rect.height * sy).coerceAtLeast(1f)
                            )
                            if (f.type == Kind.MANUAL) {
                                // 手动框选：蓝色虚线，一眼看得出是手画的
                                drawRect(
                                    color = if (on) Color(0x262563EB) else Color(0x1494A3B8),
                                    topLeft = tl, size = sz
                                )
                                drawRect(
                                    color = if (on) Color(0xFF2563EB) else Color(0xFF94A3B8),
                                    topLeft = tl, size = sz,
                                    style = Stroke(width = 1.8.dp.toPx(), pathEffect = dash)
                                )
                            } else {
                                val fill = when {
                                    f.suspect -> Color(0x55F59E0B)
                                    on -> Color(0x66E5484D)
                                    else -> Color(0x3394A3B8)
                                }
                                val stroke = when {
                                    f.suspect -> Color(0xFFB45309)
                                    on -> Color(0xFFE5484D)
                                    else -> Color(0xFF94A3B8)
                                }
                                drawRect(color = fill, topLeft = tl, size = sz)
                                if (on) {
                                    drawRect(
                                        color = stroke,
                                        topLeft = tl, size = sz,
                                        style = Stroke(width = 0.8f)
                                    )
                                }
                            }
                        }
                        // 正在拖拽的虚线预览框
                        val a = dragFrom
                        val b = dragTo
                        if (a != null && b != null) {
                            val l = min(a.x, b.x)
                            val t = min(a.y, b.y)
                            val w = kotlin.math.abs(b.x - a.x)
                            val h = kotlin.math.abs(b.y - a.y)
                            if (w > 1f && h > 1f) {
                                drawRect(Color(0x262563EB), Offset(l, t), Size(w, h))
                                drawRect(
                                    Color(0xFF2563EB), Offset(l, t), Size(w, h),
                                    style = Stroke(
                                        width = 1.8.dp.toPx(),
                                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 4f))
                                    )
                                )
                            }
                        }
                    }

                    // 放大镜：拖拽时在手指上方/右上方实时放大，松手即消失，
                    // 手指压住的那几个字在镜里看得清，落点也就准了；
                    // 正在拉的那条虚线框也一起映射进镜里，边框和手指始终对得上
                    val finger = dragTo
                    if (finger != null) {
                        val a0 = dragFrom
                        LoupeOverlay(
                            bmp = bmp,
                            finger = finger,
                            viewW = boxWpx,
                            viewH = boxHpx,
                            band = if (a0 != null) {
                                Rect(
                                    min(a0.x, finger.x), min(a0.y, finger.y),
                                    max(a0.x, finger.x), max(a0.y, finger.y)
                                )
                            } else null
                        )
                    }
                }

                if (navH > 0.dp) {
                    Spacer(Modifier.height(2.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        TextButton(onClick = { vm.goPage(page - 1) }, enabled = page > 0) {
                            Text(T("上一页", "Prev"), fontSize = 12.sp)
                        }
                        Text(
                            "${page + 1} / ${vm.pages.size}",
                            fontSize = 11.5.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        TextButton(
                            onClick = { vm.goPage(page + 1) },
                            enabled = page < vm.pages.size - 1
                        ) {
                            Text(T("下一页", "Next"), fontSize = 12.sp)
                        }
                    }
                }
            }
        }
    }
}

/**
 * 拖拽框选时的圆形放大镜：优先放在手指右上方（不挡视线），贴边时自动翻到另一侧。
 * 直接裁一块位图放大，渲染结果稳定，不依赖图层变换。
 * [band] 是正在拉的虚线框（页面坐标），会按同样的放大倍率画进镜里，
 * 这样手指被挡住时也能看清框边到底走到哪了。
 */
@Composable
private fun LoupeOverlay(
    bmp: Bitmap,
    finger: Offset,
    viewW: Float,
    viewH: Float,
    band: Rect? = null
) {
    val density = LocalDensity.current
    val zoom = 2.8f
    val d = 96.dp
    val dPx = with(density) { d.toPx() }
    val radius = dPx / 2f
    val pad = with(density) { 6.dp.toPx() }
    val dx = radius * 1.55f
    val dy = radius * 1.75f
    var cx = if (finger.x + dx + radius + pad <= viewW) finger.x + dx else finger.x - dx
    var cy = if (finger.y - dy - radius - pad >= 0f) finger.y - dy else finger.y + dy
    cx = cx.coerceIn(radius + pad, (viewW - radius - pad).coerceAtLeast(radius + pad))
    cy = cy.coerceIn(radius + pad, (viewH - radius - pad).coerceAtLeast(radius + pad))

    // 手指每挪 3px 才重裁一次，省得每帧都建位图
    val qx = (finger.x / 3f).toInt()
    val qy = (finger.y / 3f).toInt()
    val zoomed = remember(qx, qy, bmp) {
        cropLoupe(bmp, finger, viewW, viewH, dPx.toInt(), zoom)
    }

    Box(
        Modifier
            .offset { IntOffset((cx - radius).roundToInt(), (cy - radius).roundToInt()) }
            .size(d)
            .clip(CircleShape)
            .background(Color.White)
    ) {
        Image(
            bitmap = zoomed.asImageBitmap(),
            contentDescription = null,
            contentScale = ContentScale.FillBounds,
            modifier = Modifier.fillMaxSize()
        )
        Canvas(Modifier.matchParentSize()) {
            val r = size.minDimension / 2f
            val c = Offset(size.width / 2f, size.height / 2f)
            // 正在拉的虚线框：页面坐标 → 镜内坐标，倍率与位图一致，所以边和手指始终对齐
            if (band != null && band.width > 1f && band.height > 1f) {
                fun mx(x: Float) = c.x + (x - finger.x) * zoom
                fun my(y: Float) = c.y + (y - finger.y) * zoom
                val l = mx(band.x0)
                val t = my(band.y0)
                val rr = mx(band.x1)
                val bb = my(band.y1)
                drawRect(
                    color = Color(0x332563EB),
                    topLeft = Offset(l, t),
                    size = Size(rr - l, bb - t)
                )
                drawRect(
                    color = Color(0xFF2563EB),
                    topLeft = Offset(l, t),
                    size = Size(rr - l, bb - t),
                    style = Stroke(
                        width = 1.6.dp.toPx(),
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(5f, 4f))
                    )
                )
            }
            // 镜片外圈：白边压住图片，让圆看起来是块玻璃
            drawCircle(Color.White, r - 1.5.dp.toPx(), c, style = Stroke(width = 3.dp.toPx()))
            drawCircle(Color(0x552563EB), r - 0.5.dp.toPx(), c, style = Stroke(width = 1.dp.toPx()))
            // 镜心一个小圆点：对准的就是手指压住的那一点（比十字更不挡字）
            drawCircle(Color(0xCC2563EB), 2.dp.toPx(), c)
            drawCircle(Color.White, 1.dp.toPx(), c)
        }
    }
}

/** 从页面位图里裁出以手指为中心的一小块，放大到镜片大小 */
private fun cropLoupe(
    src: Bitmap,
    finger: Offset,
    viewW: Float,
    viewH: Float,
    dPx: Int,
    zoom: Float
): Bitmap {
    val sx = if (viewW > 0f) src.width / viewW else 1f
    val sy = if (viewH > 0f) src.height / viewH else 1f
    val halfX = dPx / 2f / zoom * sx
    val halfY = dPx / 2f / zoom * sy
    val ccx = finger.x * sx
    val ccy = finger.y * sy
    val x0 = (ccx - halfX).roundToInt().coerceIn(0, src.width - 1)
    val y0 = (ccy - halfY).roundToInt().coerceIn(0, src.height - 1)
    val x1 = (ccx + halfX).roundToInt().coerceIn(x0 + 1, src.width)
    val y1 = (ccy + halfY).roundToInt().coerceIn(y0 + 1, src.height)
    val crop = Bitmap.createBitmap(src, x0, y0, x1 - x0, y1 - y0)
    return Bitmap.createScaledBitmap(crop, dPx, dPx, true)
}

@Composable
private fun FullPreviewDialog(vm: AppViewModel, onClose: () -> Unit) {
    Dialog(
        onDismissRequest = onClose,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            Modifier
                .fillMaxSize()
                .padding(0.dp),
            color = Color(0xFF0B0F14)
        ) {
            Box(Modifier.fillMaxSize()) {
                PreviewPane(vm, Modifier.fillMaxSize(), onExpand = {})
                IconButton(
                    onClick = onClose,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(10.dp)
                        .size(38.dp)
                        .clip(RoundedCornerShape(19.dp))
                        .background(Color(0x66000000))
                ) {
                    Icon(Icons.Filled.Close, T("关闭", "Close"), tint = Color.White, modifier = Modifier.size(20.dp))
                }
            }
        }
    }
}

@Composable
private fun BottomBar(vm: AppViewModel, onGenerate: () -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 6.dp) {
        Row(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    T(
                        "已选 ${vm.selected.size} / ${vm.findings.size}",
                        "${vm.selected.size} / ${vm.findings.size} selected"
                    ),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                val pagesHit = vm.findings.filter { it.id in vm.selected }.map { it.page }.toSet().size
                Text(
                    T("涉及 $pagesHit 页", "$pagesHit page(s)"),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            TextButton(
                onClick = {
                    val all = vm.selected.size == vm.findings.size
                    vm.selectAll(!all)
                },
                enabled = vm.findings.isNotEmpty()
            ) {
                Text(
                    if (vm.selected.size == vm.findings.size && vm.findings.isNotEmpty())
                        T("全不选", "None")
                    else T("全选", "All"),
                    fontSize = 12.5.sp
                )
            }
            Spacer(Modifier.width(4.dp))
            Button(
                onClick = onGenerate,
                enabled = vm.selected.isNotEmpty() && vm.stage == Stage.READY,
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text(
                    T("生成打码 PDF", "Mask PDF"),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }
    }
}

@Composable
private fun MaskingOverlay(progress: Float) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Color(0x99101820)),
        contentAlignment = Alignment.Center
    ) {
        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surface) {
            Column(
                Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(30.dp),
                    strokeWidth = 3.dp,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(14.dp))
                Text(T("正在生成…", "Generating…"), fontSize = 14.sp, fontWeight = FontWeight.Medium)
                Spacer(Modifier.height(10.dp))
                LinearProgressIndicator(
                    progress = { progress },
                    modifier = Modifier.width(180.dp).height(4.dp).clip(RoundedCornerShape(2.dp))
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    "${(progress * 100).toInt()}%",
                    fontSize = 11.5.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun DoneDialog(vm: AppViewModel, onOpen: () -> Unit) {
    val s = vm.summary
    Dialog(onDismissRequest = { vm.reset() }) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(22.dp)) {
                Text(
                    T("打码完成", "Done"),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    vm.savedName,
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.primary,
                    maxLines = 2
                )
                if (s != null) {
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                        Stat(T("页数", "Pages"), "${s.pages}")
                        Stat(T("打码处", "Masks"), "${s.count}")
                        Stat(T("命中页", "Pages hit"), "${s.hitPages}")
                    }
                    Spacer(Modifier.height(12.dp))
                    val txt = s.stats.entries.joinToString(" · ") { "${it.key} ${it.value}" }
                    if (txt.isNotEmpty()) {
                        Text(
                            txt,
                            fontSize = 11.5.sp,
                            lineHeight = 18.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Spacer(Modifier.height(14.dp))
                Text(
                    T(
                        "输出为图片型 PDF，文字层已完全移除。",
                        "Output is an image-only PDF; the text layer is gone."
                    ),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(18.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    TextButton(onClick = { vm.reset() }, modifier = Modifier.weight(1f)) {
                        Text(T("再弄一份", "Another"), fontSize = 13.sp)
                    }
                    Button(
                        onClick = { vm.reset() },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text(T("完成", "Done"), fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun Stat(label: String, value: String) {
    Column {
        Text(
            value,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(label, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
