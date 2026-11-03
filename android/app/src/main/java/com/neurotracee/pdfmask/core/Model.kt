package com.neurotracee.pdfmask.core

import kotlin.math.max
import kotlin.math.min

/** 页面坐标系（PDF 点，1/72 英寸），原点在页面左上角 */
data class Rect(val x0: Float, val y0: Float, val x1: Float, val y1: Float) {
    val width: Float get() = x1 - x0
    val height: Float get() = y1 - y0
    val area: Float get() = width * height

    fun union(o: Rect) = Rect(min(x0, o.x0), min(y0, o.y0), max(x1, o.x1), max(y1, o.y1))

    fun intersect(o: Rect): Rect? {
        val ax0 = max(x0, o.x0)
        val ay0 = max(y0, o.y0)
        val ax1 = min(x1, o.x1)
        val ay1 = min(y1, o.y1)
        return if (ax1 <= ax0 || ay1 <= ay0) null else Rect(ax0, ay0, ax1, ay1)
    }

    /** 四周留出余量，保证马赛克盖满字形 */
    fun inflate(dx: Float, dy: Float) = Rect(x0 - dx, y0 - dy, x1 + dx, y1 + dy)
}

/** 一个字符及其外框；rect 为 null 表示"虚拟空格"（版面空隙，不占实际字形） */
data class CharBox(val ch: Char, val rect: Rect?)

/** 一个视觉行 */
data class Line(val text: String, val chars: List<CharBox?>)

/** 一页的文字内容 */
data class PageText(val index: Int, val width: Float, val height: Float, val lines: List<Line>)

/** 识别类型 */
object Kind {
    const val IDCARD = "idcard"
    const val BANKCARD = "bankcard"
    const val PHONE = "phone"
    const val TEL = "tel"
    const val EMAIL = "email"
    const val ADDRESS = "address"
    const val NAME = "name"
    const val BIRTH = "birth"
    const val GENDER = "gender"
    const val AGE = "age"

    /** 手动框选，text 为空，只在 rect 上打码 */
    const val MANUAL = "manual"

    val ORDER = listOf(IDCARD, BANKCARD, PHONE, TEL, EMAIL, ADDRESS, NAME, BIRTH, GENDER, AGE, MANUAL)

    fun labelEn(k: String): String = when (k) {
        IDCARD -> "ID number"
        BANKCARD -> "Bank card"
        PHONE -> "Mobile"
        TEL -> "Landline"
        EMAIL -> "Email"
        ADDRESS -> "Address"
        NAME -> "Name"
        BIRTH -> "Birth date"
        GENDER -> "Gender"
        AGE -> "Age"
        MANUAL -> "Manual"
        else -> k
    }

    fun label(k: String): String = when (k) {
        IDCARD -> "身份证号"
        BANKCARD -> "银行卡号"
        PHONE -> "手机号"
        TEL -> "座机号"
        EMAIL -> "邮箱"
        ADDRESS -> "地址"
        NAME -> "姓名"
        BIRTH -> "出生日期"
        GENDER -> "性别"
        AGE -> "年龄"
        MANUAL -> "手动框选"
        else -> k
    }
}

/** 一条命中 */
data class Finding(
    val page: Int,
    val type: String,
    val text: String,
    val rect: Rect,
    val note: String = "",
    /** 证据不足、默认不打码，只列出来让用户勾选 */
    var suspect: Boolean = false,
    var id: Int = -1
)

/** 打码后的统计 */
data class MaskSummary(
    val pages: Int,
    val count: Int,
    val stats: Map<String, Int>,
    val hitPages: Int
)
