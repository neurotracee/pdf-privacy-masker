package com.neurotracee.pdfmask.ui

import com.neurotracee.pdfmask.core.Kind
import com.neurotracee.pdfmask.tr

/** 列表里显示用：把值遮一部分，避免在界面上把完整敏感信息再露一遍 */
fun maskPreview(kind: String, value0: String): String {
    val s = value0.trim()
    return when (kind) {
        Kind.PHONE -> if (s.length >= 7) s.substring(0, 3) + "****" + s.substring(s.length - 4) else s
        Kind.TEL -> if (s.length >= 9) s.substring(0, 4) + "****" + s.substring(s.length - 4) else s
        Kind.IDCARD -> if (s.length > 8) s.substring(0, 4) + "*".repeat(s.length - 8) + s.substring(s.length - 4) else "*".repeat(s.length)
        Kind.BANKCARD -> if (s.length >= 10) s.substring(0, 4) + " **** **** " + s.substring(s.length - 4) else "*".repeat(s.length)
        Kind.EMAIL -> {
            val at = s.indexOf('@')
            if (at > 2) s.substring(0, 2) + "***" + s.substring(at) else s
        }
        Kind.NAME -> if (s.length >= 2) s[0] + "*".repeat(s.length - 1) else s
        Kind.ADDRESS -> if (s.length > 6) s.substring(0, 6) +
            tr("……（共 ${s.length} 字）", "… (${s.length} chars)") else s
        Kind.BIRTH -> if (s.length >= 4) s.substring(0, 4) +
            tr("年**月**日", "-**-**") else s
        else -> s
    }
}
