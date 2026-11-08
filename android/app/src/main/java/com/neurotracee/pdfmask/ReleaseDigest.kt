package com.neurotracee.pdfmask

/**
 * 发布正文 → 更新弹窗里的两段文字（v1.4.4）。
 *
 * 发布页正文是我们自己写的 Markdown，格式约定：
 *
 * ```
 * 更新级别：建议
 * > **一句话**：不超过 100 字，只说最关键的那几条
 * ## 1. 修复：xxx（Windows）
 * ## 2. 修复：xxx（安卓）
 * ```
 *
 * 弹窗里先给那句摘要，再把各条目按 Windows / 安卓 归类列出来，末尾写
 * 「具体详见 Release 页面」——详细说明留在发布页，弹窗只当快照。
 *
 * 解析刻意保守：找不到摘要标记就取正文第一段话；连小标题都没有就不给
 * 条目。宁可少显示，也不能把一堆 Markdown 记号糊到用户脸上。
 */
object ReleaseDigest {

    /** 一条更新说明。platform = "both" / "win" / "android" */
    data class Note(val title: String, val platform: String, val lines: List<String>)

    /** 一种语言下的弹窗文案 */
    data class Notes(val brief: String, val items: List<Note>)

    /** 中英各一份，界面按当时选的语言取 */
    data class Digest(val zh: Notes?, val en: Notes?) {
        /** 当前语言那份是空的就退回另一种：发布页只写了中文时，英文界面也别空着 */
        fun pick(en: Boolean): Notes? {
            fun usable(n: Notes?) = n != null && (n.brief.isNotBlank() || n.items.isNotEmpty())
            val first = if (en) this.en else this.zh
            val second = if (en) this.zh else this.en
            return if (usable(first)) first else if (usable(second)) second else null
        }
    }

    const val MAX_BRIEF_ZH = 100      // 用户要求：一行摘要 100 字以内
    const val MAX_BRIEF_EN = 150      // 英文同样长度信息更少，放宽到 150 字符
    private const val MAX_ITEMS = 8
    private const val MAX_ITEM_CHARS = 360

    private val HEAD = Regex("""^(#{1,6})\s+(.*)$""")
    private val FENCE = Regex("""^\s*(`{3,}|~{3,})""")
    private val BRIEF_MARK = Regex(
        "(一句话(?:结论|概括)?|一行概括|摘要|要点|in\\s+one\\s+line|at\\s+a\\s+glance|tl;?dr|summary|highlight)",
        RegexOption.IGNORE_CASE
    )
    private val PLAT_TAIL = Regex("""[（(]\s*([^）)]{0,24}?)\s*[）)]\s*$""")
    private val NAV = Regex("""^\**[^\n]{0,12}\**\s*\|\s*\[""", RegexOption.IGNORE_CASE)
    private val CONFIG = Regex("""^(?:更新级别|更新说明|版本(?:说明)?|update\s*level|version)\s*[：:]""",
        RegexOption.IGNORE_CASE)
    // 只跳过「标题本身就是下载 / 校验 / 目录」的章节。
    // 以前是「标题里出现 download 就跳过」，结果
    // 「Fixed: Android downloads arrived as .apk.zip」这种正经修复条目被整条丢掉。
    private val SKIP_TITLE = Regex(
        "^(?:下载|校验|目录|附件|(?:downloads?|checksums?|contents)\\b)",
        RegexOption.IGNORE_CASE
    )
    private val LIST_MARK = Regex("""^\s*[-*+]\s+""")
    private val QUOTE_MARK = Regex("""^\s*(?:>\s*)+""")

    fun of(body: String?): Digest {
        val (zhText, enText) = splitLang(body ?: "")
        val zh = Notes(brief(zhText, MAX_BRIEF_ZH), items(zhText))
        val en = if (enText.isBlank()) null else Notes(brief(enText, MAX_BRIEF_EN), items(enText))
        return Digest(zh, en)
    }

    // ------------------------------------------------------------ 语言切分

    /** 英文段的起点：第一个「不含汉字、且带 Release Notes」的一级标题 */
    private fun splitLang(body: String): Pair<String, String> {
        val lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        for ((i, ln) in lines.withIndex()) {
            if (!ln.startsWith("# ")) continue
            if (Regex("""[\u4e00-\u9fff]""").containsMatchIn(ln)) continue
            if (Regex("""release\s*notes?|what'?s\s*new""", RegexOption.IGNORE_CASE).containsMatchIn(ln)) {
                return lines.subList(0, i).joinToString("\n") to lines.subList(i, lines.size).joinToString("\n")
            }
        }
        return body to ""
    }

    // ------------------------------------------------------------ 清理记号

    /**
     * 去掉 Markdown 记号。反引号里的内容原样保留——`0512****1234`
     * 这类打码示例要是被吃掉星号，读起来就是错的。
     */
    private fun plain(text: String): String {
        val codes = ArrayList<String>()
        var s = Regex("""`([^`]*)`""").replace(text) { m ->
            codes.add(m.groupValues[1])
            "\u0000${codes.size - 1}\u0000"
        }
        s = Regex("""!\[[^\]]*]\([^)]*\)""").replace(s, "")
        s = Regex("""\[([^\]]+)]\([^)]*\)""").replace(s) { it.groupValues[1] }
        s = QUOTE_MARK.replace(s, "")
        s = Regex("""\*\*(.+?)\*\*""").replace(s) { it.groupValues[1] }
        s = Regex("""__(.+?)__""").replace(s) { it.groupValues[1] }
        s = LIST_MARK.replace(s, "")
        s = Regex("""\u0000(\d+)\u0000""").replace(s) { m ->
            codes.getOrElse(m.groupValues[1].toInt()) { "" }
        }
        return s.trim()
    }

    private fun clip(text: String, limit: Int): String {
        val s = text.trim()
        if (s.length <= limit) return s
        val head = s.substring(0, limit)
        val cut = head.indexOfLast { it in "。！？；.!?;" }
        return if (cut >= limit / 2) head.substring(0, cut + 1)
        else head.substring(0, limit - 1).trimEnd('，', ',', '、', ' ') + "…"
    }

    // ------------------------------------------------------------ 一句话摘要

    private fun brief(section: String, limit: Int): String {
        val lines = section.split("\n")
        for (raw in lines) {
            val s = raw.trim()
            if (s.isEmpty()) continue
            if (s.startsWith("#")) {
                if (s.startsWith("## ")) break   // 已经进到条目区，摘要区结束
                continue                          // 一级标题跳过
            }
            if (NAV.containsMatchIn(s) || CONFIG.containsMatchIn(plain(s))) continue
            val head = s.take(24)
            val m = BRIEF_MARK.find(head) ?: continue
            var cand = s.substring(m.range.last + 1)
            cand = cand.trimStart(' ', '\t', '*', '_', '：', ':', '-', '—', '.', '。')
            cand = plain(cand).trimStart(' ', ':', '：', '-', '—', '.', '。', '*')
            if (cand.length >= 8) return clip(cand, limit)
        }
        // 兜底：第一段正文
        val para = ArrayList<String>()
        var inCode = false
        for (raw in lines) {
            val s = raw.trim()
            if (FENCE.containsMatchIn(s)) { inCode = !inCode; continue }
            if (inCode) continue
            if (s.isEmpty() || s.startsWith("#") || s.startsWith("---") || s.startsWith("|")) {
                if (para.isNotEmpty()) break else continue
            }
            if (s[0] in "-*>|" || NAV.containsMatchIn(s) || CONFIG.containsMatchIn(plain(s))) {
                if (para.isNotEmpty()) break else continue
            }
            para.add(plain(s))
            if (s.endsWith("。") || s.endsWith(".") || s.endsWith("！") ||
                s.endsWith("!") || s.endsWith("？") || s.endsWith("?")
            ) {
                if (para.sumOf { it.length } > 30) break
            }
        }
        val cand = para.filter { it.isNotBlank() }.joinToString(" ")
        return if (cand.length >= 10) clip(cand, limit) else ""
    }

    // ------------------------------------------------------------ 详细条目

    private fun platform(title: String): String {
        val m = PLAT_TAIL.find(title) ?: return ""
        val tag = m.groupValues[1].lowercase()
        val win = tag.contains("windows") || tag.contains("桌面")
        val android = tag.contains("安卓") || tag.contains("android") || tag.contains("手机")
        return when {
            win && android -> "both"
            win -> "win"
            android -> "android"
            else -> ""
        }
    }

    private fun items(section: String): List<Note> {
        val out = ArrayList<Note>()
        var title: String? = null
        var plat = "both"
        var buf = ArrayList<String>()
        var inCode = false

        fun flush() {
            val t = title ?: return
            val body = ArrayList<String>()
            var used = 0
            for (ln in buf) {
                if (ln.isBlank()) continue
                val left = MAX_ITEM_CHARS - used
                if (left <= 20) break
                body.add(if (ln.length <= left) ln else clip(ln, left))
                used += minOf(ln.length, left)
            }
            if (body.isNotEmpty() && out.size < MAX_ITEMS) out.add(Note(t, plat, body))
        }

        for (raw in section.split("\n")) {
            val s = raw.trimEnd()
            if (FENCE.containsMatchIn(s)) { inCode = !inCode; continue }
            val m = HEAD.find(s)
            if (m != null && m.groupValues[1].length <= 3 && !inCode) {
                if (m.groupValues[1].length == 1) continue
                flush()
                var t = plain(m.groupValues[2])
                val p = platform(t)
                if (p.isNotEmpty()) t = PLAT_TAIL.replace(t, "").trim()
                t = Regex("""^\d+\s*[.、)]\s*""").replace(t, "").trim()
                if (t.isEmpty() || SKIP_TITLE.containsMatchIn(t)) {
                    title = null; plat = "both"; buf = ArrayList()
                } else {
                    title = t
                    plat = p.ifEmpty { "both" }
                    buf = ArrayList()
                }
                continue
            }
            if (title == null) continue
            if (s.isBlank() || s.startsWith("---") || s.startsWith("|")) continue
            val line = plain(s)
            if (line.isNotEmpty()) buf.add(line)
        }
        flush()
        return out
    }
}
