package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.Detector
import com.neurotracee.pdfmask.core.Kind
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import java.io.File

/**
 * 跨端一致性测试：同一份 PDF，Python 端和 Kotlin 端必须识别出**同一批**隐私。
 *
 * Python 端是权威基准（`test/rules_golden.json`，由 dev/gen_rules_golden.py 生成）。
 * 只比对 page / type / text 三元组——坐标系的 y 轴方向两端不同，比坐标没有意义。
 *
 * 这条测试的意义：改规则时只要一端的正则或阈值动了、另一端没跟上，
 * 这里立刻变红，不会等到用户在两台设备上看到不同结果才发现。
 */
@RunWith(RobolectricTestRunner::class)
class RuleParityTest {

    private fun repoFile(rel: String): File {
        var dir: File? = File("").absoluteFile
        while (dir != null) {
            val f = File(dir, rel)
            if (f.exists()) return f
            dir = dir.parentFile
        }
        throw AssertionError("从 ${File("").absolutePath} 向上找不到 $rel")
    }

    @Test
    fun kotlin_detector_matches_python_golden() {
        val pdf = repoFile("test/测试文档_含隐私.pdf")
        val goldenFile = repoFile("test/rules_golden.json")

        val golden = JSONObject(goldenFile.readText(Charsets.UTF_8))
        val want = ArrayList<String>()
        val arr = golden.getJSONArray("findings")
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            want.add(key(o.getInt("page"), o.getString("type"), o.getString("text").trim()))
        }

        val pages = JvmPdfText.extract(pdf)
        val got = Detector.detect(pages)
            .filter { it.type != Kind.MANUAL }
            .map { key(it.page, it.type, it.text.trim()) }

        val onlyPy = want.toSet() - got.toSet()
        val onlyKt = got.toSet() - want.toSet()
        val msg = buildString {
            append("两端识别结果不一致（基准 ${want.size} 条 / 安卓 ${got.size} 条）\n")
            if (onlyPy.isNotEmpty()) append("只有 Python 认出:\n  " + onlyPy.joinToString("\n  ") + "\n")
            if (onlyKt.isNotEmpty()) append("只有 Kotlin 认出:\n  " + onlyKt.joinToString("\n  ") + "\n")
            append("规则改了的话，跑 python dev/gen_rules_golden.py 重新生成基准，并让两端逻辑对齐。")
        }
        assertEquals(msg, want.sorted(), got.sorted())
    }

    private fun key(page: Int, type: String, text: String) = "$page|$type|$text"
}
