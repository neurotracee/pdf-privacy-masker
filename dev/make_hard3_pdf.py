# -*- coding: utf-8 -*-
"""刁难文档 3.0：纯段落直叙，完全不用表格。

按真实中文文档的写法：一段一段往下写，每段换行另起，人名散落在句子中间，
前后都没有「姓名：」这类标签。每页 4 个人物，隐私信息与干扰信息交错混排。
生成 5 页，三字名占多数（贴近中国真实姓名分布），另有少量两字名与复姓四字名。
"""
import os
import random
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(HERE, "..", "test", "刁难文档30_纯段落.pdf")

F = "china-s"

SURNAMES = ("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘蒋蔡余杜叶"
            "程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺"
            "顾毛郝龚邵万钱严覃武戴莫孔向汤")
COMPOUND = ["欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙", "慕容", "宇文",
            "司徒", "夏侯", "令狐", "独孤", "南宫", "西门", "百里", "轩辕"]

# 一个字的「名」——只要不是太离谱就行
G1 = list("伟芳娜敏静丽强磊军洋勇艳杰娟涛明超刚桂英华建峰辉玲红霞燕鹏宇浩鑫斌波健凯亮龙飞俊帅帆豪阳旭恒毅楠睿泽川康宁安邦才昌晨诚春聪达道德东风福富钢光广贵国海晗涵航昊禾宏洪鸿华慧吉佳嘉坚金津锦京晶敬君凯康来雷莉立丽利良琳玲凌灵露梅美萌蒙敏明铭娜楠宁培佩平萍奇琪齐启千茜倩乔巧勤青清庆琼秋泉群然仁荣容锐瑞若森珊善尚绍申深升胜诗石帅双顺硕思松素泰桃天婷彤薇文雯希喜贤祥翔肖欣新信星幸雄秀旭轩雪雅亚延艳燕扬尧耀业叶伊依仪怡宜义艺逸银英颖影映咏优友羽雨玉元源远月悦越云芸允运韵展章昭哲振正志智忠钟舟竹卓子紫宗祖佐")

G2 = ["华", "建", "平", "军", "峰", "杰", "辉", "玲", "红", "霞", "燕", "敏", "静", "丽", "强",
      "磊", "涛", "明", "超", "鹏", "宇", "浩", "鑫", "洁", "慧", "琳", "楠", "倩", "颖", "蕾",
      "薇", "珊", "萍", "婷", "悦", "欣", "怡", "佳", "志", "国", "文", "伟", "海", "波", "刚",
      "春", "梅", "雪", "云", "霞", "秀", "英", "芳", "兰", "玉", "珍", "珠", "琴", "月", "星"]

ADDRS = ["江苏省苏州市姑苏区干将东路88号平江华府3幢1502室",
         "浙江省杭州市西湖区文三路100号东部软件园B座703",
         "北京市海淀区中关村南大街5号理工科技大厦12层",
         "上海市浦东新区张江路665号3号楼8层",
         "广东省深圳市南山区科苑南路3099号中国储能大厦27楼",
         "四川省成都市武侯区天府大道北段1700号环球中心E2座",
         "湖北省武汉市洪山区珞喻路1037号喻园小区5栋2单元",
         "山东省青岛市市南区香港中路76号颐中皇冠假日A座",
         "陕西省西安市雁塔区科技路48号创业广场C座1106",
         "湖南省长沙市岳麓区麓谷大道658号麓谷企业广场A栋9层"]

NOISE = ["A区3号楼", "15箱", "2.5公里", "四十分钟", "36.5度", "三楼", "12800元", "3.6万",
         "五点十七分", "HT-2026-0315", "2026年3月5日", "2027年4月11日", "两次", "六点四十",
         "六年", "三个岗位", "800-820-8820", "SF1234567890123", "苏A·D2F83", "小王",
         "供应链", "Q3季度", "SKU-2024-8891", "会议室B2", "第37次", "12.6%", "4.8吨",
         "0.35毫米", "第六会议室", "东区仓库", "第二轮", "35页", "220伏"]

TIMES = ["上午九点刚过", "中午刚吃完饭", "下午的会开到一半", "临近下班的时候", "第二天清早",
         "周三例会上", "月底对账那几天", "台风过后的第一个工作日", "雨季来临之前", "供暖季开始以后"]


def gen_id(rnd):
    body = "320106%04d%02d%02d%03d" % (rnd.randint(1962, 2004), rnd.randint(1, 12),
                                       rnd.randint(1, 28), rnd.randint(1, 999))
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    mp = "10X98765432"
    return body + mp[sum(int(body[i]) * w[i] for i in range(17)) % 11], \
        (int(body[6:10]), int(body[10:12]), int(body[12:14]))


def gen_bank(rnd, ln=19):
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


def gen_phone(rnd):
    return "1%d%s" % (rnd.randint(3, 9), "".join(str(rnd.randint(0, 9)) for _ in range(9)))


def gen_mail(rnd):
    py = rnd.choice(["wang", "li", "zhang", "chen", "zhou", "xu", "sun", "hu", "lin", "luo",
                     "gao", "he", "guo", "ma", "luo", "liang"])
    dom = rnd.choice(["163.com", "126.com", "qq.com", "sina.com", "outlook.com", "foxmail.com"])
    return "%s%d%d@%s" % (py, rnd.randint(0, 999), rnd.randint(0, 99), dom)


def gen_tel(rnd):
    return "0%d-%d" % (rnd.choice([10, 21, 25, 27, 512, 571, 755, 29]),
                       rnd.randint(1000000, 9999999))


def gen_name(rnd, used, force_compound=False):
    """三字名约 65%，两字名约 30%，复姓四字名约 5%"""
    for _ in range(200):
        r = rnd.random()
        if force_compound or r < 0.05:
            nm = rnd.choice(COMPOUND) + rnd.choice(G1) + rnd.choice(G2)
        elif r < 0.35:
            nm = rnd.choice(SURNAMES) + rnd.choice(G1)
        else:
            nm = rnd.choice(SURNAMES) + rnd.choice(G1) + rnd.choice(G2)
        if nm not in used and len(nm) in (2, 3, 4):
            used.add(nm)
            return nm
    return "张伟明"


def gen_person(rnd, used, force_compound=False):
    nm = gen_name(rnd, used, force_compound)
    idc, (y, m, d) = gen_id(rnd)
    return {
        "name": nm, "phone": gen_phone(rnd), "mail": gen_mail(rnd),
        "addr": rnd.choice(ADDRS), "idc": idc, "bank": gen_bank(rnd),
        "tel": gen_tel(rnd), "birth": "%d年%d月%d日" % (y, m, d),
        "age": str(2026 - y), "gender": rnd.choice(["男", "女"]),
    }


# ---------------------------------------------------------------------------
# 段落句式：人名出现在句首 / 句末 / 逗号后 / 由…之后，全部没有标签
# ---------------------------------------------------------------------------

def n1(rnd, p, q):
    """人物出场 + 手机号 + 邮箱（顺带提到另一个人）"""
    return (
        "%s，%s从%s赶过来，进门先把%s放下，说这批货在%s到过一站，"
        "路上耽误了%s。%s在旁边翻清单，提到那份材料还有两处没对齐，"
        "让她直接打%s确认，说不通就发邮件%s。"
        % (rnd.choice(TIMES), p["name"], rnd.choice(NOISE[26:28]), rnd.choice(NOISE[1:2]),
           rnd.choice(NOISE[30:32]), rnd.choice(NOISE[2:3]), q["name"],
           p["phone"], p["mail"])
    )


def d1(rnd, p):
    """身份证 + 银行卡 + 地址 + 出生 + 性别 + 年龄 + 座机"""
    return (
        "据%s回忆，当初登记表上写的是%s，工资卡用的是%s，"
        "开户行在%s附近。%s出生，%s，今年%s岁，"
        "现住在%s，办公座机%s，手机%s，邮箱%s，有事打哪个都能找到人。"
        % (p["name"], p["idc"], p["bank"], rnd.choice(NOISE[27:29]),
           p["birth"], p["gender"], p["age"], p["addr"], p["tel"],
           p["phone"], p["mail"])
    )


def n2(rnd, p, q):
    """转述口吻，人名出现在句中"""
    return (
        "%s说那批货%s就到了，让%s先别急着签收，"
        "等复核完再走下一步。她自己的号码是%s，"
        "备用邮箱%s，说平时收得少。"
        % (p["name"], rnd.choice(NOISE[10:12]), q["name"], p["phone"], p["mail"])
    )


def d2(rnd, p):
    """把数据揉进一段感慨里"""
    return (
        "最后还是%s那边把材料补齐的。身份证%s，卡号%s，"
        "她%s出生，%s，%s岁，住%s，"
        "座机%s，手机%s，邮箱%s，说这几个号码都用好多年了。"
        % (p["name"], p["idc"], p["bank"], p["birth"], p["gender"], p["age"],
           p["addr"], p["tel"], p["phone"], p["mail"])
    )


def n3(rnd, p, q):
    """两个人一起出现"""
    return (
        "%s核对完之后签了字，%s跟着也签了，两个人合计报了%s，"
        "剩下的%s要走下一轮审批，发票贴在报销单背面，"
        "有疑问可以打%s或者%s。"
        % (p["name"], q["name"], rnd.choice(NOISE[6:7]), rnd.choice(NOISE[7:8]),
           p["phone"], q["phone"])
    )


def d3(rnd, p):
    """语气再换一种"""
    return (
        "档案袋上写着%s的名字，里面的号码是%s，卡号%s，"
        "%s出生，%s，%s岁，通讯地址%s，"
        "座机%s，手机%s，邮箱%s，都对过一遍。"
        % (p["name"], p["idc"], p["bank"], p["birth"], p["gender"], p["age"],
           p["addr"], p["tel"], p["phone"], p["mail"])
    )


def n4(rnd, p, q):
    """短句起头，人名放句末"""
    return (
        "这趟跑下来最辛苦的是%s，%s在旁边打下手，"
        "两个人在%s等了%s才把手续办完。"
        "留的手机是%s，另一个是%s，都能联系上。"
        % (p["name"], q["name"], rnd.choice(NOISE[25:27]), rnd.choice(NOISE[2:3]),
           p["phone"], q["phone"])
    )


def d4(rnd, p):
    return (
        "%s的材料单独放一袋：%s，%s，%s出生，%s，%s岁，"
        "住在%s，座机%s，手机%s，邮箱%s。"
        % (p["name"], p["idc"], p["bank"], p["birth"], p["gender"], p["age"],
           p["addr"], p["tel"], p["phone"], p["mail"])
    )


NARRS = [n1, n2, n3, n4]
DATAS = [d1, d2, d3, d4]


def wrap(text, protect, width):
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
    out = []
    for p in persons:
        for k in ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth"):
            out.append(p[k])
        out.append(p["age"] + "岁")
    return out


def draw_para(page, y, text, persons, rnd, fs=9.6, indent=0.0, lh=15.8):
    lines = wrap(text, protected(persons), 43 if fs >= 9.4 else 45)
    for k, ln in enumerate(lines):
        page.insert_text((56 + (indent if k == 0 else 0), y), ln, fontname=F, fontsize=fs)
        y += lh
    return y + 8


def build(rnd, persons):
    """5 页，每页 4 人，全部是段落，没有一张表格；每人叙述段 + 数据段各一"""
    pages = []
    for i in range(5):
        a, b, c, d = persons[i * 4:i * 4 + 4]
        nr = rnd.choice(NARRS)
        nr2 = rnd.choice([x for x in NARRS if x is not nr])
        dr = rnd.choice(DATAS)
        dr2 = rnd.choice([x for x in DATAS if x is not dr])
        blocks = [
            nr(rnd, a, b),
            dr(rnd, a),
            nr2(rnd, b, c),
            dr2(rnd, b),
            rnd.choice(NARRS)(rnd, c, d),
            rnd.choice(DATAS)(rnd, c),
            dr(rnd, d),
        ]
        pages.append(blocks)
    return pages


TITLES = ["一、现场情况记录", "二、补充说明", "三、人员情况汇总", "四、核对过程描述", "五、收尾与移交"]


def main(seed=2026, out=None):
    out = out or OUT_DEFAULT
    rnd = random.Random(seed)
    used = set()
    persons = [gen_person(rnd, used, force_compound=(i in (3, 14)))
               for i in range(20)]

    doc = pymupdf.open()
    pages_text = build(rnd, persons)
    for i, blocks in enumerate(pages_text):
        page = doc.new_page(width=595, height=842)
        page.insert_text((56, 62), TITLES[i], fontname=F, fontsize=13.5)
        page.insert_text((56, 82), "本页所涉人员信息均为虚构，仅用于流程演练。",
                         fontname=F, fontsize=8.5)
        y = 112.0
        for j, tx in enumerate(blocks):
            fs = 9.6 if j % 3 else 9.9
            y = draw_para(page, y, tx, persons, rnd, fs=fs,
                          indent=(0.0 if j % 2 else 9.0), lh=15.8)
            if y > 760:
                break

    os.makedirs(os.path.dirname(out), exist_ok=True)
    doc.save(out, deflate=True)
    doc.close()

    all_text = "".join(pg.get_text() for pg in pymupdf.open(out)).replace("\n", "")
    total = len(all_text.replace(" ", ""))
    priv = 0
    for ps in persons:
        for k in ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth"):
            priv += all_text.count(ps[k]) * len(ps[k])
        priv += all_text.count(ps["age"] + "岁") * (len(ps["age"]) + 1)
        priv += all_text.count(ps["gender"])
    print("文件:", out)
    print("页数 5，人物 %d 人（三字名 %d / 两字名 %d / 复姓 %d）" % (
        len(persons),
        sum(1 for p in persons if len(p["name"]) == 3),
        sum(1 for p in persons if len(p["name"]) == 2),
        sum(1 for p in persons if len(p["name"]) == 4)))
    print("隐私字符 %d / 总字符 %d = %.1f%%" % (priv, total, priv * 100.0 / max(1, total)))

    # 自校验：每个人的每一项是否都真的写进了 PDF（避免段落被挤出页面）
    missing = []
    for i, ps in enumerate(persons, 1):
        for k in ("name", "phone", "mail", "addr", "idc", "bank", "tel", "birth"):
            if ps[k].replace(" ", "") not in all_text:
                missing.append((i, ps["name"], k))
        if (ps["age"] + "岁") not in all_text:
            missing.append((i, ps["name"], "age"))
    if missing:
        print("  !! 有 %d 项没写进 PDF：" % len(missing))
        for m in missing[:10]:
            print("     ", m)
    else:
        print("  自校验：20 人 × 9 项隐私数据全部写进正文")
    for i, ps in enumerate(persons, 1):
        print("  %2d. %s(%d字)" % (i, ps["name"], len(ps["name"])))
    return persons


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    out = sys.argv[2] if len(sys.argv) > 2 else None
    main(seed, out)
