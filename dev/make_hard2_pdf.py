# -*- coding: utf-8 -*-
"""刁难文档 2.0：一整段自由叙述，全程没有任何字段标签。
隐私信息与大量无关干扰信息（会议、金额、编号、气象、车牌、快递单）混排。
用来检验检测引擎在「完全不像表单」的文本上到底能认出多少。"""

import os
import pymupdf

from _testpaths import out
OUT = out("刁难文档2_纯段落.pdf")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ---- 虚构人物（身份证校验位、银行卡 Luhn 都是真实有效的） ----
NAME = "苏若彤"
PHONE = "13905178822"
PHONE2 = "15862203377"
MAIL = "suruotong.88@163.com"
MAIL2 = "srt@huayu-tech.com"
ADDR = "江苏省南京市鼓楼区中山北路189号华侨大厦2栋1108室"
ADDR2 = "安徽省芜湖市镜湖区北京东路56号3单元402室"
BIRTH = "1993年11月26日"
IDC = "320106199311260176"
BANK = "6222021002109988779"
BANK2 = "6217001209876543216"
TEL = "025-83651234"
AGE = "33"

TEXT = (
    "上午九点刚过，苏若彤拎着两个纸箱从A区3号楼过来，说这批样品是城南仓库调的，一共15箱，"
    "跑了2.5公里，比原计划晚了四十分钟。会议室空调显示36.5度。"
    "她一边擦汗一边掏手机拨了13905178822，末了补一句，有问题发我邮箱suruotong.88@163.com，"
    "这两天都在，急的话工作邮箱srt@huayu-tech.com也能收，备用号15862203377平时不开机别打。"
    "12800元的采购款还没报下来，还有3.6万尾款卡在审批。"
    "下午的会从两点开到五点十七分，讨论HT-2026-0315这份合同的执行细节，"
    "签署日期定在2026年3月5日，下次复核放在2027年4月11日。"
    "散会时她提起住处，说现住在江苏省南京市鼓楼区中山北路189号华侨大厦2栋1108室，"
    "通勤换两次地铁，早上六点四十就出门，老家在安徽省芜湖市镜湖区北京东路56号3单元402室。"
    "她1993年11月26日出生在南京，今年33岁，来公司快六年，换过三个岗位。"
    "人事催她补材料，让把那张320106199311260176复印一份交上去，"
    "工资卡6222021002109988779的开户行也要填，常用的那张6217001209876543216一起报，"
    "前台座机025-83651234找小王就行，客服热线800-820-8820是外包的不用管。"
    "快递单号SF1234567890123和车牌苏A·D2F83她记在白板角落。"
)

# ---- 隐私真值（用于对比测试） ----
TRUTH = [
    ("姓名", NAME),
    ("手机号", PHONE),
    ("手机号", PHONE2),
    ("邮箱", MAIL),
    ("邮箱", MAIL2),
    ("地址", ADDR),
    ("地址", ADDR2),
    ("出生日期", BIRTH),
    ("身份证号", IDC),
    ("银行卡号", BANK),
    ("银行卡号", BANK2),
    ("座机号", TEL),
    ("年龄", AGE),
]

# ---- 干扰真值（绝对不该被打码） ----
NOISE = [
    "A区3号楼", "15箱", "2.5公里", "四十分钟", "36.5度",
    "12800元", "3.6万", "五点十七分", "HT-2026-0315",
    "2026年3月5日", "2027年4月11日", "两次", "六点四十", "六年", "三个岗位",
    "800-820-8820", "SF1234567890123", "苏A·D2F83", "小王",
]


def wrap(text, protect, width=38):
    """手动按字数折行，且绝不切断号码/邮箱/地址这类不可分割的片段"""
    spans = []
    for p in protect:
        s = 0
        while True:
            j = text.find(p, s)
            if j < 0:
                break
            spans.append((j, j + len(p)))
            s = j + 1
    lines, i = [], 0
    while i < len(text):
        end = min(i + width, len(text))
        changed = True
        while changed and end < len(text):
            changed = False
            for (a, b) in spans:
                if a < end < b:
                    end = a
                    changed = True
        if end <= i:
            end = min(i + width, len(text))
        lines.append(text[i:end])
        i = end
    return lines


def privacy_ratio(text):
    body = "".join(ch for ch in text if not ch.isspace())
    hit = 0
    for _, v in TRUTH:
        hit += len([c for c in v if not c.isspace()])
    return hit, len(body), hit / len(body)


def main():
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    F = "china-s"

    page.insert_text((50, 55), "差旅与项目跟进记录", fontname=F, fontsize=15)
    page.insert_text((50, 78), "（本页为一份随手写的记录，没有任何字段名称）", fontname=F, fontsize=9)

    prot = [v for _, v in TRUTH]
    y = 108
    for ln in wrap(TEXT, prot):
        page.insert_text((50, y), ln, fontname=F, fontsize=11)
        y += 21

    doc.save(OUT)
    doc.close()

    hit, total, ratio = privacy_ratio(TEXT)
    print("已生成", OUT)
    print("正文字数（不含空白）:", total)
    print("隐私字符数:", hit, "占比: %.1f%%" % (ratio * 100))
    print("段落数: 1 （全文无表格、无字段标签）")
    print("隐私真值 %d 项 / 干扰真值 %d 项" % (len(TRUTH), len(NOISE)))
    return ratio


if __name__ == "__main__":
    main()
