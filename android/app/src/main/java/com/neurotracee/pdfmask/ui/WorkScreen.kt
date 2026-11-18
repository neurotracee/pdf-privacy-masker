package com.neurotracee.pdfmask.ui

import android.graphics.Bitmap

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.ui.input.pointer.changedToUpIgnoreConsumed
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
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
    // 0 = 只看（轻点放大 / 双击取消）；1 = 手动框选；2 = 橡皮擦（局部恢复）
    // 用文档身份做 key：换了文件一定回到「只看」，不会把上一份的模式带过来
    var editMode by remember(vm.docKey) { mutableStateOf(0) }
    // 识别结果面板：默认收起，把屏幕让给预览，需要勾选时再展开
    var listOpen by remember { mutableStateOf(initialListOpen) }
    val hinge = if (fold.separating && fold.vertical) fold.hingeWidthDp.dp else 0.dp

    Box(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize()) {
            DocHeader(vm, onPickAnother)
            WorkHintBar(editMode)
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 2.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                TextButton(
                    onClick = { editMode = if (editMode == 1) 0 else 1 },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        if (editMode == 1) T("✓ 手动框选", "✓ Box") else T("手动框选", "Box"),
                        fontSize = 12.5.sp
                    )
                }
                TextButton(
                    onClick = { editMode = if (editMode == 2) 0 else 2 },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(
                        if (editMode == 2) T("✓ 橡皮擦", "✓ Erase") else T("橡皮擦", "Erase"),
                        fontSize = 12.5.sp
                    )
                }
                // 一键回到刚识别完的样子：擦除、手动框、取消过的勾选全部复位。
                // 换文件时本来就默认回到这个状态，这个按钮是给「改乱了想重来」用的。
                val msgReset = T("已恢复到初始状态", "Back to the initial state")
                val msgAlready = T("当前就是初始状态", "Already at the initial state")
                TextButton(
                    onClick = {
                        val changed = vm.restoreDefaults()
                        editMode = 0
                        vm.toast(if (changed) msgReset else msgAlready)
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(T("恢复默认", "Reset"), fontSize = 12.5.sp)
                }
            }
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
                        PreviewPane(vm, Modifier.fillMaxSize(), editMode, onExpand = { fullPreview = true }, testDragAt = testDragAt)
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
                            editMode,
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

        if (vm.stage == Stage.DONE) {
            DoneDialog(vm) { onOpenFile(vm.savedName) }
        }

        if (fullPreview) {
            FullPreviewDialog(
                vm = vm,
                editMode = editMode,
                onEditMode = { editMode = it }
            ) { fullPreview = false }
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
                // 一处都没检出来、但 OCR 确实跑过时，把体检数字直接摆在这行灰字里：
                // 「渲染 8 页 · 检测框 0 个」和「检测框 120 个 · 认出 0 行」是两种完全
                // 不同的故障，截个图就够定位，不用再让用户配合抓日志。
                if (vm.findings.isEmpty() && vm.ocrStats.isNotBlank()) {
                    T(
                        "${vm.pages.size} 页 · 识别到 0 处 · OCR：${vm.ocrStats}",
                        "${vm.pages.size} pages · 0 found · OCR: ${vm.ocrStats}"
                    )
                } else {
                    T(
                        "${vm.pages.size} 页 · 识别到 ${vm.findings.size} 处 · 已选 ${vm.selected.size} 处",
                        "${vm.pages.size} pages · ${vm.findings.size} found · ${vm.selected.size} selected"
                    )
                },
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/** 顶部精简提示：告诉用户能拖、能双击取消，省得自己摸索 */
@Composable
private fun WorkHintBar(editMode: Int = 0) {
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
            if (editMode == 2) T(
                "橡皮擦：长按拖过要恢复的那一小块 · 只恢复划过的范围 · 轻点撤销上一笔",
                "Eraser: long-press and drag over the area to restore · only that patch comes back · tap to undo"
            ) else if (editMode == 1) T(
                "手动框选：长按拖动画框 · 双指缩放移动 · 双击取消这处打码",
                "Box: long-press to draw · pinch to zoom/move · double-tap to toggle a mask"
            ) else T(
                "双指缩放/移动 · 长按拖动画框 · 双击取消",
                "Pinch to zoom/move · long-press to box · double-tap to toggle"
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
    editMode: Int = 0,
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
            // 预览缩放与平移：双指捏合或按住拖动空白处；缩放后单指拖动改为平移，
            // 想画框就长按再拖——1 倍时行为完全不变，老用户的手感不会被打乱。
            var zoom by remember(page) { mutableFloatStateOf(1f) }
            var pan by remember(page) { mutableStateOf(Offset.Zero) }
            var lastTapAt by remember { mutableLongStateOf(0L) }
            var lastTapPos by remember { mutableStateOf(Offset.Zero) }
            var pendingTap by remember { mutableStateOf<Job?>(null) }
            val gestureScope = rememberCoroutineScope()
            // 双击命中：按页面坐标判断，另加 10dp 宽容，小字框也点得中
            val touchPadPx = with(density) { 10.dp.toPx() }
            // 提示文案在组合期取好，双击回调里不能调 @Composable
            val msgMaskOff = T("已取消这处打码", "Mask removed")
            val msgMaskOn = T("已恢复这处打码", "Mask restored")
            val msgUndo = T("已撤销最后一笔擦除", "Last erase undone")
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
                        // 手势约定（和桌面端一致）：
                        //   · 双指捏合 = 放大/缩小；两指一起移动 = 看前后左右
                        //   · 单指长按后拖动 = 画虚线框（放大到 6 倍也能画，框自动落回页面坐标）
                        //   · 单指直接拖也能画框（1 倍时的老习惯不变）
                        //   · 轻点 = 放大查看，双击方框 = 取消/恢复该处打码
                        .pointerInput(page, scaleX, scaleY, boxWpx, boxHpx) {
                            val slop = 10f
                            fun toContent(p: Offset) =
                                Offset((p.x - pan.x) / zoom, (p.y - pan.y) / zoom)
                            fun clampPan() {
                                val c = com.neurotracee.pdfmask.core.PageZoom
                                    .clampPan(zoom, pan.x, pan.y, boxWpx, boxHpx)
                                pan = Offset(c[0], c[1])
                            }
                            awaitEachGesture {
                                val down = awaitFirstDown(requireUnconsumed = false)
                                val t0 = System.currentTimeMillis()
                                var mode = 0          // 0 未定 / 1 缩放或平移 / 2 画框
                                val start = down.position
                                var prevPos = down.position
                                var lastDist = 0f
                                var lastCentroid = Offset.Zero
                                var isTap = true
                                var multi = false
                                // 双指抬起一根后，剩下的那根手指不能拿「捏合前」的旧坐标
                                // 做差，否则会突然平移一大截（用户说的「抽一下」）。
                                var needResync = false

                                while (true) {
                                    val ev = awaitPointerEvent()
                                    val pressed = ev.changes.filter { it.pressed }
                                    if (pressed.isEmpty()) break

                                    if (pressed.size >= 2) {
                                        multi = true
                                        isTap = false
                                        needResync = true
                                        val cx = pressed.map { it.position.x }.average().toFloat()
                                        val cy = pressed.map { it.position.y }.average().toFloat()
                                        val c = Offset(cx, cy)
                                        val d = (pressed[0].position - pressed[1].position).getDistance()
                                        if (mode != 1) {
                                            // 进入缩放：以本帧中心为基准，避免首帧把 pan 拽到 (0,0)
                                            mode = 1
                                            lastDist = d
                                            lastCentroid = c
                                            dragFrom = null
                                            dragTo = null
                                            ev.changes.forEach { it.consume() }
                                            continue
                                        }
                                        // 锚点缩放 + 跟随平移：一次算完，避免重复累加导致画面漂移
                                        val r = com.neurotracee.pdfmask.core.PageZoom.pinch(
                                            zoom, pan.x, pan.y,
                                            lastCentroid.x, lastCentroid.y, c.x, c.y,
                                            lastDist, d, boxWpx, boxHpx
                                        )
                                        zoom = r[0]
                                        pan = Offset(r[1], r[2])
                                        lastDist = d
                                        lastCentroid = c
                                        ev.changes.forEach { it.consume() }
                                        continue
                                    }

                                    val pos = pressed[0].position
                                    if (mode == 0) {
                                        val moved = (pos - start).getDistance()
                                        if (moved > slop) {
                                            // 单指只干一件事：画框。缩放后的移动交给双指，
                                            // 免得想拖动画框时页面先被推走。
                                            isTap = false
                                            mode = 2
                                            dragFrom = toContent(start)
                                            dragTo = toContent(pos)
                                        } else if (System.currentTimeMillis() - t0 > 380L) {
                                            // 长按：不管当前缩放多少，都开始画框
                                            isTap = false
                                            mode = 2
                                            dragFrom = toContent(start)
                                            dragTo = toContent(pos)
                                        }
                                    }
                                    when (mode) {
                                        1 -> {
                                            if (needResync) {
                                                // 刚少了一根手指：本帧只对齐基准、不平移，
                                                // prevPos 由循环末尾统一更新成当前点
                                                needResync = false
                                            } else {
                                                pan = Offset(
                                                    pan.x + (pos.x - prevPos.x),
                                                    pan.y + (pos.y - prevPos.y)
                                                )
                                                clampPan()
                                            }
                                            ev.changes.forEach { it.consume() }
                                        }
                                        2 -> {
                                            dragTo = toContent(pos)
                                            pressed[0].consume()
                                        }
                                    }
                                    prevPos = pos
                                    if (pressed[0].changedToUpIgnoreConsumed()) break
                                }

                                if (mode == 2) {
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
                                            val pr = Rect(l / scaleX, t / scaleY,
                                                          (l + w) / scaleX, (t + h) / scaleY)
                                            if (editMode == 2) vm.addEraser(page, pr)
                                            else vm.addManual(page, pr)
                                        }
                                    }
                                } else {
                                    dragFrom = null
                                    dragTo = null
                                }

                                if (isTap && !multi) {
                                    if (editMode == 2) {
                                        // 橡皮擦模式下轻点 = 撤销上一笔擦除；
                                        // 以前这里没有分支隔开，撤销完还会继续走「打开放大视图」，
                                        // 一次点击同时干了两件事。
                                        if ((vm.erasers[page]?.size ?: 0) > 0) {
                                            vm.undoEraser(page)
                                            vm.toast(msgUndo)
                                        }
                                    } else {
                                        val now = System.currentTimeMillis()
                                        val near = (down.position - lastTapPos).getDistance() < 90f
                                        if (now - lastTapAt < 340L && near) {
                                            // 双击：取消/恢复这一处打码
                                            lastTapAt = 0L
                                            pendingTap?.cancel()
                                            pendingTap = null
                                            val hit = hitTest(toContent(down.position))
                                            if (hit != null) {
                                                val wasOn = hit.id in vm.selected
                                                vm.toggle(hit.id)
                                                vm.toast(if (wasOn) msgMaskOff else msgMaskOn)
                                            }
                                        } else {
                                            lastTapAt = now
                                            lastTapPos = down.position
                                            pendingTap?.cancel()
                                            // 延迟 340ms 再进放大视图，给双击留出判定时间
                                            pendingTap = gestureScope.launch {
                                                delay(340)
                                                onExpand()
                                            }
                                        }
                                    }
                                }
                            }
                        }
                ) {
                    // 缩放/平移只作用于页面内容这一层：手势本身在外层用原始坐标收，
                    // 所以放大到 6 倍画出来的框，坐标依然能准确落回页面。
                    Box(
                        Modifier
                            .fillMaxSize()
                            .graphicsLayer {
                                // 用 this. 前缀：外层有同名的 scaleX/scaleY（页面点→像素比例），
                                // 不加限定符会被外层 val 遮住，报「Val cannot be reassigned」
                                this.scaleX = zoom
                                this.scaleY = zoom
                                this.translationX = pan.x
                                this.translationY = pan.y
                                this.transformOrigin = TransformOrigin(0f, 0f)
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
                            // 橡皮擦与导出共用同一套「打码区域减法」：被擦掉的小块直接从
                            // 打码范围里挖掉，所以预览里看到的就是原图像素本身。
                            // 以前这里是从原图裁一块贴上来，叠划几次就会贴出错位副本，
                            // 看起来像「框选后又复制了一层内容」——现在不可能再出现。
                            val ers = vm.erasers[page].orEmpty()
                            for (f in vm.findings) {
                                if (f.page != page) continue
                                val on = f.id in vm.selected
                                val parts =
                                    if (ers.isEmpty()) listOf(f.rect)
                                    else com.neurotracee.pdfmask.core.MaskRegion.subtract(f.rect, ers)
                                for (r in parts) {
                                    val tl = Offset(r.x0 * sx, r.y0 * sy)
                                    val sz = Size(
                                        (r.width * sx).coerceAtLeast(1f),
                                        (r.height * sy).coerceAtLeast(1f)
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
                            }
                            // 橡皮擦只画一圈淡绿虚线：区域里的内容是页面位图本身，
                            // 不需要（也不允许）再从别处复制像素过来
                            for (r in ers) {
                                if (r.width <= 0f || r.height <= 0f) continue
                                val dx0 = r.x0 * sx
                                val dy0 = r.y0 * sy
                                val dw = (r.width * sx).coerceAtLeast(1f)
                                val dh = (r.height * sy).coerceAtLeast(1f)
                                drawRect(
                                    color = Color(0xCC2FA84F),
                                    topLeft = Offset(dx0, dy0),
                                    size = Size(dw, dh),
                                    style = Stroke(width = 1.dp.toPx(), pathEffect = dash)
                                )
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

                    }

                    // 放大镜：拖拽时在手指上方/右上方实时放大，松手即消失，
                    // 手指压住的那几个字在镜里看得清，落点也就准了；
                    // 正在拉的那条虚线框也一起映射进镜里，边框和手指始终对得上
                    val finger = dragTo?.let { Offset(it.x * zoom + pan.x, it.y * zoom + pan.y) }
                    if (finger != null) {
                        val a0 = dragFrom?.let { Offset(it.x * zoom + pan.x, it.y * zoom + pan.y) }
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
                            } else null,
                            erase = editMode == 2
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
    band: Rect? = null,
    erase: Boolean = false
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
                    color = if (erase) Color(0x332FA84F) else Color(0x332563EB),
                    topLeft = Offset(l, t),
                    size = Size(rr - l, bb - t)
                )
                drawRect(
                    color = if (erase) Color(0xFF2FA84F) else Color(0xFF2563EB),
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
private fun FullPreviewDialog(
    vm: AppViewModel,
    editMode: Int,
    onEditMode: (Int) -> Unit,
    onClose: () -> Unit
) {
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
                // 放大视图里同样能画框 / 擦除：以前这里写死 0，用户在这里拉框永远
                // 只会加手动框，橡皮擦看起来像完全没做——就是那个「点了橡皮擦还在框选」。
                PreviewPane(vm, Modifier.fillMaxSize(), editMode, onExpand = {})
                Row(
                    Modifier
                        .align(Alignment.TopStart)
                        .padding(10.dp),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    ModeChip(
                        on = editMode == 1,
                        label = if (editMode == 1) T("✓ 手动框选", "✓ Box") else T("手动框选", "Box")
                    ) { onEditMode(if (editMode == 1) 0 else 1) }
                    ModeChip(
                        on = editMode == 2,
                        label = if (editMode == 2) T("✓ 橡皮擦", "✓ Erase") else T("橡皮擦", "Erase")
                    ) { onEditMode(if (editMode == 2) 0 else 2) }
                }
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

/** 放大视图顶部的小模式按钮：深色背景上保证看得清 */
@Composable
private fun ModeChip(on: Boolean, label: String, onClick: () -> Unit) {
    TextButton(
        onClick = onClick,
        modifier = Modifier
            .clip(RoundedCornerShape(10.dp))
            .background(if (on) Color(0xFF2563EB) else Color(0x66000000)),
        colors = ButtonDefaults.textButtonColors(contentColor = Color.White)
    ) {
        Text(label, fontSize = 12.sp)
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
