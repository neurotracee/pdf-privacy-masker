package com.neurotracee.pdfmask

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * 应用内更新的缓存目录清理：下载中断 / 主动取消 / 校验失败都不该把残包
 * 越堆越多。核心保证是「固定文件名 + 每次下载开头 clean + 失败路径删 part」，
 * 这里用 Robolectric 的真实 cacheDir 验证清理行为（不发网络请求）。
 */
@RunWith(RobolectricTestRunner::class)
class UpdateApkCacheTest {

    private lateinit var ctx: Context

    @Before
    fun setUp() {
        ctx = ApplicationProvider.getApplicationContext()
        UpdateApk.clean(ctx)          // 每个用例前清空，避免互相干扰
    }

    /** 模拟 100 次中断：无论写多少次，目录里始终只有一个固定名字的 part */
    @Test
    fun repeated_interrupts_leave_a_single_part() {
        repeat(100) { i ->
            UpdateApk.clean(ctx)      // 每次下载开头都会先清
            val part = File(UpdateApk.dir(ctx), "download.part")
            part.writeBytes(ByteArray((i + 1) * 1024))   // 假装下到一半
            assertTrue(part.exists())
        }
        val files = UpdateApk.dir(ctx).listFiles()!!
        assertEquals(1, files.size)
        assertEquals("download.part", files.first().name)
    }

    /** clean 不带 keep：把 part 和旧的正式包都删掉 */
    @Test
    fun clean_removes_part_and_stale_apk() {
        val d = UpdateApk.dir(ctx)
        File(d, "download.part").writeBytes(ByteArray(2048))
        File(d, "PDFPrivacyMasker-1.4.7.0.apk").writeBytes(ByteArray(4096))
        assertEquals(2, d.listFiles()!!.size)

        UpdateApk.clean(ctx)
        assertEquals(0, d.listFiles()!!.size)
        assertFalse(File(d, "download.part").exists())
        assertFalse(File(d, "PDFPrivacyMasker-1.4.7.0.apk").exists())
    }

    /** 已下好、只差权限那一步的正式包要能保留，供「继续安装」用 */
    @Test
    fun clean_keeps_the_downloaded_apk_when_asked() {
        val d = UpdateApk.dir(ctx)
        File(d, "download.part").writeBytes(ByteArray(1024))
        val good = File(d, "PDFPrivacyMasker-1.4.7.2.apk")
        good.writeBytes(ByteArray(8192))

        UpdateApk.clean(ctx, keep = good)
        val left = d.listFiles()!!
        assertEquals(1, left.size)
        assertEquals(good.canonicalPath, left.first().canonicalPath)
        assertTrue(good.exists())
    }

    /** 目录本身要能自动建出来（首次更新时还不存在） */
    @Test
    fun dir_is_created_on_demand() {
        UpdateApk.clean(ctx)
        val d = UpdateApk.dir(ctx)
        assertTrue(d.exists())
        assertTrue(d.isDirectory)
    }
}
