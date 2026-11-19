package com.neurotracee.pdfmask.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.neurotracee.pdfmask.Stage

/**
 * 手里还有没处理完的文件时，按返回（含全面屏手势左右滑）先问一句，而不是直接退出应用。
 *
 * 之前这里是个坑：WorkScreen 没有 [androidx.activity.compose.BackHandler]，系统返回
 * 直接走了 Activity 默认行为 —— 应用被关掉，用户刚框选好、刚打完码但还没保存的东西
 * 全没了，而且没有任何挽回的机会。
 *
 * 四个出口，按「用户此刻最可能想要什么」排序：
 * - 继续编辑（主按钮，默认安全）；
 * - 保存后离开（只有已经有打码结果时才给，存完再回主页）；
 * - 临时保存（把这份 PDF 和当前的框/擦除/勾选存成草稿，首页能接着编辑）；
 * - 直接离开（回主页，不是杀进程 —— 回到主页还能重新选文件）。
 */
@Composable
internal fun LeaveConfirmDialog(
    stage: Stage,
    onStay: () -> Unit,
    onSaveAndLeave: (() -> Unit)?,
    onSaveDraft: (() -> Unit)?,
    onLeave: () -> Unit
) {
    Dialog(
        onDismissRequest = onStay,
        properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = true)
    ) {
        LeaveConfirmContent(stage, onStay, onSaveAndLeave, onSaveDraft, onLeave)
    }
}

/**
 * 对话框里的内容单独抽出来。
 *
 * 两个原因：一是 [Dialog] 是独立的窗口，截图测试抓不到里面的东西，抽出来才能
 * 在窄屏上核对四个按钮挤不挤；二是以后想在别处复用它（比如首页的草稿卡片点
 * 「继续编辑」发现文件被删了）不用再抄一遍。
 */
@Composable
internal fun LeaveConfirmContent(
    stage: Stage,
    onStay: () -> Unit,
    onSaveAndLeave: (() -> Unit)?,
    onSaveDraft: (() -> Unit)?,
    onLeave: () -> Unit
) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            Column(Modifier.padding(22.dp)) {
                Text(
                    T("要离开这个文件吗？", "Leave this file?"),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    when (stage) {
                        Stage.DONE -> T(
                            "打码结果还没保存。现在离开的话，这份结果就没了，得重新处理一遍。",
                            "The masked file has not been saved yet. If you leave now it is gone and you " +
                                "will have to run it again."
                        )
                        Stage.MASKING -> T(
                            "正在生成打码文件，现在离开会中断这次处理。",
                            "The masked file is being generated — leaving now interrupts it."
                        )
                        else -> T(
                            "这份 PDF 已经读进来了，但还没生成打码结果。离开后需要重新选择文件。",
                            "This PDF is loaded but no masked file has been produced yet. You would have to " +
                                "pick the file again."
                        )
                    },
                    fontSize = 12.5.sp,
                    lineHeight = 20.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(Modifier.height(18.dp))
                // 四个出口挤一行的话，360dp 屏上主按钮会被压成竖排单字（试过，
                // 截图里「继续编辑」四个字竖着摞起来）。主按钮独占一行，其余
                // 次要操作放到下面一行，谁的优先级一眼看得出来。
                Button(
                    onClick = onStay,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Text(T("继续编辑", "Keep editing"), fontSize = 14.sp)
                }
                Spacer(Modifier.height(10.dp))
                // 等分三份 + 单行不折行：英文按钮比中文长得多，按内容宽度排会
                // 把最后一个压成两行（「Save &」/「leave」），等分反而稳定。
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = onLeave, modifier = Modifier.weight(1f), contentPadding = PaddingValues(horizontal = 2.dp)) {
                        Text(
                            T("直接离开", "Leave anyway"),
                            fontSize = 11.sp, maxLines = 1, softWrap = false,
                            textAlign = TextAlign.Center
                        )
                    }
                    if (onSaveDraft != null) {
                        TextButton(onClick = onSaveDraft, modifier = Modifier.weight(1f), contentPadding = PaddingValues(horizontal = 2.dp)) {
                            Text(
                                T("临时保存", "Save for later"),
                                fontSize = 11.sp, maxLines = 1, softWrap = false,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                    if (onSaveAndLeave != null) {
                        TextButton(onClick = onSaveAndLeave, modifier = Modifier.weight(1f), contentPadding = PaddingValues(horizontal = 2.dp)) {
                            Text(
                                T("保存后离开", "Save & leave"),
                                fontSize = 11.sp, maxLines = 1, softWrap = false,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
                if (onSaveDraft != null) {
                    Spacer(Modifier.height(2.dp))
                    Text(
                        T(
                            "临时保存会把当前的框选、擦除和勾选留着，下次打开在首页接着编辑。",
                            "Save for later keeps your boxes, erasures and unticked items, so you can pick up " +
                                "where you left off from the home screen."
                        ),
                        fontSize = 11.sp,
                        lineHeight = 17.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
}
