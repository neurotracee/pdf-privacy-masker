# -*- coding: utf-8 -*-
"""生成一份高浓度虚构隐私信息的中文 PDF，用于端到端自检"""
import os
import pymupdf

OUT = os.path.join(os.path.dirname(__file__), "..", "test", "测试文档_含隐私.pdf")
os.makedirs(os.path.dirname(OUT), exist_ok=True)


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


ID1 = id18("32058219920718001")
ID2 = id18("31010419881123002")
BANK1 = luhn("622202100112345678")
BANK2 = luhn("621700123456789012")
PHONE1 = "13812346780"
PHONE2 = "15900871234"
TEL1 = "0512-67891234"
TEL2 = "010-88997766"
MAIL1 = "chenjiahao1992@163.com"
MAIL2 = "lin.xiaowen88@qq.com"
ADDR1 = "江苏省苏州市姑苏区干将东路88号平江华府3幢1502室"
ADDR2 = "上海市徐汇区漕溪北路398号汇智大厦B座901室"
NAME1 = "陈嘉豪"
NAME2 = "林晓雯"
BIRTH1 = "1992年07月18日"
BIRTH2 = "1988年11月23日"

F = "china-s"
FB = "china-ss"


def fit(text, maxw, size=10.5, font=F):
    """字号自适应，保证不出框"""
    while size > 6.5:
        if pymupdf.get_text_length(text, fontname=font, fontsize=size) <= maxw:
            return size
        size -= 0.5
    return size


def main():
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    y = 56
    page.insert_text((170, y), "员工入职信息登记表", fontname=FB, fontsize=20)
    page.insert_text((60, y + 22), "编号：HR-2026-0315", fontname=F, fontsize=9)

    # (label1, value1, label2, value2)  第二对为空则整行合并
    rows = [
        ("姓名", NAME1, "性别", "男"),
        ("出生日期", BIRTH1, "年龄", "34岁"),
        ("身份证号", ID1, "手机号", PHONE1),
        ("座机号", TEL1, "开户行", "中国工商银行"),
        ("电子邮箱", MAIL1, "", ""),
        ("家庭住址", ADDR1, "", ""),
        ("银行卡号", BANK1, "", ""),
        ("紧急联系人", NAME2, "联系电话", PHONE2),
        ("身份证号", ID2, "年龄", "37岁"),
        ("备用邮箱", MAIL2, "", ""),
        ("单位地址", ADDR2, "", ""),
        ("座机", TEL2, "出生日期", BIRTH2),
    ]

    top = y + 44
    rh = 31
    x0, x1, x2 = 60, 165, 355
    RIGHT = 535
    for i, (k1, v1, k2, v2) in enumerate(rows):
        yy = top + i * rh
        page.draw_rect(pymupdf.Rect(x0, yy, RIGHT, yy + rh), color=(0.65, 0.65, 0.65), width=0.7)
        page.draw_line(pymupdf.Point(x1, yy), pymupdf.Point(x1, yy + rh), color=(0.65, 0.65, 0.65), width=0.7)
        page.insert_text((x0 + 8, yy + 21), k1, fontname=F, fontsize=10, color=(0.25, 0.25, 0.25))
        if k2:
            page.draw_line(pymupdf.Point(x2, yy), pymupdf.Point(x2, yy + rh), color=(0.65, 0.65, 0.65), width=0.7)
            fs = fit(v1, x2 - x1 - 14)
            page.insert_text((x1 + 8, yy + 21), v1, fontname=F, fontsize=fs)
            page.insert_text((x2 + 8, yy + 21), k2, fontname=F, fontsize=10, color=(0.25, 0.25, 0.25))
            fs2 = fit(v2, RIGHT - x2 - 100)
            page.insert_text((x2 + 100, yy + 21), v2, fontname=F, fontsize=fs2)
        else:
            fs = fit(v1, RIGHT - x1 - 14)
            page.insert_text((x1 + 8, yy + 21), v1, fontname=F, fontsize=fs)

    y2 = top + len(rows) * rh + 44
    page.insert_text((60, y2), "本人承诺以上信息真实有效，如有变更及时告知。", fontname=F, fontsize=11)
    page.insert_text((60, y2 + 28), "签名：陈嘉豪            日期：2026年03月15日", fontname=F, fontsize=11)

    # ---------------- 第 2 页：正文 + 普通日期对照 ----------------
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((170, 62), "个人信息授权与项目会议纪要", fontname=FB, fontsize=16)

    lines = [
        "一、信息确认",
        "本人陈嘉豪，出生日期1992年07月18日，身份证号%s，现居住于%s。" % (ID1, ADDR1),
        "手机号%s，座机0512-67891234，邮箱%s。配偶林晓雯，手机%s。" % (PHONE1, MAIL1, PHONE2),
        "收款账户为%s（中国工商银行），开户名陈嘉豪。" % BANK1,
        "",
        "二、项目会议安排（普通日期，不应打码）",
        "2026年03月05日上午9时，于苏州总部3楼会议室召开季度经营分析会。",
        "会议报名截止日期：2026年03月01日，合同签订日期：2026年04月12日。",
        "本次合同有效期自2026年04月12日至2027年04月11日。",
        "",
        "三、补充说明",
        "联系人：陈嘉豪    联系电话：%s" % PHONE2,
        "备用地址：%s，收件人：林晓雯。" % ADDR2,
        "身份证件已于2026年01月08日完成核验，核验人：林晓雯。",
        "配偶银行卡%s，开户邮箱%s。" % (BANK2, MAIL2),
    ]
    yy = 104
    for ln in lines:
        if ln:
            fs = fit(ln, 475, 10.5)
            p2.insert_text((60, yy), ln, fontname=F, fontsize=min(fs, 10.5))
        yy += 22 if ln else 12

    doc.save(OUT)
    doc.close()

    pii = [NAME1, NAME2, ID1, ID2, BANK1, BANK2, PHONE1, PHONE2, TEL1, TEL2,
           MAIL1, MAIL2, ADDR1, ADDR2, BIRTH1, BIRTH2, "男", "34岁", "37岁"]
    d = pymupdf.open(OUT)
    allch = "".join(p.get_text() for p in d).replace("\n", "").replace(" ", "")
    d.close()
    hit = sum(allch.count(x.replace(" ", "")) * len(x.replace(" ", "")) for x in pii)
    print("输出:", os.path.abspath(OUT))
    print("全文有效字符:", len(allch), " 隐私字符:", hit, " 占比: %.1f%%" % (100.0 * hit / len(allch)))


if __name__ == "__main__":
    main()
