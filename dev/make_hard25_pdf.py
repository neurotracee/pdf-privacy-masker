# -*- coding: utf-8 -*-
"""刁难文档 2.5：5 页、每页多人、零标签混排，隐私信息与干扰信息交错。

生成规则：
- 全部虚构数据，但身份证校验位 / 银行卡 Luhn 均真实有效
- 姓名、号码、地址、出生日期等多人物并存，单页出现 ≥2 人
- 混入会议、金额、编号、气象、车牌、快递单号等干扰项，全程不写字段标签
- 输出隐私字符占比统计，保证 ≥30%
"""
import os
import random
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(HERE, "..", "test", "刁难文档25_多人多页.pdf")

F = "china-s"
FS = 9.5

SURNAMES = "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
GIVEN_1 = "伟芳娜秀英敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英建国志强晓明春梅雪梅"
GIVEN_2 = "华 建 平 军 峰 杰 辉 玲 红 霞 燕 敏 静 丽 强 磊 涛 明 超 鹏 宇 浩 鑫 冉 洁 慧 琳 楠 倩 颖 蕾 薇 珊 萍 玲 婷 悦 欣 怡 佳 慧"
GIVEN_2 = GIVEN_2.split()


def id18(rnd):
    """生成校验位合法的 18 位身份证"""
    area = "320106"
    y = rnd.randint(1962, 2004)
    m = rnd.randint(1, 12)
    d = rnd.randint(1, 28)
    body = "%s%04d%02d%02d%03d" % (area, y, m, d, rnd.randint(1, 999))
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    mp = "10X98765432"
    return body + mp[sum(int(body[i]) * w[i] for i in range(17)) % 11], (y, m, d)


def luhn(rnd, ln=19):
    body = "62" + "".join(str(rnd.randint(0, 9)) for _ in range(ln - 3))
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


def phone(rnd):
    return "1%d%s" % (rnd.randint(3, 9),
                      "".join(str(rnd.randint(0, 9)) for _ in range(9)))


def mail(rnd, name):
    py = "".join(["wang", "li", "zhang", "chen", "zhou", "xu", "sun", "hu", "lin", "luo"][
        rnd.randint(0, 9)])
    dom = rnd.choice(["163.com", "126.com", "qq.com", "sina.com", "outlook.com", "foxmail.com"])
    return "%s%d%d@%s" % (py, rnd.randint(0, 999), rnd.randint(0, 99), dom)


def tel(rnd):
    return "0%d-%d" % (rnd.choice([10, 21, 25, 27, 512, 571, 755]),
                       rnd.randint(1000000, 9999999))


ADDRS = ["江苏省苏州市姑苏区干将东路88号平江华府3幢1502室",
         "浙江省杭州市西湖区文三路100号东部软件园B座703",
         "北京市海淀区中关村南大街5号理工科技大厦12层",
         "上海市浦东新区张江路665号3号楼8层",
         "广东省深圳市南山区科苑南路3099号中国储能大厦27楼",
         "四川省成都市武侯区天府大道北段1700号环球中心E2座",
         "湖北省武汉市洪山区珞喻路1037号喻园小区5栋2单元",
         "山东省青岛市市南区香港中路76号颐中皇冠假日A座"]

NOISE = ["A区3号楼", "15箱", "2.5公里", "四十分钟", "36.5度", "三楼", "12800元", "3.6万",
         "五点十七分", "HT-2026-0315", "2026年3月5日", "2027年4月11日", "两次", "六点四十",
         "六年", "三个岗位", "800-820-8820", "SF1234567890123", "苏A·D2F83", "小王",
         "供应链", "Q3季度", "SKU-2024-8891", "会议室B2", "第37次", "12.6%", "4.8吨"]

NR = ["上午九点刚过", "中午吃饭的时候", "下午的会开到一半", "临近下班", "第二天一早",
      "周三的例会上", "月底对账", "台风过后的第一天"]


def make_person(rnd, used=None):
    for _ in range(400):
        s = rnd.choice(SURNAMES)
        if rnd.random() < 0.55:
            g = rnd.choice(GIVEN_2)
        else:
            g = rnd.choice(GIVEN_1)
        nm = s + g
        if used is None or nm not in used:
            if used is not None:
                used.add(nm)
            break
    idc, (y, m, d) = id18(rnd)
    age = 2026 - y
    return {
        "name": nm, "phone": phone(rnd), "mail": mail(rnd, nm),
        "addr": rnd.choice(ADDRS), "idc": idc, "bank": luhn(rnd),
        "tel": tel(rnd), "birth": "%d年%02d月%02d日" % (y, m, d),
        "age": str(age), "gender": rnd.choice(["男", "女"]),
    }


def build_text(rnd, persons):
    """拼出 5 页内容：段落 + 表格混排，全程无字段标签"""
    p1 = ("%s，%s拎着两个纸箱从%s过来，说这批样品是城南仓库调过来的，一共%s箱，"
          "路上跑了%s，比原计划晚了%s。三楼那间会议室的空调显示%s，物业派人修过一次才勉强能用。"
          "她一边擦汗一边掏手机拨了%s，把情况跟对方讲了一遍，末了补一句，有问题发我邮箱%s就行。"
          "同行的%s在旁边核对清单，说%s那份合同的执行细节还得再确认，签署日期定在%s，"
          "下一次复核放在%s。散会时她又提起住处的事，说现住在%s，通勤要换两次地铁，"
          "早上%s就得出门。人事那边催她补交材料，让把那张%s复印一份交上去，"
          "工资卡%s的开户行信息也要一起填，前台座机%s打过去找小王就行。"
          % (rnd.choice(NR), persons[0]["name"], rnd.choice(NOISE[:2]), rnd.choice(NOISE[1:2]),
             rnd.choice(NOISE[2:3]), rnd.choice(NOISE[3:4]), rnd.choice(NOISE[4:5]),
             persons[0]["phone"], persons[0]["mail"], persons[1]["name"],
             rnd.choice(NOISE[9:10]), rnd.choice(NOISE[10:11]), rnd.choice(NOISE[11:12]),
             persons[0]["addr"], rnd.choice(NOISE[13:14]), persons[0]["idc"],
             persons[0]["bank"], persons[1]["tel"]))

    p3 = ("另一批材料是%s整理的，她说自己%s出生在南京，今年%s岁，性别%s，"
          "老家在%s，父母还在那边。她留的联系方式是%s，备用邮箱%s，"
          "身份证%s和常用的那张银行卡%s都登记在这张表上。"
          "同组的%s比她晚来两年，%s那天入职，籍贯是%s，现在住在%s，"
          "手机%s，座机%s，邮箱%s，身份证号%s，工资卡%s。"
          "两个人合计报了%s的差旅，剩下的%s要走下一轮审批，"
          "发票号FP-2026-%d贴在报销单背面，单号%s，车牌%s，都是常规登记，不必重复提交。"
          % (persons[2]["name"], persons[2]["birth"], persons[2]["age"], persons[2]["gender"],
             persons[3]["addr"], persons[2]["phone"], persons[2]["mail"],
             persons[2]["idc"], persons[2]["bank"],
             persons[3]["name"], rnd.choice(NOISE[10:11]), persons[3]["addr"], persons[3]["addr"],
             persons[3]["phone"], persons[3]["tel"], persons[3]["mail"],
             persons[3]["idc"], persons[3]["bank"],
             rnd.choice(NOISE[6:7]), rnd.choice(NOISE[7:8]),
             rnd.randint(1000, 9999), rnd.choice(NOISE[17:18]), rnd.choice(NOISE[18:19])))

    p5 = ("最后一天集中核对，%s、%s、%s三个人一起到了现场，"
          "分别出示了%s、%s和%s，还有一个备用联系方式是%s和%s。"
          "其中%s的出生日期是%s，年龄%s，性别%s；%s的出生日期是%s，年龄%s，性别%s。"
          "资料袋里剩下的是%s的复印件，背面写着%s，通讯地址%s，"
          "现场温度36.5度，参与人数37人，用了2.5小时的时间，最后一批货15箱在%s送到。"
          % (persons[4]["name"], persons[5]["name"], persons[6]["name"],
             persons[4]["idc"], persons[5]["idc"], persons[6]["idc"],
             persons[5]["phone"], persons[6]["phone"],
             persons[5]["name"], persons[5]["birth"], persons[5]["age"], persons[5]["gender"],
             persons[6]["name"], persons[6]["birth"], persons[6]["age"], persons[6]["gender"],
             persons[4]["name"], persons[4]["mail"], persons[4]["addr"],
             rnd.choice(NOISE[13:14])))
    return p1, p3, p5


def wrap(text, protect, width):
    """按宽度折行，遇到受保护片段（隐私值）时整体换行，避免把号码截断"""
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


def protected(persons):
    keys = ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth")
    out = []
    for p in persons:
        for k in keys:
            out.append(p[k])
        out.append(p["age"] + "岁")
    return out


def draw_para(page, y, text, persons, rnd):
    prot = protected(persons)
    lines = wrap(text, prot, 44)
    for ln in lines:
        page.insert_text((56, y), ln, fontname=F, fontsize=FS)
        y += 15.5
        if y > 780:
            break
    return y


def draw_table(page, x0, y, rows, colw, headers, rh=30, fs=8.6):
    tw = sum(colw)
    page.draw_rect(pymupdf.Rect(x0, y, x0 + tw, y + rh * (len(rows) + 1)), color=(0, 0, 0), width=0.8)
    cx = x0
    for w in colw[:-1]:
        cx += w
        page.draw_line(pymupdf.Point(cx, y), pymupdf.Point(cx, y + rh * (len(rows) + 1)),
                       color=(0, 0, 0), width=0.6)
    for i in range(len(rows) + 2):
        yy = y + rh * i
        page.draw_line(pymupdf.Point(x0, yy), pymupdf.Point(x0 + tw, yy), color=(0, 0, 0), width=0.6)
    for j, h in enumerate(headers):
        page.insert_text((x0 + sum(colw[:j]) + 5, y + rh - 10), h, fontname=F, fontsize=fs + 0.4)
    for i, row in enumerate(rows):
        yy = y + rh * (i + 1) + rh - 10
        for j, v in enumerate(row):
            page.insert_text((x0 + sum(colw[:j]) + 5, yy), v, fontname=F, fontsize=fs)
    return y + rh * (len(rows) + 1)


def main(seed=2026, out=None):
    out = out or OUT_DEFAULT
    rnd = random.Random(seed)
    used = set()
    persons = [make_person(rnd, used) for _ in range(7)]

    doc = pymupdf.open()
    # 页1：叙述
    p = doc.new_page(width=595, height=842)
    p.insert_text((56, 60), "现场情况记录（一）", fontname=F, fontsize=13)
    p1, p3, p5 = build_text(rnd, persons)
    y = draw_para(p, 100, p1, persons, rnd)

    # 页2：人员名单表（每行不同人）
    p = doc.new_page(width=595, height=842)
    p.insert_text((56, 60), "随行人员登记（二）", fontname=F, fontsize=13)
    rows = []
    for ps in persons[:5]:
        rows.append([ps["name"], ps["gender"], ps["age"] + "岁", ps["phone"], ps["idc"]])
    y = draw_table(p, 46, 90, rows, [58, 34, 40, 96, 190],
                   ["人员", "性别", "年龄", "联系方式", "证件号码"])
    y += 24
    rows2 = [[ps["name"], ps["mail"]] for ps in persons[:5]]
    y = draw_table(p, 46, y, rows2, [58, 300], ["人员", "电子信箱"])
    y += 26
    p.insert_text((56, y), "备注：以上均为现场登记信息，随行人员共五人，车辆苏A·D2F83，", fontname=F, fontsize=9)
    p.insert_text((56, y + 16), "当天温度36.5度，共搬运15箱样品，用时2.5小时，走完了12.6%的流程。", fontname=F, fontsize=9)

    # 页3：叙述（第2组人物）
    p = doc.new_page(width=595, height=842)
    p.insert_text((56, 60), "补充说明（三）", fontname=F, fontsize=13)
    draw_para(p, 100, p3, persons, rnd)

    # 页4：开户信息表（多张卡、多地址）
    p = doc.new_page(width=595, height=842)
    p.insert_text((56, 60), "收款账户登记（四）", fontname=F, fontsize=13)
    rows3 = [[ps["name"], ps["bank"]] for ps in persons[:5]]
    y = draw_table(p, 40, 90, rows3, [56, 232], ["户名", "账号"])
    y += 22
    rows4 = [[ps["name"], ps["tel"], ps["addr"]] for ps in persons[:4]]
    y = draw_table(p, 30, y, rows4, [52, 88, 372], ["联系人", "固定电话", "通讯地址"], rh=40, fs=8.2)
    y += 24
    p.insert_text((56, y), "开户行均为中国工商银行，账号核对无误，报销单号FP-2026-3382，", fontname=F, fontsize=9)
    p.insert_text((56, y + 16), "合同编号HT-2026-0315，签署日期2026年3月5日，复核日期2027年4月11日。", fontname=F, fontsize=9)

    # 页5：混合段落（第3组人物 + 出生日期/性别/年龄）
    p = doc.new_page(width=595, height=842)
    p.insert_text((56, 60), "集中核对记录（五）", fontname=F, fontsize=13)
    y = draw_para(p, 100, p5, persons, rnd)
    y += 18
    p.insert_text((56, y), "其余事项：会议室B2、第37次例会、Q3季度指标、SKU-2024-8891、4.8吨货物，", fontname=F, fontsize=9)
    p.insert_text((56, y + 16), "客服热线800-820-8820为外包号码，快递单号SF1234567890123，均无需处理。", fontname=F, fontsize=9)

    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc.save(out, deflate=True)
    doc.close()

    # ---- 隐私字符占比统计 ----
    all_text = "".join(pg.get_text() for pg in pymupdf.open(out)).replace("\n", "")
    total = len(all_text.replace(" ", ""))
    priv = 0
    for ps in persons:
        for k in ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth"):
            priv += all_text.count(ps[k]) * len(ps[k])
        priv += all_text.count(ps["age"] + "岁") * (len(ps["age"]) + 1)
        priv += all_text.count(ps["gender"]) * 1
    print("文件:", out)
    print("页数: 5，人物: %d 人" % len(persons))
    print("隐私字符 %d / 总字符 %d = %.1f%%" % (priv, total, priv * 100.0 / max(1, total)))
    for i, ps in enumerate(persons, 1):
        print("  %d. %s %s %s %s 生日%s %s %s岁 %s %s" % (
            i, ps["name"], ps["phone"], ps["mail"], ps["idc"], ps["birth"],
            ps["gender"], ps["age"], ps["bank"], ps["tel"]))
    return persons


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    out = sys.argv[2] if len(sys.argv) > 2 else None
    main(seed, out)
