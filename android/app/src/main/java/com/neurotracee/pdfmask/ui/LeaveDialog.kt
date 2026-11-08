package com.neurotracee.pdfmask.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
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
 * 三个出口，按「用户此刻最可能想要什么」排序：
 * - 继续编辑（主按钮，默认安全）；
 * - 保存后离开（只有已经有打码结果时才给，存完再回主页）；
 * - 直接离开（回主页，不是杀进程 —— 回到主页还能重新选文件）。
 */
@Composable
internal fun LeaveConfirmDialog(
    stage: Stage,
    onStay: () -> Unit,
    onSaveAndLeave: (() -> Unit)?,
    onLeave: () -> Unit
) {
    Dialog(
        onDismissRequest = onStay,
        properties = DialogProperties(dismissOnBackPress = true, dismissOnClickOutside = true)
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

                Spacer(Modifier.height(16.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onLeave) {
                        Text(T("直接离开", "Leave anyway"), fontSize = 12.5.sp)
                    }
                    if (onSaveAndLeave != null) {
                        TextButton(onClick = onSaveAndLeave) {
                            Text(T("保存后离开", "Save, then leave"), fontSize = 12.5.sp)
                        }
                    }
                    Spacer(Modifier.padding(horizontal = 3.dp))
                    Button(
                        onClick = onStay,
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text(T("继续编辑", "Keep editing"), fontSize = 13.sp)
                    }
                }
            }
        }
    }
}
