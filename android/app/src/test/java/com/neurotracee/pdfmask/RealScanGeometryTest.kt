package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.AlignMap
import com.neurotracee.pdfmask.core.CharLayout
import com.neurotracee.pdfmask.core.Rect
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * 用**真实扫描页**的检测/识别结果，跑产品里的字框几何（[CharLayout] + [AlignMap]），
 * 把算出来的字框写成 boxes.json，交给 `dev/draw_boxes.py` 回放到页面上做逐像素核对。
 *
 * 夹具由 `dev/dump_ocr_fixture.py` 生成（桌面端同一份 PP-OCRv4 模型）。没有夹具时
 * 这个测试自动跳过，不影响正常构建。
 */
@RunWith(RobolectricTestRunner::class)
class RealScanGeometryTest {

    private fun fixtureDir(): File? {
        val candidates = listOf(
            File(System.getenv("PDFMASK_FIXTURE_DIR") ?: ""),
            File("../../dev/fixtures/ocr"),
            File("dev/fixtures/ocr"),
            File("../dev/fixtures/ocr")
        )
        return candidates.firstOrNull { it.isDirectory && it.listFiles()?.any { f -> f.name.endsWith(".json") } == true }
    }

    @Test
    fun boxes_cover_every_detected_line_and_stay_monotonic() {
        val dir = fixtureDir()
        assumeTrue("没有 OCR 夹具，跳过", dir != null)
        val files = dir!!.listFiles { f -> f.name.endsWith(".json") && !f.name.endsWith(".boxes.json") }
            .orEmpty().sortedBy { it.name }
        assumeTrue("没有 OCR 夹具，跳过", files.isNotEmpty())

        for (f in files) {
            val o = JSONObject(f.readText(Charsets.UTF_8))
            val bw = o.getInt("bw")
            val bh = o.getInt("bh")
            val pageW = o.getDouble("pageW").toFloat()
            val pageH = o.getDouble("pageH").toFloat()
            // 夹具里的角度来自桌面端（PIL：逆时针为正）；安卓侧是 Matrix.postRotate
            // （顺时针为正），所以进 AlignMap 之前要取反。两边各自自洽，只是约定相反。
            val skew = -o.getDouble("skew").toFloat()
            val map = AlignMap(bw, bh, skew, pageW, pageH)
            val items = o.getJSONArray("items")
            val out = StringBuilder()
            out.append("{\"tag\":\"").append(o.getString("tag"))
                .append("\",\"pageW\":").append(pageW)
                .append(",\"pageH\":").append(pageH)
                .append(",\"skew\":").append(skew)
                .append(",\"items\":[")

            for (i in 0 until items.length()) {
                val it = items.getJSONObject(i)
                val crop = it.getJSONObject("crop")
                val cw = crop.getInt("w")
                val ch = crop.getInt("h")
                val lum = File(dir, crop.getString("bin")).readBytes().map { it.toInt() and 0xFF }.toIntArray()
                assertEquals("夹具裁图尺寸不符：" + crop.getString("bin"), cw * ch, lum.size)

                val text = it.getString("text")
                val spansJson = it.getJSONArray("spans")
                val spans = (0 until minOf(spansJson.length(), text.length)).map { k ->
                    val s = spansJson.getJSONArray(k)
                    floatArrayOf(s.getDouble(0).toFloat(), s.getDouble(1).toFloat())
                }
                val n = minOf(spans.size, text.length)
                val split = CharLayout.split(
                    lum, cw, ch, text.substring(0, n), spans,
                    it.getDouble("hintTop").toFloat(),
                    it.getDouble("hintBottom").toFloat(),
                    it.getDouble("contentLeft").toFloat(),
                    it.getDouble("contentRight").toFloat()
                )
                val cx0 = it.getInt("cx0")
                val cy0 = it.getInt("cy0")
                val top = (cy0 + split.top).toFloat()
                val bot = (cy0 + split.bottom).toFloat()
                val boxes = ArrayList<Rect>(n)
                for (k in 0 until n) {
                    val r = map.toPage(
                        Rect(cx0 + split.xs[k], top, cx0 + split.xs[k + 1], bot)
                    )
                    boxes.add(r)
                    val where = "「" + text + "」第 ${k} 字 对齐框=" +
                        "[%.2f,%.2f,%.2f,%.2f] 页面框=%s".format(
                            cx0 + split.xs[k], top, cx0 + split.xs[k + 1], bot, r
                        )
                    // 基本不变量：字框必须在页面内，且宽高为正
                    assertTrue("字框越界：$where", r.x0 >= -1f && r.x1 <= pageW + 1f)
                    assertTrue("字框越界：$where", r.y0 >= -1f && r.y1 <= pageH + 1f)
                    assertTrue("字框宽度必须为正：$where", r.x1 > r.x0)
                    assertTrue("字框高度必须为正：$where", r.y1 > r.y0)
                }
                if (i > 0) out.append(',')
                out.append("{\"text\":").append(JSONObject.quote(text))
                    .append(",\"dbg\":{")
                    .append("\"w\":").append(cw).append(",\"h\":").append(ch)
                    .append(",\"top\":").append(split.top).append(",\"bottom\":").append(split.bottom)
                    .append(",\"xs0\":").append(split.xs.first()).append(",\"xsN\":").append(split.xs.last())
                    .append(",\"n\":").append(n)
                    .append(",\"hint\":[").append(it.getDouble("hintTop")).append(',')
                    .append(it.getDouble("hintBottom")).append(']')
                    .append(",\"content\":[").append(it.getDouble("contentLeft")).append(',')
                    .append(it.getDouble("contentRight")).append(']')
                    .append("},\"chars\":[")
                boxes.forEachIndexed { k, r ->
                    if (k > 0) out.append(',')
                    out.append('[')
                        .append((r.x0 * 100).toInt() / 100f).append(',')
                        .append((r.y0 * 100).toInt() / 100f).append(',')
                        .append((r.x1 * 100).toInt() / 100f).append(',')
                        .append((r.y1 * 100).toInt() / 100f).append(']')
                }
                out.append("]}")
            }
            out.append("]}")
            File(dir, o.getString("tag") + ".boxes.json").writeText(out.toString(), Charsets.UTF_8)
        }
    }

    private fun assertEquals(msg: String, a: Int, b: Int) =
        org.junit.Assert.assertEquals(msg, a.toLong(), b.toLong())
}
