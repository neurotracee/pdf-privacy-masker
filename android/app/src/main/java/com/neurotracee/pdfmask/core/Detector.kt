package com.neurotracee.pdfmask.core

import kotlin.math.min

/**
 * 识别引擎：从桌面版 pdfmask.py 逐条移植，规则保持一致。
 *
 * 输入是已经还原成「视觉行」的文字（每行带每个字符的外框），
 * 输出是带页面坐标的命中列表。不依赖 Android，可以直接跑 JVM 单元测试。
 */
object Detector {

    private const val HAN_START = '\u4e00'
    private const val HAN_END = '\u9fa5'
    private const val PUNCT = " :：,，、;；。.|·-—_"
    private const val DATE_BODY = """[0-9]{4}\s*[年\-/\.]\s*[0-9]{1,2}\s*[月\-/\.]\s*[0-9]{1,2}\s*日?"""

    private val RE_DIGIT_RUN = Regex("""[0-9]{11,}""")
    private val RE_BIRTH_ACROSS = Regex("""($DATE_BODY)\s*出?$""")

    private val ADDR_TRIM_PREFIX = listOf(
        "现居住于", "现居住在", "现居于", "现居住", "居住于", "居住地", "住所在",
        "家住", "住在", "居所", "位于", "地址为", "为", "在"
    )

    private val NAME_TAIL_SIMPLE = "省市区县镇乡村街道路号楼层室栋幢园湖山河桥站厂店铺堂馆院校系部处科室"

    fun isHan(c: Char) = c in HAN_START..HAN_END

    // ---------------------------------------------------------------- 校验

    fun id18Ok(s: String): Boolean {
        if (s.length != 18) return false
        val w = intArrayOf(7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        val m = "10X98765432"
        var tot = 0
        for (i in 0 until 17) {
            val d = s[i] - '0'
            if (d < 0 || d > 9) return false
            tot += d * w[i]
        }
        return m[tot % 11] == s[17].uppercaseChar()
    }

    fun idPlausible(s: String): Boolean {
        if (s.length != 18) return false
        for (i in 0 until 17) if (s[i] !in '0'..'9') return false
        val prov = s.substring(0, 2)
        if (prov !in PROVINCES) return false
        val y = s.substring(6, 10).toIntOrNull() ?: return false
        val mo = s.substring(10, 12).toIntOrNull() ?: return false
        val d = s.substring(12, 14).toIntOrNull() ?: return false
        return y in 1900..2026 && mo in 1..12 && d in 1..31
    }

    fun luhnOk(s: String): Boolean {
        if (s.isEmpty()) return false
        var tot = 0
        var alt = false
        for (i in s.indices.reversed()) {
            var d = s[i] - '0'
            if (d < 0 || d > 9) return false
            if (alt) {
                d *= 2
                if (d > 9) d -= 9
            }
            tot += d
            alt = !alt
        }
        return tot % 10 == 0
    }

    fun id15Ok(s: String): Boolean {
        if (s.length != 15) return false
        for (c in s) if (c !in '0'..'9') return false
        if (s.substring(0, 2) !in PROVINCES) return false
        val mo = s.substring(8, 10).toInt()
        val d = s.substring(10, 12).toInt()
        return mo in 1..12 && d in 1..31
    }

    private val PROVINCES = setOf(
        "11", "12", "13", "14", "15", "21", "22", "23", "31", "32", "33",
        "34", "35", "36", "37", "41", "42", "43", "44", "45", "46",
        "50", "51", "52", "53", "54", "61", "62", "63", "64", "65",
        "71", "81", "82", "91"
    )

    fun looksName(word0: String): Boolean {
        val w = word0.trim()
        if (w.length < 2 || w.length > 4) return false
        if (w in T.NAME_STOP) return false
        if (w.any { it in '0'..'9' }) return false
        if (w.length >= 3 && w.substring(0, 2) in T.COMPOUND_SURNAME) return true
        if (w[0] !in T.SURNAME_1) return false
        if (w.last() in NAME_TAIL_SIMPLE) return false
        return true
    }

    // ---------------------------------------------------------------- 主入口

    fun detect(pages: List<PageText>): List<Finding> {
        val findings = mutableListOf<Finding>()
        for (p in pages) {
            for (line in p.lines) {
                findings.addAll(scanLine(line, p.index))
            }
            findings.addAll(scanBirthAcrossLines(p))
            findings.addAll(scanGenderByHeader(p))
        }
        var res = dedupe(findings)
        res = dedupe(spreadConfirmedNames(pages, res))
        val sus = scanNamesSuspect(pages, res)
        if (sus.isNotEmpty()) res = dedupe(res + sus)
        res.forEachIndexed { i, f -> f.id = i }
        return res
    }

    // ---------------------------------------------------------------- 单行

    private fun spanRect(chars: List<CharBox?>, start: Int, end: Int): Rect? {
        var r: Rect? = null
        val e = min(end, chars.size)
        for (i in start until e) {
            if (i < 0) continue
            val c = chars[i]?.rect ?: continue
            r = if (r == null) c else r.union(c)
        }
        return r
    }

    private fun clipValue(text: String, valueStart: Int): Pair<Int, Int> {
        var s = valueStart.coerceIn(0, text.length)
        while (s < text.length && text[s] in " :：·") s++
        val seg = text.substring(s)
        val m = T.RE_ANY_LABEL.find(seg)
        var end = s + (m?.range?.first ?: seg.length)
        for (stop in charArrayOf('。', '；', ';')) {
            val i = text.indexOf(stop, s)
            if (i > s && i < end) {
                end = i
                break
            }
        }
        var i = text.indexOf('，', s)
        while (i in (s + 1) until end) {
            val tail = text.substring(i + 1, end).trimStart()
            if (tail.isNotEmpty() && T.RE_ANY_LABEL.matchAt(tail, 0) != null) {
                end = i
                break
            }
            i = text.indexOf('，', i + 1)
        }
        while (end > s && text[end - 1] in PUNCT) end--
        while (s < end && text[s] in " :：·") s++
        if (s > end) s = end
        return s to end
    }

    private fun trimAddrPrefix(text: String, s0: Int, e: Int): Int {
        var s = s0
        val seg = text.substring(s, e)
        for (pre in ADDR_TRIM_PREFIX) {
            if (seg.startsWith(pre) && (e - s) - pre.length >= 4) return s + pre.length
        }
        for (k in 0 until min(6, e - s)) {
            if (text[s + k] in "在于" && (e - (s + k + 1)) >= 4) return s + k + 1
        }
        return s
    }

    private fun scanLine(line: Line, page: Int): List<Finding> {
        val text = line.text
        val chars = line.chars
        val found = mutableListOf<Finding>()
        val taken = mutableListOf<IntRange>()

        fun add(kind: String, start: Int, end: Int, raw: String? = null, note: String = "") {
            val s = start.coerceIn(0, text.length)
            val e = end.coerceIn(0, text.length)
            if (s >= e) return
            for (r in taken) {
                if (s < r.last + 1 && e > r.first) return
            }
            val rect = spanRect(chars, s, e) ?: return
            if (rect.width < 0.8f && rect.height < 0.8f) return
            taken.add(s until e)
            found.add(Finding(page, kind, raw ?: text.substring(s, e).trim(), rect, note))
        }

        fun addName(s0: Int, e0: Int, cand0: String) {
            var e = e0
            var cand = (cand0).trim()
            while (cand.isNotEmpty() && cand.last() in PUNCT) {
                cand = cand.dropLast(1)
                e--
            }
            if (cand.isEmpty() || cand in T.NAME_STOP || !looksName(cand)) return
            val keep = if (cand.length >= 3 && cand.substring(0, 2) in T.COMPOUND_SURNAME) 2 else 1
            if (cand.length - keep < 1) return
            add(Kind.NAME, s0 + keep, e, cand, "保留姓氏:" + cand.substring(0, keep))
        }

        // 1. 身份证
        for (m in T.RE_ID18.findAll(text)) {
            if (id18Ok(m.value)) add(Kind.IDCARD, m.range.first, m.range.last + 1, m.value)
        }
        for (m in T.RE_ID15.findAll(text)) {
            if (id15Ok(m.value)) add(Kind.IDCARD, m.range.first, m.range.last + 1, m.value)
        }
        for (m in T.RE_ID_LABEL_FB.findAll(text)) {
            val g = m.groups[1] ?: continue
            if (g.value.isEmpty()) continue
            add(Kind.IDCARD, g.range.first, g.range.last + 1, g.value, "标签兜底")
        }

        // 2. 银行卡
        for (m in T.RE_BANK.findAll(text)) {
            val s = m.value
            if (luhnOk(s) && s.toSet().size >= 5) add(Kind.BANKCARD, m.range.first, m.range.last + 1, s)
        }
        for (m in T.RE_BANK_LABEL_FB.findAll(text)) {
            val g = m.groups[1] ?: continue
            if (g.value.isEmpty()) continue
            add(Kind.BANKCARD, g.range.first, g.range.last + 1, g.value, "标签兜底")
        }

        // 3. 手机号
        for (rx in listOf(T.RE_MOBILE, T.RE_MOBILE_SEP)) {
            for (m in rx.findAll(text)) add(Kind.PHONE, m.range.first, m.range.last + 1, m.value)
        }

        // 3.5 长数字串拆分（表格相邻单元格无分隔时会粘成一串）
        for (m in RE_DIGIT_RUN.findAll(text)) {
            val run = m.value
            val base = m.range.first
            val used = BooleanArray(run.length)

            fun free(i: Int, n: Int): Boolean {
                if (i < 0 || i + n > run.length) return false
                for (k in i until i + n) if (used[k]) return false
                return true
            }

            fun take(i: Int, n: Int, kind: String, note: String) {
                for (k in i until i + n) used[k] = true
                add(kind, base + i, base + i + n, run.substring(i, i + n), note)
            }

            for (i in 0..(run.length - 18)) {
                if (i < 0) break
                val seg = run.substring(i, i + 18)
                if (free(i, 18) && id18Ok(seg) && idPlausible(seg)) take(i, 18, Kind.IDCARD, "长串拆分")
            }
            for (n in intArrayOf(19, 18, 17, 16)) {
                for (i in 0..(run.length - n)) {
                    if (i < 0) break
                    val seg = run.substring(i, i + n)
                    if (free(i, n) && luhnOk(seg) && seg.toSet().size >= 5) take(i, n, Kind.BANKCARD, "长串拆分")
                }
            }
            for (i in 0..(run.length - 11)) {
                if (i < 0) break
                val seg = run.substring(i, i + 11)
                if (free(i, 11) && Regex("""1[3-9][0-9]{9}""").matches(seg)) take(i, 11, Kind.PHONE, "长串拆分")
            }
            if (run.length >= 22) {
                for (i in 0..(run.length - 18)) {
                    if (i < 0) break
                    val seg = run.substring(i, i + 18)
                    val yr = seg.substring(6, 10).toIntOrNull()
                    if (free(i, 18) && idPlausible(seg) && yr != null && yr in 1940..2010) {
                        take(i, 18, Kind.IDCARD, "长串拆分·校验位异常")
                    }
                }
            }
            var i = 0
            while (i < run.length) {
                if (used[i]) {
                    i++
                    continue
                }
                var j = i
                while (j < run.length && !used[j]) j++
                if (j - i >= 24) take(i, j - i, Kind.IDCARD, "粘连长串")
                i = j
            }
        }

        // 4. 邮箱
        for (m in T.RE_EMAIL.findAll(text)) add(Kind.EMAIL, m.range.first, m.range.last + 1, m.value)
        if (text.contains(' ') && text.contains('@')) {
            val idx = text.indices.filter { text[it] != ' ' }
            val flat = idx.map { text[it] }.joinToString("")
            for (m in T.RE_EMAIL.findAll(flat)) {
                val s0 = idx[m.range.first]
                val s1 = idx[m.range.last] + 1
                if (s1 - s0 > m.value.length) add(Kind.EMAIL, s0, s1, m.value, "字距还原")
            }
        }

        // 5. 座机
        for (m in T.RE_TEL.findAll(text)) add(Kind.TEL, m.range.first, m.range.last + 1, m.value)
        for (m in T.RE_TEL_LABEL.findAll(text)) {
            val g = m.groups[1] ?: continue
            val v = g.value.trim()
            if (v.matches(Regex("""[0-9\-\s\(\)]{7,20}""")) && v.count { it == '-' } <= 2) {
                add(Kind.TEL, g.range.first, g.range.first + g.value.length, v)
            }
        }

        // 6. 出生日期
        for (m in T.RE_BIRTH_LABEL.findAll(text)) {
            val g = m.groups[1] ?: continue
            if (g.value.isNotEmpty()) add(Kind.BIRTH, g.range.first, g.range.last + 1, g.value.trim(), "标签:出生")
        }
        for (m in T.RE_BIRTH_SUFFIX.findAll(text)) {
            val g = m.groups[1] ?: continue
            if (g.value.isNotEmpty()) add(Kind.BIRTH, g.range.first, g.range.last + 1, g.value.trim(), "后缀:出生")
        }

        // 7. 性别
        for (m in T.RE_GENDER.findAll(text)) {
            val g = m.groups[1] ?: continue
            add(Kind.GENDER, g.range.first, g.range.last + 1, g.value)
        }
        for (pair in listOf(
            T.RE_GENDER_BARE_1 to "逗号夹注",
            T.RE_GENDER_BARE_2 to "逗号夹注",
            T.RE_GENDER_BARE_3 to "出生后夹注"
        )) {
            for (m in pair.first.findAll(text)) {
                val g = m.groups[1] ?: continue
                add(Kind.GENDER, g.range.first, g.range.last + 1, g.value, pair.second)
            }
        }
        if (found.isEmpty()) {
            val t = text.trim()
            if (t.length == 1 && (t == "男" || t == "女")) {
                val i = text.indexOf(t)
                add(Kind.GENDER, i, i + 1, t)
            }
        }

        // 8. 年龄
        for (m in T.RE_AGE.findAll(text)) {
            val g = m.groups[1] ?: continue
            add(Kind.AGE, g.range.first, g.range.last + 1, g.value)
        }
        for (m in T.RE_AGE_2.findAll(text)) {
            val g = m.groups[1] ?: continue
            add(Kind.AGE, g.range.first, g.range.last + 1, g.value)
        }
        for (m in T.RE_AGE_3.findAll(text)) {
            val g = m.groups[1] ?: continue
            val v = g.value.toIntOrNull() ?: continue
            if (v in 1..120) add(Kind.AGE, g.range.first, g.range.last + 1, g.value)
        }

        // 9. 地址
        for (m in T.RE_ADDR_LABEL.findAll(text)) {
            val g = m.groups[1] ?: continue
            val (s0, e0) = clipValue(text, g.range.first)
            val s = trimAddrPrefix(text, s0, e0)
            if (e0 - s >= 4) add(Kind.ADDRESS, s, e0, text.substring(s, e0))
        }
        for (m in T.RE_ADDR_FREE.findAll(text)) {
            val s = trimAddrPrefix(text, m.range.first, m.range.last + 1)
            add(Kind.ADDRESS, s, m.range.last + 1, text.substring(s, m.range.last + 1))
        }

        // 10. 姓名（标签 / 签名 / 自指 / 称谓）
        for (rx in listOf(T.RE_NAME_LABEL, T.RE_NAME_SIGN, T.RE_NAME_SELF)) {
            for (m in rx.findAll(text)) {
                val g = m.groups[1] ?: continue
                if (g.value.isEmpty()) continue
                var (s, e) = clipValue(text, g.range.first)
                var cand = text.substring(s, e)
                if (!looksName(cand.trim())) {
                    s = g.range.first
                    e = g.range.last + 1
                    cand = text.substring(s, e)
                }
                addName(s, e, cand)
            }
        }
        for (m in T.RE_NAME_HONOR.findAll(text)) {
            val g = m.groups[1] ?: continue
            if (g.value.isNotEmpty()) addName(g.range.first, g.range.last + 1, g.value)
        }

        // 11a. 纯叙述文本里的姓名
        for ((s, e, cand) in scanNamesProse(text)) {
            val keep = if (cand.length >= 3 && cand.substring(0, 2) in T.COMPOUND_SURNAME) 2 else 1
            if (cand.length - keep < 1) continue
            add(Kind.NAME, s + keep, e, cand, "叙述·保留姓氏:" + cand.substring(0, keep))
        }
        // 11b. 老规则的动词白名单兜底
        for (m in T.RE_NAME_BARE.findAll(text)) {
            val g = m.groups[1] ?: continue
            val cand = g.value
            if (cand.isEmpty()) continue
            if (cand in T.NAME_STOP || cand in T.COMMON_WORD_STOP) continue
            if (cand.last() in T.NAME_TAIL_BAD) continue
            if (cand.last() in "方性率度值量费价额份项类批次") continue
            addName(g.range.first, g.range.last + 1, cand)
        }

        // 12. 人名枚举
        for (m in T.RE_NAME_LIST.findAll(text)) {
            val g = m.groups[1] ?: continue
            val parts = g.value.split("、").toMutableList()
            if (parts.isEmpty()) continue
            val lastP = parts.last()
            if (lastP.length == 3 && lastP[2] in "个人名位两三四五六七八九十多余") {
                parts[parts.size - 1] = lastP.substring(0, 2)
            }
            val ok = parts.filter { looksName(it) }
            if (ok.size < 2 || ok.size < parts.size) continue
            var pos = g.range.first
            for (p in parts) {
                val idx = text.indexOf(p, pos)
                if (idx >= 0) {
                    addName(idx, idx + p.length, p)
                    pos = idx + p.length
                }
            }
        }

        // 13. 并列人名
        for (m in T.RE_NAME_CONJ.findAll(text)) {
            val a = m.groups[1] ?: continue
            val b = m.groups[2] ?: continue
            if (looksName(a.value) && looksName(b.value)) {
                addName(a.range.first, a.range.last + 1, a.value)
                addName(b.range.first, b.range.last + 1, b.value)
            }
        }

        // 14. 带引入语的人名
        for (m in T.RE_NAME_CTX.findAll(text)) {
            val g = m.groups[1] ?: continue
            val cand = g.value
            if (cand in T.NAME_STOP || !looksName(cand)) continue
            addName(g.range.first, g.range.last + 1, cand)
        }

        return found
    }

    // ---------------------------------------------------------------- 纯段落人名

    private fun scanNamesProse(text: String): List<Triple<Int, Int, String>> {
        val out = mutableListOf<Triple<Int, Int, String>>()
        val n = text.length
        if (n < 2) return out

        fun leftOk(p: Int): Boolean {
            if (p <= 0) return true
            val c = text[p - 1]
            if (!isHan(c)) return true
            if (c in T.LEFT_HARD || c in T.LEFT_SOFT_CHARS) return true
            if (p >= 2 && text.substring(p - 2, p) in T.LEFT_SOFT_WORDS) return true
            return false
        }

        fun rightOk(q: Int): Boolean {
            if (q >= n) return true
            val c = text[q]
            if (!isHan(c)) return true
            return c in T.RIGHT_PRED
        }

        var p = 0
        while (p < n - 1) {
            val ch = text[p]
            if (!isHan(ch) || ch.toString() in T.NAME_STOP) {
                p++
                continue
            }
            val sur = mutableListOf<Int>()
            if (p + 1 < n && text.substring(p, p + 2) in T.COMPOUND_SURNAME) sur.add(2)
            if (ch in T.SURNAME_1) sur.add(1)
            if (sur.isEmpty() || !leftOk(p)) {
                p++
                continue
            }
            var hit: Triple<Int, Int, String>? = null
            outer@ for (k in sur) {
                for (g in intArrayOf(2, 1)) {
                    val q = p + k + g
                    if (q > n) continue
                    val given = text.substring(p + k, q)
                    if (given.isEmpty() || given.any { it !in T.GIVEN_CHARS }) continue
                    if (!rightOk(q)) continue
                    val cand = text.substring(p, q)
                    if (cand in T.NAME_STOP || cand in T.COMMON_WORD_STOP) continue
                    if (cand.last() in T.NAME_TAIL_BAD) continue
                    hit = Triple(p, q, cand)
                    break@outer
                }
            }
            if (hit != null) {
                out.add(hit)
                p = hit.second
            } else {
                p++
            }
        }
        return out
    }

    // ---------------------------------------------------------------- 性别列

    /**
     * 表格里「性别」那一列通常只写一个「男」或「女」，前后都是空白，没有标签也没有逗号。
     * 只要本页出现过「性别」表头，就把页内这种独立成格的男/女都按性别处理。
     * （正文里的「男同学」「女装」不会被波及，因为它们前后不是空白。）
     */
    private fun scanGenderByHeader(page: PageText): List<Finding> {
        if (page.lines.none { it.text.contains("性别") }) return emptyList()
        val out = mutableListOf<Finding>()
        val soft = "，,。、；;：:|｜（）()／/"
        for (line in page.lines) {
            val t = line.text
            for (i in t.indices) {
                val c = t[i]
                if (c != '男' && c != '女') continue
                val prev = if (i > 0) t[i - 1] else ' '
                val next = if (i + 1 < t.length) t[i + 1] else ' '
                val okPrev = prev.isWhitespace() || prev in soft
                val okNext = next.isWhitespace() || next in soft
                if (!okPrev || !okNext) continue
                val r = spanRect(line.chars, i, i + 1) ?: continue
                out.add(Finding(page.index, Kind.GENDER, c.toString(), r, "性别列"))
            }
        }
        return out
    }

    // ---------------------------------------------------------------- 跨行出生

    private fun scanBirthAcrossLines(page: PageText): List<Finding> {
        val out = mutableListOf<Finding>()
        for (i in 0 until page.lines.size - 1) {
            val t1 = page.lines[i].text
            val t2 = page.lines[i + 1].text.trimStart()
            if (!(t2.startsWith("生") || t2.startsWith("出生"))) continue
            val body = t1.trimEnd()
            val m = RE_BIRTH_ACROSS.find(body) ?: continue
            val g = m.groups[1] ?: continue
            if (g.value.isEmpty()) continue
            val r = spanRect(page.lines[i].chars, g.range.first, g.range.last + 1) ?: continue
            out.add(Finding(page.index, Kind.BIRTH, g.value, r, "跨行:出生"))
        }
        return out
    }

    // ---------------------------------------------------------------- 同名扩散

    private fun spreadConfirmedNames(pages: List<PageText>, findings: List<Finding>): List<Finding> {
        val names = LinkedHashSet<String>()
        for (f in findings) {
            if (f.type == Kind.NAME && f.text.isNotEmpty()) names.add(f.text)
        }
        if (names.isEmpty()) return findings
        val extra = mutableListOf<Finding>()
        val soft = "的是了和与跟由对把被让给从在、，。；："
        for (p in pages) {
            for (line in p.lines) {
                val text = line.text
                for (nm in names) {
                    var start = 0
                    while (true) {
                        val i = text.indexOf(nm, start)
                        if (i < 0) break
                        start = i + 1
                        val before = if (i > 0) text[i - 1] else null
                        val after = if (i + nm.length < text.length) text[i + nm.length] else null
                        val leftOk = before == null || !isHan(before) || before in soft
                        val rightOk = after == null || !isHan(after) || after in soft
                        if (!(leftOk || rightOk)) continue
                        val keep = if (nm.length >= 3 && nm.substring(0, 2) in T.COMPOUND_SURNAME) 2 else 1
                        val r = spanRect(line.chars, i + keep, i + nm.length) ?: continue
                        extra.add(
                            Finding(p.index, Kind.NAME, nm, r, "同名扩散:" + nm.substring(0, keep))
                        )
                    }
                }
            }
        }
        return findings + extra
    }

    // ---------------------------------------------------------------- 疑似人名

    private fun scanNamesSuspect(pages: List<PageText>, findings: List<Finding>): List<Finding> {
        val taken = HashSet<String>()
        for (f in findings) if (f.type == Kind.NAME) taken.add(f.text)

        val cand = LinkedHashMap<String, MutableList<Pair<Int, Rect>>>()
        for (p in pages) {
            for (line in p.lines) {
                val text = line.text
                val n = text.length
                var i = 0
                while (i < n - 1) {
                    val ch = text[i]
                    if (!isHan(ch)) {
                        i++
                        continue
                    }
                    if (i > 0) {
                        val prev = text[i - 1]
                        if (isHan(prev) && prev !in T.LEFT_HARD && prev !in T.LEFT_SOFT_CHARS) {
                            i++
                            continue
                        }
                    }
                    var sur = 0
                    if (i + 1 < n && text.substring(i, i + 2) in T.COMPOUND_SURNAME) sur = 2
                    else if (ch in T.SURNAME_1) sur = 1
                    if (sur == 0) {
                        i++
                        continue
                    }
                    var hit: Triple<Int, Int, String>? = null
                    for (g in intArrayOf(2, 1)) {
                        val q = i + sur + g
                        if (q > n) continue
                        val given = text.substring(i + sur, q)
                        if (given.isEmpty() || given.any { it !in T.GIVEN_CHARS }) continue
                        val full = text.substring(i, q)
                        if (full in T.NAME_STOP || full in T.COMMON_WORD_STOP) continue
                        if (full.last() in T.NAME_TAIL_BAD) continue
                        if (full in taken) {
                            hit = Triple(i, q, full)
                            break
                        }
                        if (q < n) {
                            val nxt = text[q]
                            if (isHan(nxt) && (nxt in T.GIVEN_CHARS || nxt in T.RIGHT_PRED)) continue
                        }
                        hit = Triple(i, q, full)
                        break
                    }
                    if (hit != null) {
                        val r = spanRect(line.chars, hit.first + sur, hit.second)
                        if (r != null && r.width * r.height > 0.5f) {
                            cand.getOrPut(hit.third) { mutableListOf() }.add(p.index to r)
                        }
                        i = hit.second
                    } else {
                        i++
                    }
                }
            }
        }

        val out = mutableListOf<Finding>()
        for ((nm, list) in cand) {
            if (list.size < 2 || nm in taken) continue
            val keep = if (nm.length >= 3 && nm.substring(0, 2) in T.COMPOUND_SURNAME) 2 else 1
            if (nm.length - keep < 1) continue
            for ((pno, r) in list) {
                out.add(
                    Finding(
                        pno, Kind.NAME, nm, r,
                        "疑似·保留姓氏:" + nm.substring(0, keep), suspect = true
                    )
                )
            }
        }
        return out
    }

    // ---------------------------------------------------------------- 去重

    private fun dedupe(list: List<Finding>): List<Finding> {
        val prio = HashMap<String, Int>()
        Kind.ORDER.forEachIndexed { i, k -> prio[k] = i }
        val sorted = list.sortedWith(
            compareBy<Finding>({ prio[it.type] ?: 99 }, { -it.rect.area })
        )
        val kept = mutableListOf<Finding>()
        for (f in sorted) {
            var dup = false
            for (k in kept) {
                if (k.page != f.page) continue
                val inter = f.rect.intersect(k.rect) ?: continue
                if (inter.area >= minOf(f.rect.area, k.rect.area) * 0.6f) {
                    dup = true
                    break
                }
            }
            if (!dup) kept.add(f)
        }
        return kept.sortedWith(
            compareBy<Finding>(
                { it.page },
                { Math.round(it.rect.y0 * 10f) },
                { Math.round(it.rect.x0 * 10f) }
            )
        )
    }
}
