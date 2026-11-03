package com.neurotracee.pdfmask

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Color as AColor
import android.os.Looper
import android.view.View
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.ComposeView
import androidx.test.core.app.ApplicationProvider
import com.neurotracee.pdfmask.core.CharBox
import com.neurotracee.pdfmask.core.Finding
import com.neurotracee.pdfmask.core.Kind
import com.neurotracee.pdfmask.core.Line
import com.neurotracee.pdfmask.core.PageText
import com.neurotracee.pdfmask.core.Rect
import com.neurotracee.pdfmask.ui.FoldInfo
import com.neurotracee.pdfmask.ui.HomeScreen
import androidx.compose.foundation.shape.RoundedCornerShape
import com.neurotracee.pdfmask.ui.PdfMaskTheme
import com.neurotracee.pdfmask.ui.AboutPanel
import com.neurotracee.pdfmask.ui.SaveTargetPanel
import com.neurotracee.pdfmask.ui.SettingsPanel
import com.neurotracee.pdfmask.ui.WorkScreen
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

/**
 * 界面截图核对：在多种屏幕比例 / 折叠屏形态下渲染首页与工作页，
 * PNG 落到 app/build/ui-shots/ 供人工肉眼核对（不参与 apk 构建）。
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [33])
class UiShotTest {

    private val outDir = File("build/ui-shots").apply { mkdirs() }

    // ---------- 假数据 ----------

    private fun demoPage(index: Int = 0): PageText {
        val texts = listOf(
            "员工信息登记表",
            "姓名：张伟      性别：男      年龄：34",
            "身份证号：320102199003072316",
            "手机号：13812345678",
            "座机：025-83312345",
            "邮箱：zhangwei1990@example.com",
            "银行卡：6222 0202 0000 1234 567",
            "住址：江苏省南京市玄武区中山路100号3栋502室",
            "出生日期：1990年3月7日"
        )
        var y = 90f
        val lines = texts.map { t ->
            val cs = ArrayList<CharBox?>()
            var x = 56f
            for (ch in t) {
                val w = if (ch.code < 128) 6.2f else 13.0f
                cs.add(CharBox(ch, Rect(x, y - 11f, x + w, y + 3f)))
                x += w
            }
            val line = Line(t, cs)
            y += 26f
            line
        }
        return PageText(index, 595f, 842f, lines)
    }

    /** 从伪造的页面文字里取子串的真实外框，保证框选与缩略图严格对齐 */
    private fun boxOf(page: PageText, lineIdx: Int, sub: String): Rect? {
        val line = page.lines.getOrNull(lineIdx) ?: return null
        val at = line.text.indexOf(sub)
        if (at < 0) return null
        var r: Rect? = null
        for (k in at until at + sub.length) {
            val rr = line.chars.getOrNull(k)?.rect ?: continue
            r = r?.union(rr) ?: rr
        }
        return r
    }

    private fun demoFindings(): List<Finding> {
        val pg = demoPage()
        val raw = listOf(
            Triple(Kind.NAME, 1, "张伟"),
            Triple(Kind.GENDER, 1, "男"),
            Triple(Kind.AGE, 1, "34"),
            Triple(Kind.IDCARD, 2, "320102199003072316"),
            Triple(Kind.PHONE, 3, "13812345678"),
            Triple(Kind.TEL, 4, "025-83312345"),
            Triple(Kind.EMAIL, 5, "zhangwei1990@example.com"),
            Triple(Kind.BANKCARD, 6, "6222 0202 0000 1234 567"),
            Triple(Kind.ADDRESS, 7, "江苏省南京市玄武区中山路100号3栋502室"),
            Triple(Kind.BIRTH, 8, "1990年3月7日")
        )
        val auto = raw.mapIndexedNotNull { i, (k, li, t) ->
            val r = boxOf(pg, li, t) ?: return@mapIndexedNotNull null
            Finding(0, k, t, r, note = if (i == 6) "字距还原" else "", suspect = i == 9, id = i)
        }
        // 两条手动框选（负数 id，和 ViewModel 的规则一致）
        val manual1 = Finding(0, Kind.MANUAL, "", Rect(56f, 88f, 300f, 112f), note = "手动框选", id = -1)
        val manual2 = Finding(0, Kind.MANUAL, "", Rect(330f, 300f, 540f, 348f), note = "手动框选", id = -2)
        return auto + manual1 + manual2
    }

    private fun demoThumb(): Bitmap {
        val w = 900
        val h = 1273
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        c.drawColor(AColor.WHITE)
        // 用页面点坐标直接画，保证与 Finding 的 rect 严格对齐
        c.scale(w / 595f, h / 842f)
        val p = Paint().apply {
            color = AColor.rgb(70, 70, 70)
            textSize = 15f
            isAntiAlias = true
        }
        for (line in demoPage().lines) {
            val first = line.chars.firstOrNull { it?.rect != null }?.rect ?: continue
            c.drawText(line.text, first.x0, first.y1 - 3f, p)
        }
        return bmp
    }

    private fun seedVm(): AppViewModel {
        val app = ApplicationProvider.getApplicationContext<android.app.Application>()
        val vm = AppViewModel(app)
        val fs = demoFindings()
        val thumb = demoThumb()
        vm.seedForPreview(
            name = "员工信息登记表.pdf",
            pageTexts = listOf(demoPage(0), demoPage(1)),
            found = fs,
            sel = fs.filter { !it.suspect }.map { it.id }.toSet(),
            thumbBitmaps = mapOf(0 to thumb, 1 to thumb)
        )
        return vm
    }

    // ---------- 渲染 + 落盘 ----------

    private fun render(name: String, dark: Boolean = false, content: @Composable () -> Unit) {
        val activity = Robolectric.buildActivity(ComponentActivity::class.java).setup().get()
        val view = ComposeView(activity)
        activity.setContentView(view)
        view.setContent {
            PdfMaskTheme(dark = dark) { content() }
        }
        val looper = shadowOf(Looper.getMainLooper())
        repeat(8) { looper.idle() }

        val dm = activity.resources.displayMetrics
        val w = dm.widthPixels
        val h = dm.heightPixels
        view.measure(
            View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY)
        )
        view.layout(0, 0, w, h)
        repeat(8) { looper.idle() }

        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)
        canvas.drawColor(AColor.WHITE)
        view.draw(canvas)
        FileOutputStream(File(outDir, "$name.png")).use {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
        println("UI-SHOT $name -> ${w}x${h}px")
    }

    private fun shootApp(
        name: String,
        work: Boolean,
        expanded: Boolean,
        fold: FoldInfo,
        dark: Boolean = false,
        listOpen: Boolean = false,
        testDragAt: androidx.compose.ui.geometry.Offset? = null
    ) {
        val vm = seedVm()
        render(name, dark) {
            Scaffold(
                containerColor = MaterialTheme.colorScheme.background,
                topBar = { AppTopBar(onSettings = {}) }
            ) { pad ->
                Box(Modifier.padding(pad).fillMaxSize()) {
                    if (work) {
                        WorkScreen(
                            vm = vm,
                            expanded = expanded,
                            fold = fold,
                            onPickAnother = {},
                            onGenerate = {},
                            onOpenFile = {},
                            initialListOpen = listOpen,
                            testDragAt = testDragAt
                        )
                    } else {
                        HomeScreen(loading = false, onPick = {}, fold = fold, expanded = expanded)
                    }
                }
            }
        }
    }


    /** 把对话框/面板内容放在圆角卡片里单独渲染 */
    private fun shootPanel(name: String, dark: Boolean = false, content: @Composable () -> Unit) {
        render(name, dark) {
            Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
                Box(Modifier.fillMaxSize().padding(14.dp), contentAlignment = Alignment.Center) {
                    Surface(
                        shape = RoundedCornerShape(18.dp),
                        color = MaterialTheme.colorScheme.surface,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        content()
                    }
                }
            }
        }
    }

    private val noFold = FoldInfo(false, true, 0)

    // ---------- 用例 ----------

    /** 360×800dp 常见手机竖屏 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun home_phone_portrait() = shootApp("01-home-phone-portrait", false, false, noFold)

    /** 320×640dp 小屏手机 */
    @Test
    @Config(qualifiers = "w320dp-h640dp-xhdpi")
    fun home_small_phone() = shootApp("02-home-small-phone", false, false, noFold)

    /** 800×360dp 手机横屏（自动走双栏） */
    @Test
    @Config(qualifiers = "w800dp-h360dp-xxhdpi")
    fun home_phone_landscape() = shootApp("03-home-phone-landscape", false, true, noFold)

    /** 360×800dp 工作页单栏 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun work_phone_portrait() = shootApp("04-work-phone-portrait", true, false, noFold)

    /** 411×914dp 长屏手机 */
    @Test
    @Config(qualifiers = "w411dp-h914dp-xxhdpi")
    fun work_tall_phone() = shootApp("05-work-tall-phone", true, false, noFold)

    /** 640×360dp 手机横屏工作页 */
    @Test
    @Config(qualifiers = "w640dp-h360dp-xxhdpi")
    fun work_phone_landscape() = shootApp("06-work-phone-landscape", true, true, noFold)

    /** 折叠屏折叠态 344×841dp（外屏） */
    @Test
    @Config(qualifiers = "w344dp-h841dp-xhdpi")
    fun work_fold_closed() = shootApp("07-work-fold-closed", true, false, noFold)

    /** 折叠屏展开态 673×841dp，竖直铰链留 24dp */
    @Test
    @Config(qualifiers = "w673dp-h841dp-xhdpi")
    fun work_fold_open() = shootApp(
        "08-work-fold-open", true, true,
        FoldInfo(separating = true, vertical = true, hingeWidthDp = 24)
    )

    /** 折叠屏横置 841×673dp */
    @Test
    @Config(qualifiers = "w841dp-h673dp-xhdpi")
    fun work_fold_open_landscape() = shootApp(
        "09-work-fold-open-landscape", true, true,
        FoldInfo(separating = true, vertical = true, hingeWidthDp = 24)
    )

    /** 折叠屏半折（水平铰链） */
    @Test
    @Config(qualifiers = "w673dp-h420dp-xhdpi")
    fun work_fold_hinge_horizontal() = shootApp(
        "10-work-fold-hinge-horizontal", true, false,
        FoldInfo(separating = true, vertical = false, hingeWidthDp = 20)
    )

    /** 平板 900×1280dp */
    @Test
    @Config(qualifiers = "w900dp-h1280dp-mdpi")
    fun work_tablet() = shootApp("11-work-tablet", true, true, noFold)

    /** 深色主题下的工作页（夜间模式） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-night-xxhdpi")
    fun work_phone_dark() = shootApp("12-work-phone-dark", true, false, noFold, dark = true)

    /** 深色主题下的首页 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-night-xxhdpi")
    fun home_phone_dark() = shootApp("13-home-phone-dark", false, false, noFold, dark = true)

    /** 英文界面（首页） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun home_english() {
        com.neurotracee.pdfmask.AppPrefs.init(
            ApplicationProvider.getApplicationContext<android.app.Application>()
        )
        com.neurotracee.pdfmask.AppPrefs.updateLang("en")
        try {
            shootApp("14-home-english", false, false, noFold)
        } finally {
            com.neurotracee.pdfmask.AppPrefs.updateLang("zh")
        }
    }

    /** 英文界面（处理页，含手动框选） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun work_english() {
        com.neurotracee.pdfmask.AppPrefs.init(
            ApplicationProvider.getApplicationContext<android.app.Application>()
        )
        com.neurotracee.pdfmask.AppPrefs.updateLang("en")
        try {
            shootApp("15-work-english", true, false, noFold)
        } finally {
            com.neurotracee.pdfmask.AppPrefs.updateLang("zh")
        }
    }

    /** 设置面板（中文，浅色） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun settings_panel_zh() = shootPanel("16-settings-zh") {
        SettingsPanel(onClose = {}, onPickSaveDir = {}, onShowAbout = {})
    }

    /** 设置面板（英文） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun settings_panel_en() {
        com.neurotracee.pdfmask.AppPrefs.init(
            ApplicationProvider.getApplicationContext<android.app.Application>()
        )
        com.neurotracee.pdfmask.AppPrefs.updateLang("en")
        try {
            shootPanel("17-settings-en") {
                SettingsPanel(onClose = {}, onPickSaveDir = {}, onShowAbout = {})
            }
        } finally {
            com.neurotracee.pdfmask.AppPrefs.updateLang("zh")
        }
    }

    /** 设置面板（深色） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun settings_panel_dark() = shootPanel("18-settings-dark", dark = true) {
        SettingsPanel(onClose = {}, onPickSaveDir = {}, onShowAbout = {})
    }

    /** 首次导出时的保存位置对话框（两个问题） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun save_target_panel() = shootPanel("19-save-target") {
        SaveTargetPanel(onPickDir = {}, onCancel = {}, onConfirm = {})
    }

    /** 深色主题下的首页 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun home_dark() = shootApp("20-home-dark", false, false, noFold, dark = true)

    /** 新版处理页：折叠态（预览占大屏） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun work_collapsed() = shootApp("30-work-collapsed", true, false, noFold)

    /** 新版处理页：展开识别结果浮层 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun work_list_open() =
        shootApp("31-work-list-open", true, false, noFold, listOpen = true)

    /** 长屏手机折叠态 */
    @Test
    @Config(qualifiers = "w411dp-h914dp-xxhdpi")
    fun work_collapsed_tall() = shootApp("32-work-collapsed-tall", true, false, noFold)

    /** 折叠屏展开态：双栏（列表 34% / 预览 66%） */
    @Test
    @Config(qualifiers = "w673dp-h841dp-xhdpi")
    fun work_fold_open_v2() = shootApp("33-work-fold-open-v2", true, true, noFold)

    /** 深色下的折叠态 */
    @Test
    @Config(qualifiers = "w360dp-h800dp-night-xxhdpi")
    fun work_collapsed_dark() =
        shootApp("34-work-collapsed-dark", true, false, noFold, dark = true)

    /** 关于页（含赞赏码，浅色） */
    @Test
    @Config(qualifiers = "w360dp-h1700dp-xxhdpi")
    fun about_panel() = shootPanel("35-about-zh") { AboutPanel(onClose = {}, maxHeight = 1500.dp) }

    /** 关于页（深色） */
    @Test
    @Config(qualifiers = "w360dp-h1700dp-night-xxhdpi")
    fun about_panel_dark() = shootPanel("36-about-dark", dark = true) { AboutPanel(onClose = {}, maxHeight = 1500.dp) }

    /** 关于页（英文，核对维护文案改写后是否溢出） */
    @Test
    @Config(qualifiers = "w360dp-h1700dp-xxhdpi")
    fun about_panel_english() {
        com.neurotracee.pdfmask.AppPrefs.init(
            ApplicationProvider.getApplicationContext<android.app.Application>()
        )
        com.neurotracee.pdfmask.AppPrefs.updateLang("en")
        try {
            shootPanel("37-about-en") { AboutPanel(onClose = {}, maxHeight = 1500.dp) }
        } finally {
            com.neurotracee.pdfmask.AppPrefs.updateLang("zh")
        }
    }

    /** 拖拽框选中的放大镜（手指在页面中部） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-xxhdpi")
    fun work_loupe_zh() = shootApp(
        "39-loupe-zh", true, false, noFold,
        testDragAt = androidx.compose.ui.geometry.Offset(0.18f, 0.12f)
    )

    /** 放大镜贴边时自动翻到另一侧（手指在右下） */
    @Test
    @Config(qualifiers = "w360dp-h800dp-night-xxhdpi")
    fun work_loupe_corner_dark() = shootApp(
        "40-loupe-corner-dark", true, false, noFold, dark = true,
        testDragAt = androidx.compose.ui.geometry.Offset(0.56f, 0.16f)
    )

    /** 检查更新：有新版（含链接与兜底说明） */
    @Test
    @Config(qualifiers = "w360dp-h1600dp-xxhdpi")
    fun update_card_new_version() = shootPanel("45-update-new") {
        com.neurotracee.pdfmask.ui.UpdateResultCard(
            r = com.neurotracee.pdfmask.Updater.Result(
                ok = true, current = "1.4.0", latest = "1.5.0", hasUpdate = true,
                url = "https://github.com/neurotracee/pdf-privacy-masker/releases/download/v1.5.0/PDFPrivacyMasker-1.5.0-arm64.apk"
            ),
            opened = true, onOpen = {}, onCopy = {}
        )
    }

    /** 检查更新：失败态（错误详情 + 排查清单） */
    @Test
    @Config(qualifiers = "w360dp-h1600dp-xxhdpi")
    fun update_card_failed() = shootPanel("46-update-fail") {
        com.neurotracee.pdfmask.ui.UpdateResultCard(
            r = com.neurotracee.pdfmask.Updater.Result(
                ok = false, current = "1.4.0",
                detail = "连不上 GitHub，可能是网络、代理或安全软件拦住了。\nSocketTimeoutException: timeout",
                url = "https://github.com/neurotracee/pdf-privacy-masker/releases/latest"
            ),
            opened = null, onOpen = {}, onCopy = {}
        )
    }
}
