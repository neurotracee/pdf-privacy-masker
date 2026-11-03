package com.neurotracee.pdfmask.ui

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import com.neurotracee.pdfmask.R
import java.io.IOException

/**
 * 赞赏码保存。
 *
 * API 29+：直接写系统相册 `Pictures/PDFPrivacyMasker`，不需要任何权限。
 * API 26~28：往 MediaStore 写真需要 `WRITE_EXTERNAL_STORAGE`，而本项目坚持不申请存储权限，
 *            所以这两版改走系统「保存到…」选择器，同样零权限。
 */
internal object ThanksQr {
    const val FILE_NAME = "PDFPrivacyMasker-赞赏码.png"
    private const val ALBUM = "PDFPrivacyMasker"
    private const val MIME = "image/png"

    fun canSaveToGallery(): Boolean = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q

    private fun decode(ctx: Context): Bitmap =
        BitmapFactory.decodeResource(ctx.resources, R.drawable.thanks_qr)
            ?: throw IOException("decodeResource returned null")

    private fun compress(src: Bitmap, out: java.io.OutputStream): Boolean =
        src.compress(Bitmap.CompressFormat.PNG, 100, out)

    /** 写入系统相册；返回给人看的路径，失败抛异常由调用方提示 */
    fun saveToGallery(ctx: Context): String {
        val res = ctx.contentResolver
        val pending = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, FILE_NAME)
            put(MediaStore.Images.Media.MIME_TYPE, MIME)
            put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/" + ALBUM)
            put(MediaStore.Images.Media.IS_PENDING, 1)
        }
        val uri = res.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, pending)
            ?: throw IOException("MediaStore insert returned null")
        try {
            res.openOutputStream(uri)?.use { out ->
                if (!compress(decode(ctx), out)) throw IOException("compress returned false")
            } ?: throw IOException("openOutputStream returned null")
        } catch (e: Exception) {
            runCatching { res.delete(uri, null, null) }
            throw e
        }
        runCatching {
            res.update(
                uri,
                ContentValues().apply { put(MediaStore.Images.Media.IS_PENDING, 0) },
                null,
                null
            )
        }
        return "${Environment.DIRECTORY_PICTURES}/$ALBUM/$FILE_NAME"
    }

    /** 用户在选择器里指定的位置写入（API 26~28 用） */
    fun writeTo(ctx: Context, uri: Uri): Boolean = try {
        ctx.contentResolver.openOutputStream(uri)?.use { compress(decode(ctx), it) } ?: false
    } catch (e: Exception) {
        false
    }
}
