# -*- coding: utf-8 -*-
"""刁难文档：故意不写标签 / 换标签写法 / 标签与值分离 / 纯叙述裸奔
用来检验检测引擎是否只靠「前面有没有关键字」"""
import os
import pymupdf

from _testpaths import out
OUT = out("刁难文档_无标签.pdf")


def id18(body17):
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    m = "10X98765432"
    t = sum(int(body17[i]) * w[i] for i in range(17))
    return body17 + m[t % 11]


def luhn(body):
    tot, alt = 0, True
    for ch in reversed(body):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
        alt = not alt
    return body + str((10 - tot % 10) % 10)


IDS = [id18("32058219920718001"), id18("31010419881123002"), id18("44030519950612003")]
BANKS = [luhn("622202100112345678"), luhn("621700123456789012")]
PHONES = ["13812346780", "15900871234", "18600009999"]
TELS = ["0512-67891234", "010-88997766"]
MAILS = ["chenjiahao1992@163.com", "lin.xiaowen88@qq.com"]
ADDRS = ["江苏省苏州市姑苏区干将东路88号平江华府3幢1502室",
         "浙江省杭州市西湖区文三路100号A座",
         "广东省深圳市南山区科技园南路15号"]
NAMES = ["周敏", "郑伟成", "李静", "欧阳明轩"]

doc = pymupdf.open()
W, H = 595, 842
F = "china-s"


def new_page(title):
    p = doc.new_page(width=W, height=H)
    p.insert_text((50, 50), title, fontname=F, fontsize=15)
    return p


# ============ 第1页：表格只有表头，数据行完全无标签 ============
p = new_page("一、只有表头的表格（数据行本身没有任何标签）")
p.insert_text((50, 78), "注意：下面每一行数据前面都没有「姓名」「身份证」这类词。", fontname=F, fontsize=10)

hdr = ["序号", "人员", "证件号码", "联系方式", "通讯地址"]
xs = [50, 95, 165, 320, 430]
y = 105
for i, h in enumerate(hdr):
    p.insert_text((xs[i], y), h, fontname=F, fontsize=10)
p.draw_line((48, y + 6), (545, y + 6))

rows = [
    ("1", NAMES[0], IDS[0], PHONES[0], ADDRS[0]),
    ("2", NAMES[1], IDS[1], PHONES[1], ADDRS[1]),
    ("3", NAMES[2], IDS[2], PHONES[2], ADDRS[2]),
]
y += 26
for r in rows:
    p.insert_text((xs[0], y), r[0], fontname=F, fontsize=9)
    p.insert_text((xs[1], y), r[1], fontname=F, fontsize=9)
    p.insert_text((xs[2], y), r[2], fontname=F, fontsize=7.5)
    p.insert_text((xs[3], y), r[3], fontname=F, fontsize=9)
    p.insert_text((xs[4], y), r[4], fontname=F, fontsize=5.6)
    y += 24

# ============ 第2页：换标签写法 + 标签和数据在同一行但很远 ============
p = new_page("二、换一种标签写法（都不是常见关键词）")

lines = [
    "联系方式一三八一二三四六七八零",          # 中文数字，非标准
    "手机 13812346780",                        # 只有「手机」两字，简化写法
    "另可致电 15900871234 找本人",             # 无标签，裸奔
    "证件号码 320582199207180019",              # 变体标签
    "档案编号 320582199207180019",              # 错标签（其实是身份证号）
    "卡号 6222021001123456789",                 # 变体
    "邮箱 chenjiahao1992@163.com",
    "住所在江苏省苏州市姑苏区干将东路88号平江华府3幢1502室",  # 「住所在」无冒号
    "性别 男   年龄 45",                        # 无冒号
    "生日 1992-07-18",
    "签署日期 2026年3月5日",                     # 普通日期，不应打码
]
y = 85
for i, t in enumerate(lines):
    p.insert_text((50, y), t, fontname=F, fontsize=11)
    y += 30

# ============ 第3页：纯叙述段落，完全没有标签 ============
p = new_page("三、纯叙述段落（全文没有一个字段标签）")
paras = [
    "三月五日下午，周敏带着材料来到窗口，她的证件是",
    "320582199207180019，随身带的手机是13812346780，",
    "家里住在江苏省苏州市姑苏区干将东路88号平江华府3幢1502室。",
    "",
    "同行的是郑伟成，身份证" + IDS[1] + "，",
    "他留的邮箱是lin.xiaowen88@qq.com。",
    "这次办事的日期是2026年3月5日，下次复核安排在2027年3月4日。",
    "",
    "另有李静，1992年7月18日出生，今年34岁，联系电话15900871234。",
]
y = 90
for t in paras:
    if t:
        p.insert_text((50, y), t, fontname=F, fontsize=11)
    y += 32

# ============ 第4页：日期语义对照 ============
p = new_page("四、日期语义对照（只有出生类才该打码）")
dates = [
    ("出生日期：1992年07月18日", True),
    ("生日：1992-07-18", True),
    ("出生于1992年7月18日", True),
    ("本人1992年07月18日生", True),
    ("会议日期：2026年03月05日", False),
    ("合同签署日期：2026年03月01日", False),
    ("核验日期：2026年01月08日", False),
    ("入职日期：2020年05月20日", False),
    ("有效期至2027年04月11日", False),
]
y = 85
for t, _ in dates:
    p.insert_text((50, y), t, fontname=F, fontsize=11)
    y += 34

# ============ 第5页：校验位被写错 / 字距被拉开 ============
p = new_page("五、校验位错一位、字距被拉开（扫描/OCR 常见）")
xs2 = [
    "证件号 320582199207180018（校验位写错了）",
    "身份证号 310104198811230021（校验位不对）",
    "银行卡号 6222021001123456788（Luhn 不通过）",
    "邮箱 c h e n j i a h a o 1 9 9 2 @ 1 6 3 . c o m",
]
y = 90
for t in xs2:
    p.insert_text((50, y), t, fontname=F, fontsize=11)
    y += 34

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
doc.close()
print("已生成", OUT)
