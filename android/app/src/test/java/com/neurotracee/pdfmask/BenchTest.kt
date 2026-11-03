package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.Detector
import org.junit.Test
import java.io.File
import java.util.Locale

/**
 * 基准对照：对测试目录里每个 PDF 跑一遍识别，按 TSV 输出，
 * 再与桌面版输出逐条对比（见 tools/compare.py）。
 */
class BenchTest {

    @Test
    fun dumpAll() {
        val dir = File("C:/Users/YB/PDF隐私打码工具-开源包/test")
        val outDir = File("D:/android-build/jvmtest/kt_out")
        outDir.mkdirs()
        val files = dir.listFiles { f -> f.extension.lowercase() == "pdf" }
            ?.sortedBy { it.name } ?: emptyList()

        val summary = StringBuilder()
        for (f in files) {
            val pages = JvmPdfText.extract(f)
            val findings = Detector.detect(pages)
            val sb = StringBuilder()
            sb.append("###").append(findings.size).append("\n")
            sb.append("page\ttype\ttext\tx0\ty0\tx1\ty1\tnote\tsuspect\n")
            for (x in findings) {
                sb.append(x.page).append('\t')
                sb.append(x.type).append('\t')
                sb.append(x.text).append('\t')
                sb.append(String.format(Locale.US, "%.2f", x.rect.x0)).append('\t')
                sb.append(String.format(Locale.US, "%.2f", x.rect.y0)).append('\t')
                sb.append(String.format(Locale.US, "%.2f", x.rect.x1)).append('\t')
                sb.append(String.format(Locale.US, "%.2f", x.rect.y1)).append('\t')
                sb.append(x.note).append('\t')
                sb.append(if (x.suspect) 1 else 0).append('\n')
            }
            File(outDir, f.name + ".tsv").writeText(sb.toString(), Charsets.UTF_8)
            val lb = StringBuilder()
            for (p in pages) {
                for (line in p.lines) {
                    if (line.text.isBlank()) continue
                    lb.append("[p").append(p.index).append("] ").append(line.text).append('\n')
                }
            }
            File(outDir, f.name + ".lines.txt").writeText(lb.toString(), Charsets.UTF_8)
            summary.append(f.name).append(" -> ").append(findings.size).append(" 条, ")
                .append(pages.sumOf { it.lines.size }).append(" 行\n")
        }
        File(outDir, "_summary.txt").writeText(summary.toString(), Charsets.UTF_8)
        println(summary)
    }
}
