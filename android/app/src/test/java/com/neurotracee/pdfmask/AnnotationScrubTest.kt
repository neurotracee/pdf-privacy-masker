package com.neurotracee.pdfmask

import com.neurotracee.pdfmask.core.Detector
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 注释 / 书签这类没有字形坐标的自由文本，判断里面有没有敏感内容。
 *
 * 安卓打码时会把注释一起渲染进位图，所以只要这里返回 true，就打码会把
 * 该注释的整块矩形盖掉——判断宁可宽一点，也不要把内容漏出去。
 */
class AnnotationScrubTest {

    @Test
    fun structuredNumbersAreSensitive() {
        assertTrue(Detector.looksSensitive("回电 13812346780 即可"))
        assertTrue(Detector.looksSensitive("身份证 320582199207180019"))
        assertTrue(Detector.looksSensitive("邮箱 chenjiahao1992@163.com"))
        assertTrue(Detector.looksSensitive("座机 0512-66881234"))
        assertTrue(Detector.looksSensitive("卡号 4532015112830366"))
        // 卡面那种 4 位一组、空格/短横分隔的印法
        assertTrue(Detector.looksSensitive("卡号 4532 0151 1283 0366"))
        assertTrue(Detector.looksSensitive("卡号 4532-0151-1283-0366"))
    }

    @Test
    fun namesAndAddressesAreSensitive() {
        assertTrue(Detector.looksSensitive("复核：赵子墨"))
        assertTrue(Detector.looksSensitive("复核：赵子墨 江苏省苏州市姑苏区干将东路88号"))
        assertTrue(Detector.looksSensitive("家庭住址：浙江省杭州市西湖区文三路100号"))
    }

    @Test
    fun cleanNotesAreLeftAlone() {
        assertFalse(Detector.looksSensitive("这里排版间距再调一下"))
        assertFalse(Detector.looksSensitive("第二章 正常章节"))
        // 16 位但过不了 Luhn，属于普通编号，不该动
        assertFalse(Detector.looksSensitive("订单号 2026 1112 3344 5566"))
        assertFalse(Detector.looksSensitive(""))
    }
}
