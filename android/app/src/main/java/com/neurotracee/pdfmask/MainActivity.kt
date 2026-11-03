package com.neurotracee.pdfmask

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Modifier
import com.neurotracee.pdfmask.ui.PdfMaskTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        // 偏好要在任何 Compose 之前就绪：语言、主题、保存目录都从这里读
        AppPrefs.init(applicationContext)
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val incoming = extractPdfUri(intent)
        setContent {
            PdfMaskTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppRoot()
                }
            }
        }
        if (incoming != null) {
            window.decorView.post {
                // 由别的应用「打开方式 / 分享」进来时，直接载入
                val vmHolder = ViewModelHolder
                vmHolder.pending?.invoke(incoming)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        extractPdfUri(intent)?.let { uri ->
            ViewModelHolder.pending?.invoke(uri)
        }
    }

    private fun extractPdfUri(intent: Intent?): android.net.Uri? {
        intent ?: return null
        return when (intent.action) {
            Intent.ACTION_VIEW -> intent.data
            Intent.ACTION_SEND -> intent.getParcelableExtra(Intent.EXTRA_STREAM)
            else -> null
        }
    }
}

/** 让 Activity 收到的外部文件能交给当前 ViewModel 处理 */
object ViewModelHolder {
    var pending: ((android.net.Uri) -> Unit)? = null
}
