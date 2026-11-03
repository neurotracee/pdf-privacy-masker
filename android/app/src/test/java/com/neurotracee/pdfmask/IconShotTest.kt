package com.neurotracee.pdfmask

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Path
import android.graphics.RectF
import androidx.core.content.res.ResourcesCompat
import androidx.test.core.app.ApplicationProvider
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

/**
 * 图标预览：把自适应图标分别按「无遮罩 / 圆形 / 圆角方形 / 小尺寸」渲染出来，
 * 确认主图形都在安全区里，不会被桌面遮罩切掉。
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [33])
class IconShotTest {

    private val outDir = File("build/ui-shots").apply { mkdirs() }

    private fun drawIcon(canvas: Canvas, size: Int, mask: Int) {
        val ctx = ApplicationProvider.getApplicationContext<android.app.Application>()
        val d = ResourcesCompat.getDrawable(ctx.resources, R.mipmap.ic_launcher, null) ?: return
        canvas.save()
        when (mask) {
            1 -> { // 圆形
                val p = Path().apply { addOval(RectF(0f, 0f, size.toFloat(), size.toFloat()), Path.Direction.CW) }
                canvas.clipPath(p)
            }
            2 -> { // 圆角方形（约 22% 圆角，接近多数国产桌面）
                val r = size * 0.22f
                val p = Path().apply {
                    addRoundRect(RectF(0f, 0f, size.toFloat(), size.toFloat()), r, r, Path.Direction.CW)
                }
                canvas.clipPath(p)
            }
        }
        d.setBounds(0, 0, size, size)
        d.draw(canvas)
        canvas.restore()
    }

    private fun shot(name: String, size: Int, mask: Int) {
        val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        c.drawColor(if (mask == 0) Color.TRANSPARENT else Color.rgb(238, 240, 244))
        drawIcon(c, size, mask)
        FileOutputStream(File(outDir, "$name.png")).use {
            bmp.compress(Bitmap.CompressFormat.PNG, 100, it)
        }
    }

    @Test
    @Config(qualifiers = "xxhdpi")
    fun icon_full() = shot("21-icon-full", 432, 0)

    @Test
    @Config(qualifiers = "xxhdpi")
    fun icon_circle() = shot("22-icon-circle", 432, 1)

    @Test
    @Config(qualifiers = "xxhdpi")
    fun icon_rounded() = shot("23-icon-rounded", 432, 2)

    /** 桌面实际显示尺寸附近，检查小尺寸是否还能辨认 */
    @Test
    @Config(qualifiers = "xxhdpi")
    fun icon_small() = shot("24-icon-48dp", 144, 2)
}
