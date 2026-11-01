# -*- coding: utf-8 -*-
"""盲测：随机生成人物 + 随机号码 + 随机叙述模板，测程序能否自动识别。

生成过程完全由随机数决定（姓名、号码、地址、句式、干扰项位置都不预设），
程序侧只调用 pdfmask.detect_document / cli，不做任何人工指定或后处理。
"""

import os
import random
import string
import sys

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pdfmask  # noqa: E402

OUTDIR = os.path.join(HERE, "..", "test", "blind")
os.makedirs(OUTDIR, exist_ok=True)

SURNAMES = [c for c in pdfmask.SURNAME_1 if c not in "司项常白"]
GIVEN = list("伟芳娜敏静丽强磊洋艳勇军杰娟涛明超霞平刚英华慧美婷轩涵萱怡然睿泽宇晨欣雨思佳嘉子梓琪悦可心语诗梦瑶婉清若知宁安乐舒铭博文武斌建国志永海波江琳珊璐璇瑾瑜琛")
PROV = [("江苏省", "南京市", "鼓楼区"), ("浙江省", "杭州市", "西湖区"),
        ("广东省", "深圳市", "南山区"), ("四川省", "成都市", "武侯区"),
        ("湖北省", "武汉市", "江汉区"), ("山东省", "青岛市", "市南区"),
        ("福建省", "厦门市", "思明区"), ("陕西省", "西安市", "雁塔区"),
        ("湖南省", "长沙市", "岳麓区"), ("河南省", "郑州市", "金水区")]
ROADS = ["中山北路", "人民大道", "解放路", "建设路", "长江路", "科技园南路",
         "文化街", "新华路", "青年路", "和平大道", "花园东路", "滨江大道"]
DOMAINS = ["163.com", "qq.com", "126.com", "sina.com", "outlook.com"]
AREACODE = ["010", "021", "025", "0571", "0755", "028", "027", "0532", "029", "0731"]


def id18(area, ymd, seq):
    body = area + ymd + seq
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    m = "10X98765432"
    t = sum(int(body[i]) * w[i] for i in range(17))
    return body + m[t % 11]


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


def make_person(rnd):
    sn = rnd.choice(SURNAMES)
    n_given = rnd.choice([1, 2, 2])          # 2 字名 / 3 字名 都随机出现
    given = "".join(rnd.choice(GIVEN) for _ in range(n_given))
    name = sn + given
    y, mo, d = rnd.randint(1955, 2005), rnd.randint(1, 12), rnd.randint(1, 28)
    birth = "%d年%02d月%02d日" % (y, mo, d)
    prov, city, dist = rnd.choice(PROV)
    addr = "%s%s%s%s%d号%s栋%d室" % (
        prov, city, dist, rnd.choice(ROADS), rnd.randint(1, 300),
        rnd.choice("ABC"), rnd.randint(101, 2508))
    py = "".join(rnd.choice(string.ascii_lowercase) for _ in range(rnd.randint(5, 9)))
    return {
        "name": name,
        "phone": "1" + rnd.choice("3578") + "".join(rnd.choice(string.digits) for _ in range(9)),
        "mail": "%s%d@%s" % (py, rnd.randint(1, 99), rnd.choice(DOMAINS)),
        "addr": addr,
        "birth": birth,
        "idc": id18(rnd.choice(["320106", "110105", "310104", "440305", "510107"]),
                    "%d%02d%02d" % (y, mo, d), "%03d" % rnd.randint(1, 999)),
        "bank": luhn(rnd.choice(["622202", "621700", "622848"]) +
                     "".join(rnd.choice(string.digits) for _ in range(12))),
        "tel": "%s-%d" % (rnd.choice(AREACODE), rnd.randint(60000000, 89999999)),
        "age": str(2026 - y),
        "prov": prov, "city": city,
    }


TEMPLATES = [
    ("上午{N1}点刚过，{NAME}拎着两个纸箱从{SITE}过来，说这批样品是{CITY}仓库调的，"
     "一共{N2}箱，跑了{N3}公里，比原计划晚了{N4}分钟。会议室空调显示{TEMP}度。"
     "她一边擦汗一边掏手机拨了{PHONE}，末了补一句，有问题发我邮箱{MAIL}。"
     "{MONEY}元的采购款还没报下来，还有{YU}万尾款卡在审批。"
     "下午的会讨论了{CODE}这份合同的执行细节，签署日期定在{D1}，下次复核放在{D2}。"
     "散会时她提起住处，说现住在{ADDR}，通勤换两次地铁。"
     "她{BIRTH}出生在{CITY}，今年{AGE}岁，来公司快{N5}年。"
     "人事催她补材料，让把那张{IDC}复印一份交上去，工资卡{BANK}的开户行也要填，"
     "前台座机{TEL}找{HONOR}就行，客服热线800-820-8820是外包的不用管。"
     "快递单号{TRACK}和车牌{PLATE}她记在白板角落。"),
    ("{NAME}今天来得早，{N1}点半就在{SITE}等着了。她说{CITY}那边的{N2}箱货走的是另一条线，"
     "绕了{N3}公里。空调{TEMP}度，谁都坐不住。"
     "有急事打{PHONE}，或者发{MAIL}，两个都行。"
     "报销单上{MONEY}元那笔还没批，{YU}万的尾款也压着。"
     "会上过了一遍{CODE}合同，签字定在{D1}，复核在{D2}。"
     "她住在{ADDR}，早上要换两次车。"
     "资料里{IDC}那张还没复印，工资卡{BANK}的支行要补，座机{TEL}也能找到人。"
     "她{BIRTH}生人，今年{AGE}岁，在这边干了{N5}年。"
     "白板上还留着快递单{TRACK}和车牌{PLATE}。"),
]


def fill(tpl, p, rnd):
    return tpl.format(
        NAME=p["name"], PHONE=p["phone"], MAIL=p["mail"], ADDR=p["addr"],
        BIRTH=p["birth"], IDC=p["idc"], BANK=p["bank"], TEL=p["tel"], AGE=p["age"],
        CITY=p["city"], PROV=p["prov"],
        N1=str(rnd.randint(1, 9)), N2=str(rnd.randint(5, 90)), N3=str(rnd.randint(1, 9)),
        N4=str(rnd.randint(10, 59)), N5=str(rnd.randint(2, 12)),
        TEMP=str(rnd.randint(18, 39)), MONEY=str(rnd.randint(1000, 99999)),
        YU=str(round(rnd.uniform(0.5, 9.9), 1)),
        CODE="HT-%d-%04d" % (rnd.randint(2024, 2026), rnd.randint(1, 9999)),
        D1="%d年%d月%d日" % (2026, rnd.randint(1, 12), rnd.randint(1, 28)),
        D2="%d年%d月%d日" % (2027, rnd.randint(1, 12), rnd.randint(1, 28)),
        SITE="%s区%d号楼" % (rnd.choice("ABCD"), rnd.randint(1, 9)),
        HONOR=rnd.choice(["小王", "小李", "前台"]),
        TRACK="SF%d" % rnd.randint(10 ** 11, 10 ** 12 - 1),
        PLATE="%sA·%s%d%s" % (rnd.choice("苏浙沪粤川"), rnd.choice("DFGH"),
                              rnd.randint(10, 99), rnd.choice("ABCDEF")),
    )


def wrap(text, protect, width=38):
    spans = []
    for p in protect:
        s = 0
        while True:
            j = text.find(p, s)
            if j < 0:
                break
            spans.append((j, j + len(p)))
            s = j + 1
    UNITS = "岁年月日元万度箱个号点分公室里栋米%"
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
            if changed:
                continue
            # 不把「数字 / 数字+单位 / 英文串」掰到两行
            if (text[end - 1].isdigit() and text[end].isdigit()) or \
               (text[end - 1].isdigit() and text[end] in UNITS) or \
               (text[end] in "0123456789" and text[end - 1] in "0123456789") or \
               (text[end - 1].isascii() and text[end - 1].isalnum() and text[end].isascii() and text[end].isalnum()):
                end -= 1
                changed = True
        if end <= i:
            end = min(i + width, len(text))
        lines.append(text[i:end])
        i = end
    return lines


def build(seed, idx):
    rnd = random.Random(seed)
    p = make_person(rnd)
    text = fill(rnd.choice(TEMPLATES), p, rnd)

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 55), "工作记录（%02d）" % idx, fontname="china-s", fontsize=15)
    page.insert_text((50, 80), "随手写的记录，没有任何字段名称", fontname="china-s", fontsize=9)
    protect = [p[k] for k in ("name", "phone", "mail", "addr", "birth", "idc", "bank", "tel")]
    y = 110
    for ln in wrap(text, protect):
        page.insert_text((50, y), ln, fontname="china-s", fontsize=11)
        y += 21
    path = os.path.join(OUTDIR, "盲测%02d.pdf" % idx)
    doc.save(path)
    doc.close()
    return path, p, text


def main():
    truth_keys = [("name", "姓名"), ("phone", "手机号"), ("mail", "邮箱"), ("addr", "地址"),
                  ("birth", "出生日期"), ("idc", "身份证"), ("bank", "银行卡"), ("tel", "座机"),
                  ("age", "年龄")]
    tot_hit = tot_all = 0
    miss_by_kind = {}
    print("=" * 78)
    print("盲测：随机人物 + 随机号码（生成前未知内容），程序全自动识别")
    print("=" * 78)
    for idx in range(1, 7):
        path, p, text = build(1000 + idx * 37, idx)
        doc, fs = pdfmask.detect_document(path)
        got = [f["text"] for f in fs]
        ratio = sum(len(v) for v in p.values() if isinstance(v, str) and any(
            c.isdigit() or c in "省市区路号栋室" for c in v))
        line = []
        for k, label in truth_keys:
            v = p[k]
            ok = any(v in g or g in v for g in got)
            tot_all += 1
            if ok:
                tot_hit += 1
            else:
                miss_by_kind[label] = miss_by_kind.get(label, 0) + 1
            line.append("%s%s" % (label, "✓" if ok else "✗"))
        # 干扰项：普通日期与编号不应被打
        n_date = [d for d in ["%d年" % 2026, "%d年" % 2027] if d 
                  and any(d in g for g in got)]
        print("\n盲测%02d  姓名=%s（%d字）" % (idx, p["name"], len(p["name"])))
        print("  识别: " + "  ".join(line))
        print("  打码项数: %d" % len(fs))

    print("\n" + "-" * 78)
    print("合计召回: %d/%d = %.1f%%" % (tot_hit, tot_all, tot_hit * 100.0 / tot_all))
    if miss_by_kind:
        print("漏检分布:", miss_by_kind)
    else:
        print("漏检: 无")


if __name__ == "__main__":
    main()
