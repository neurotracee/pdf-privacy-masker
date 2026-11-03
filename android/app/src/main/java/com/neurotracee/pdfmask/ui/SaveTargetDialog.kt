package com.neurotracee.pdfmask.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.neurotracee.pdfmask.AppPrefs

/**
 * 首次导出时的「保存位置」对话框，对应 Windows 端那张弹窗里的两个勾选：
 * 1. 下次默认使用这个路径
 * 2. 不再询问
 */
@Composable
fun SaveTargetDialog(
    onPickDir: () -> Unit,
    onCancel: () -> Unit,
    onConfirm: () -> Unit
) {
    Dialog(onDismissRequest = onCancel) {
        Surface(shape = RoundedCornerShape(18.dp), color = MaterialTheme.colorScheme.surface) {
            SaveTargetPanel(onPickDir, onCancel, onConfirm)
        }
    }
}

/** 对话框本体（不含外壳，便于单独渲染） */
@Composable
fun SaveTargetPanel(
    onPickDir: () -> Unit,
    onCancel: () -> Unit,
    onConfirm: () -> Unit
) {
    var remember by remember { mutableStateOf(AppPrefs.rememberDir) }
    var noAsk by remember { mutableStateOf(true) }
    val dir = prettyTree(AppPrefs.saveTreeUri)

    Column(Modifier.padding(22.dp).fillMaxWidth()) {
        Text(
            T("选择保存位置", "Where to save"),
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Spacer(Modifier.height(6.dp))
        Text(
            T(
                "打码后的 PDF 会存到这个文件夹，原文件不会被改动。",
                "Masked PDFs go into this folder. The original is never modified."
            ),
            fontSize = 12.5.sp,
            lineHeight = 18.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(14.dp))

        Surface(
            shape = RoundedCornerShape(10.dp),
            color = MaterialTheme.colorScheme.surfaceVariant,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                Modifier.padding(horizontal = 12.dp, vertical = 11.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    dir ?: T("还没选文件夹", "No folder chosen"),
                    fontSize = 13.sp,
                    color = if (dir == null) MaterialTheme.colorScheme.onSurfaceVariant
                    else MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f),
                    maxLines = 1
                )
                Spacer(Modifier.width(8.dp))
                TextButton(onClick = onPickDir) {
                    Text(T("选择文件夹", "Choose"), fontSize = 12.5.sp)
                }
            }
        }

        Spacer(Modifier.height(10.dp))
        CheckLine(
            checked = remember,
            label = T("下次默认使用这个路径", "Use this folder by default next time"),
            sub = T("以后打开就停在这个文件夹", "Next time it opens here"),
            onCheck = { remember = it }
        )
        CheckLine(
            checked = noAsk,
            label = T("不再询问", "Don't ask again"),
            sub = T("以后直接存到这里，不再弹这个窗口", "Save straight here, no more dialogs"),
            onCheck = { noAsk = it }
        )

        Spacer(Modifier.height(10.dp))
        Text(
            T(
                "两个勾选随时能在右上角「设置」里改。都不勾也没关系，下次还会再问一次。",
                "Both can be changed later in Settings. Leave them unchecked and we'll ask again next time."
            ),
            fontSize = 11.sp,
            lineHeight = 16.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(Modifier.height(16.dp))
        Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        Spacer(Modifier.height(12.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            TextButton(onClick = onCancel) {
                Text(T("取消", "Cancel"), fontSize = 13.sp)
            }
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = {
                    AppPrefs.updateRememberDir(remember)
                    AppPrefs.updateNoAsk(noAsk && AppPrefs.saveTreeUri != null)
                    AppPrefs.markAsked()
                    onConfirm()
                },
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text(T("确定", "OK"), fontSize = 13.sp)
            }
        }
    }
}

@Composable
private fun CheckLine(checked: Boolean, label: String, sub: String, onCheck: (Boolean) -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .clickable { onCheck(!checked) }
            .padding(vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Checkbox(
            checked = checked,
            onCheckedChange = { onCheck(it) },
            modifier = Modifier.width(36.dp),
            colors = CheckboxDefaults.colors(
                checkedColor = MaterialTheme.colorScheme.primary,
                uncheckedColor = MaterialTheme.colorScheme.outline
            )
        )
        Spacer(Modifier.width(6.dp))
        Column {
            Text(
                label,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurface
            )
            Text(sub, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
