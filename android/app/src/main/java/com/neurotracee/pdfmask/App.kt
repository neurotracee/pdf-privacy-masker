package com.neurotracee.pdfmask

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.DocumentsContract
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContract
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.neurotracee.pdfmask.ui.AppInfoDialog
import com.neurotracee.pdfmask.ui.AutoUpdateGate
import com.neurotracee.pdfmask.ui.HomeScreen
import com.neurotracee.pdfmask.ui.LeaveConfirmDialog
import com.neurotracee.pdfmask.ui.GreenTag
import com.neurotracee.pdfmask.ui.SaveTargetDialog
import com.neurotracee.pdfmask.ui.SettingsDialog
import com.neurotracee.pdfmask.ui.T
import com.neurotracee.pdfmask.ui.WorkScreen
import com.neurotracee.pdfmask.ui.rememberFold
import kotlinx.coroutines.launch

class CreatePdfDocument : ActivityResultContract<Pair<String, Uri?>, Uri?>() {
    override fun createIntent(context: Context, input: Pair<String, Uri?>): Intent {
        val i = Intent(Intent.ACTION_CREATE_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType("application/pdf")
            .putExtra(Intent.EXTRA_TITLE, input.first)
        input.second?.let {
            i.putExtra(DocumentsContract.EXTRA_INITIAL_URI, it)
        }
        return i
    }

    override fun parseResult(resultCode: Int, intent: Intent?): Uri? =
        if (resultCode == Activity.RESULT_OK) intent?.data else null
}

@Composable
fun AppRoot(vm: AppViewModel = viewModel()) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var showSettings by remember { mutableStateOf(false) }
    var showAbout by remember { mutableStateOf(false) }
    var showSaveAsk by remember { mutableStateOf(false) }
    // 手里还有文件时按返回：先问一句，别直接退出应用
    var showLeaveAsk by remember { mutableStateOf(false) }
    // 「保存后离开」：保存成功后再回主页，用这个标记告诉回调该收尾了
    var leaveAfterSave by remember { mutableStateOf(false) }

    /**
     * 真的离开当前文件：正在打码就先中断，然后回主页。
     * 注意是回主页，不是结束进程——用户还能重新选文件，不会一下子被踢出应用。
     */
    fun finishLeaving() {
        leaveAfterSave = false
        showLeaveAsk = false
        scope.launch {
            if (vm.stage == Stage.MASKING) vm.cancelMasking()
            vm.reset()
        }
    }
    val fold = rememberFold()

    val config = LocalConfiguration.current
    val expanded = config.screenWidthDp >= 600

    val picker = rememberLauncherForActivityResult(ActivityResultContractsOpenPdf()) { uri ->
        if (uri != null) vm.load(uri)
    }

    // 选目录：拿持久授权，之后就能免弹窗直接存
    val dirPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { tree ->
        if (tree != null) {
            runCatching {
                ctx.contentResolver.takePersistableUriPermission(
                    tree,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
            }
            AppPrefs.updateSaveDir(tree.toString())
        }
    }

    fun savedMsg(name: String) {
        scope.launch { snackbar.showSnackbar(tr("已保存：", "Saved: ") + name) }
    }

    val saver = rememberLauncherForActivityResult(CreatePdfDocument()) { uri ->
        if (uri == null) {
            // 用户取消了另存：顺手清掉「保存后离开」的意图，免得下次保存时突然离开
            leaveAfterSave = false
            vm.cancelMasking()
        } else {
            vm.writeTo(uri) { name ->
                savedMsg(name)
                if (leaveAfterSave) finishLeaving()
            }
        }
    }

    fun saveToDefaultDir() {
        val u = AppPrefs.saveTreeUri?.let { runCatching { Uri.parse(it) }.getOrNull() }
        if (u == null) {
            saver.launch(vm.suggestOutName() to null)
        } else {
            vm.saveToTree(u) { name ->
                savedMsg(name)
                if (leaveAfterSave) finishLeaving()
            }
        }
    }

    fun startSave() {
        when {
            AppPrefs.noAsk && AppPrefs.saveTreeUri != null -> saveToDefaultDir()
            !AppPrefs.askedSaveOnce -> showSaveAsk = true
            else -> saver.launch(vm.suggestOutName() to null)
        }
    }

    LaunchedEffect(vm) {
        ViewModelHolder.pending = { uri -> vm.load(uri) }
    }

    LaunchedEffect(vm.message) {
        vm.message?.let {
            snackbar.showSnackbar(it)
            vm.clearMessage()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            AppTopBar(onSettings = { showSettings = true })
        }
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            when (vm.stage) {
                Stage.HOME, Stage.LOADING -> HomeScreen(
                    loading = vm.stage == Stage.LOADING,
                    onPick = { picker.launch(arrayOf("application/pdf")) },
                    fold = fold,
                    expanded = expanded
                )

                else -> WorkScreen(
                    vm = vm,
                    expanded = expanded,
                    fold = fold,
                    onPickAnother = { vm.reset() },
                    onGenerate = { startSave() },
                    onOpenFile = { name -> savedMsg(name) }
                )
            }
        }
    }

    if (showSettings) {
        SettingsDialog(
            onClose = { showSettings = false },
            onPickSaveDir = { dirPicker.launch(null) },
            onShowAbout = {
                showSettings = false
                showAbout = true
            }
        )
    }

    if (showAbout) {
        AppInfoDialog(onClose = { showAbout = false })
    }

    // 手里有文件时，返回（含全面屏手势左右滑）先问一句：
    // 继续编辑 / 保存后离开 / 直接离开。以前这里没人接，系统直接退出应用，
    // 用户刚框好、刚打完还没存的东西全丢。
    BackHandler(enabled = vm.stage != Stage.HOME) {
        showLeaveAsk = true
    }

    if (showLeaveAsk) {
        LeaveConfirmDialog(
            stage = vm.stage,
            onStay = { showLeaveAsk = false },
            onSaveAndLeave = if (vm.stage == Stage.DONE) {
                {
                    leaveAfterSave = true
                    showLeaveAsk = false
                    startSave()
                }
            } else null,
            onLeave = { finishLeaving() }
        )
    }

    // 启动先自动查一次版本：断网静默跳过，慢的话给一个能关掉的提示
    AutoUpdateGate()

    if (showSaveAsk) {
        SaveTargetDialog(
            onPickDir = { dirPicker.launch(null) },
            onCancel = {
                showSaveAsk = false
                leaveAfterSave = false
            },
            onConfirm = {
                showSaveAsk = false
                if (AppPrefs.saveTreeUri != null) saveToDefaultDir()
                else saver.launch(vm.suggestOutName() to null)
            }
        )
    }
}

@Composable
internal fun AppTopBar(onSettings: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.background)
            // 关键：给状态栏让出高度，否则标题会被时间/信号图标压住
            .windowInsetsPadding(WindowInsets.statusBars)
            .padding(start = 16.dp, end = 6.dp, top = 8.dp, bottom = 8.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = T("PDF 隐私打码", "PDF Privacy Masker"),
                fontSize = 19.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(Modifier.width(7.dp))
            GreenTag(T("支持扫描件", "Scans OK"))
            Spacer(Modifier.weight(1f))
            IconButton(
                onClick = onSettings,
                modifier = Modifier.size(46.dp)
            ) {
                Icon(
                    Icons.Filled.Settings,
                    contentDescription = T("设置", "Settings"),
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(22.dp)
                )
            }
        }
        Text(
            text = T(
                "真马赛克 · 全程本地零上传 · 扫描件自动识别",
                "Real mosaic · 100% on-device · scans read locally"
            ),
            fontSize = 11.5.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 2.dp, bottom = 2.dp)
        )
    }
}

/** 打开 PDF：只接受 application/pdf，只拿单个文件的临时读权限 */
class ActivityResultContractsOpenPdf : ActivityResultContract<Array<String>, Uri?>() {
    override fun createIntent(context: Context, input: Array<String>): Intent =
        Intent(Intent.ACTION_OPEN_DOCUMENT)
            .addCategory(Intent.CATEGORY_OPENABLE)
            .setType("application/pdf")
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

    override fun parseResult(resultCode: Int, intent: Intent?): Uri? =
        if (resultCode == Activity.RESULT_OK) intent?.data else null
}
