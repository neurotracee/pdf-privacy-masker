# -*- coding: utf-8 -*-
"""端到端自检：检测覆盖率 / 文本层抹除 / 马赛克不可辨 / 版面一致 / 原文件未改"""
import hashlib
import os
import subprocess
import sys
import tempfile

import pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import pdfmask  # noqa: E402
from _testpaths import IN_DIR, out  # noqa: E402

# 输入样本只读自 test/；本次产生的 pdf / png 全部写到临时目录，
# 跑完不会在 git 工作区里留下任何垃圾文件。
OUT_DIR = os.environ.get("PDFMASK_TEST_DIR") or tempfile.mkdtemp(prefix="pdfmask-selfcheck-")
os.makedirs(OUT_DIR, exist_ok=True)
ENV = dict(os.environ, PDFMASK_TEST_DIR=OUT_DIR)

SRC = os.path.join(IN_DIR, "测试文档_含隐私.pdf")
OUT = out("测试文档_打码后.pdf")

PII = {
    "姓名": ["陈嘉豪", "林晓雯"],
    "身份证号": ["320582199207180019", "31010419881123002X"],
    "银行卡号": ["6222021001123456789", "6217001234567890122"],
    "手机号": ["13812346780", "15900871234"],
    "座机号": ["0512-67891234", "010-88997766"],
    "邮箱": ["chenjiahao1992@163.com", "lin.xiaowen88@qq.com"],
    "地址": ["江苏省苏州市姑苏区干将东路88号平江华府3幢1502室",
             "上海市徐汇区漕溪北路398号汇智大厦B座901室"],
    "出生日期": ["1992年07月18日", "1988年11月23日"],
}
SURNAME_KEEP = ["陈", "林"]
NORMAL_DATES = ["2026年03月05日", "2026年03月01日", "2026年04月12日",
                "2027年04月11日", "2026年01月08日", "2026年03月15日"]

ok_all = True


def check(name, cond, detail=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""))


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    print("=" * 72)
    print("PDF 隐私打码工具 · 端到端自检")
    print("=" * 72)

    h_before = md5(SRC)
    doc0 = pymupdf.open(SRC)
    src_text = "".join(p.get_text() for p in doc0)
    flat = src_text.replace("\n", "").replace(" ", "")

    # --- 1. 测试样本隐私浓度 ---
    print("\n[1] 测试样本")
    pii_chars = sum(flat.count(x.replace(" ", "")) * len(x.replace(" ", "")) for v in PII.values() for x in v)
    pii_chars += flat.count("男") * 1 + flat.count("34岁") * 3 + flat.count("37岁") * 3
    ratio = 100.0 * pii_chars / len(flat)
    check("隐私信息占比 ≥ 30%%（实际 %.1f%%，%d/%d 字符）" % (ratio, pii_chars, len(flat)), ratio >= 30)

    # --- 2. 检测召回 ---
    print("\n[2] 检测召回")
    doc, findings = pdfmask.detect_document(SRC)
    texts = [f["text"] for f in findings]
    joined = "|".join(texts)
    for kind, items in PII.items():
        for it in items:
            hit = it in joined
            check("%s %s" % (kind, it[:22]), hit)
    check("性别「男」", any(f["type"] == "gender" for f in findings))
    check("年龄 34 / 37", sum(1 for f in findings if f["type"] in ("age",)) >= 2)
    dom = {}
    for f in findings:
        dom[pdfmask.TYPE_NAME.get(f["type"], f["type"])] = dom.get(pdfmask.TYPE_NAME.get(f["type"], f["type"]), 0) + 1
    print("      检出分布:", dom, "共", len(findings), "处")

    # 姓名保留姓氏
    nm = [f for f in findings if f["type"] == "name"]
    check("姓名保留姓氏（打码从第 2 字开始）", all(f["note"].startswith("保留姓氏") for f in nm),
          "%d 处姓名全部保留姓氏" % len(nm))

    # --- 3. 普通日期不被误判 ---
    print("\n[3] 日期语义区分")
    for d in NORMAL_DATES:
        check("普通日期未命中: %s" % d, not any(d.replace(" ", "") in t.replace(" ", "") for t in texts))
    check("出生日期已命中", sum(1 for f in findings if f["type"] == "birth") >= 2)

    # --- 4. 执行打码 ---
    print("\n[4] 执行打码")
    if os.path.exists(OUT):
        os.remove(OUT)
    pdfmask.cli(SRC, OUT, verbose=False)
    check("输出文件已生成", os.path.exists(OUT))
    check("原文件未被修改（MD5 一致）", md5(SRC) == h_before)
    doc2 = pymupdf.open(OUT)
    check("页数一致 (%d)" % doc0.page_count, doc2.page_count == doc0.page_count)
    same_size = all(abs(a.rect.width - b.rect.width) < 0.1 and abs(a.rect.height - b.rect.height) < 0.1
                    for a, b in zip(doc0, doc2))
    check("页面尺寸一致", same_size)

    # --- 5. 文本层彻底抹除 ---
    print("\n[5] 文本层抹除")
    out_text = "".join(p.get_text() for p in doc2)
    out_flat = out_text.replace("\n", "").replace(" ", "")
    leaked = []
    for kind, items in PII.items():
        for it in items:
            probe = it.replace(" ", "")
            if kind == "姓名":
                probe = probe[1:]  # 名字部分（姓氏允许保留）
            if probe in out_flat:
                leaked.append("%s:%s" % (kind, it))
    check("敏感串全部从文本层消失", not leaked, "泄漏: " + ", ".join(leaked) if leaked else "")
    check("姓氏仍可正常选中（陈/林 保留在文本层）",
          all(s in out_flat for s in SURNAME_KEEP))
    for d in NORMAL_DATES:
        check("普通日期文本保留: %s" % d, d.replace(" ", "") in out_flat)
    # 非敏感正文完整
    body = "本人承诺以上信息真实有效，如有变更及时告知。"
    check("非敏感正文完整保留", body in out_flat.replace(" ", ""))
    check("章节标题完整保留", "二、项目会议安排" in out_flat)

    # 高亮标注不应残留
    check("未残留任何 redact 注释框", not any(
        (a.type[0] in (12,) or a.type[1] == "Redact") for p in doc2 for a in p.annots()))

    # --- 6. 马赛克真实性与不可辨性 ---
    print("\n[6] 马赛克真实性")
    z = pdfmask.MOSAIC_ZOOM
    checked = 0
    worst_ratio = 0.0
    for f in findings:
        page_o = doc0[f["page"]]
        page_n = doc2[f["page"]]
        r = f["rect"]
        clip = pymupdf.Rect(max(0, r.x0 - 0.2), max(0, r.y0 - 0.2),
                            min(page_o.rect.x1, r.x1 + 0.2), min(page_o.rect.y1, r.y1 + 0.2))
        if clip.width < 6 or clip.height < 6:
            continue
        m = pymupdf.Matrix(z, z)
        po = page_o.get_pixmap(clip=clip, matrix=m, alpha=False, colorspace=pymupdf.csGRAY)
        pn = page_n.get_pixmap(clip=clip, matrix=m, alpha=False, colorspace=pymupdf.csGRAY)
        io_ = Image.frombytes("L", (po.width, po.height), po.samples)
        inr = Image.frombytes("L", (pn.width, pn.height), pn.samples)
        # 高频能量（拉普拉斯方差）对比：马赛克应显著低于原文
        def hf(img):
            w, h = img.size
            px = img.load()
            acc = 0.0
            cnt = 0
            for y in range(1, h - 1, 2):
                for x in range(1, w - 1, 2):
                    v = (4 * px[x, y] - px[x - 1, y] - px[x + 1, y] - px[x, y - 1] - px[x, y + 1])
                    acc += v * v
                    cnt += 1
            return acc / max(1, cnt)
        h_o, h_n = hf(io_), hf(inr)
        if h_o > 40:
            checked += 1
            ratio_hf = h_n / h_o
            worst_ratio = max(worst_ratio, ratio_hf)
    check("高频细节能量下降 >90%（原文字形已被打散）", worst_ratio < 0.10,
          "最差区域残留 %.1f%%，抽检 %d 处" % (worst_ratio * 100, checked))

    # 边缘密度：马赛克块边界稀疏（约 1/块宽），文字笔画边界密集，纯色块则为 0
    def edge_density(img, thr=25):
        w, h = img.size
        px = img.load()
        big = tot = 0
        for y in range(0, h):
            for x in range(1, w):
                tot += 1
                if abs(px[x, y] - px[x - 1, y]) > thr:
                    big += 1
        return big / max(1, tot)

    f0 = next(f for f in findings if f["type"] == "idcard")
    r = f0["rect"]
    z2 = pdfmask.MOSAIC_ZOOM
    po = doc0[f0["page"]].get_pixmap(clip=r, matrix=pymupdf.Matrix(z2, z2), alpha=False, colorspace=pymupdf.csGRAY)
    pn = doc2[f0["page"]].get_pixmap(clip=r, matrix=pymupdf.Matrix(z2, z2), alpha=False, colorspace=pymupdf.csGRAY)
    io_ = Image.frombytes("L", (po.width, po.height), po.samples)
    inr = Image.frombytes("L", (pn.width, pn.height), pn.samples)
    d_o, d_n = edge_density(io_), edge_density(inr)
    check("打码后边缘密度骤降（原 %.1f%% → %.1f%%），字形结构消失" % (d_o * 100, d_n * 100), d_n < d_o * 0.25)
    check("打码区仍有像素块纹理（非纯色块涂抹）", d_n > 0.002,
          "边缘密度 %.2f%%" % (d_n * 100))

    # 嵌入图像数量（证明是贴图而非涂色）
    imgs = sum(len(p.get_images(full=True)) for p in doc2)
    check("打码区域以嵌入位图实现（非矢量色块）", imgs >= len(set(f["page"] for f in findings)),
          "共嵌入 %d 张位图" % imgs)

    # --- 7. 旋转页（扫描件常见 /Rotate 90） ---
    print("\n[7] 旋转页回归")
    rot_src = out("rot90.pdf")
    rot_out = out("rot90_out.pdf")
    dd = pymupdf.open()
    pp = dd.new_page(width=595, height=842)
    idr = "110105199003072316"
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    mm = "10X98765432"
    idr = idr[:17] + mm[sum(int(idr[i]) * w[i] for i in range(17)) % 11]
    pp.insert_text((60, 100), "姓名：周思远", fontname="china-s", fontsize=14)
    pp.insert_text((60, 130), "手机：13700001111", fontname="china-s", fontsize=14)
    pp.insert_text((60, 160), "身份证号：" + idr, fontname="china-s", fontsize=14)
    pp.insert_text((60, 190), "地址：北京市朝阳区建国路88号现代城3号楼1502室", fontname="china-s", fontsize=14)
    pp.set_rotation(90)
    dd.save(rot_src)
    dd.close()
    for f in (rot_out,):
        if os.path.exists(f):
            os.remove(f)
    pdfmask.cli(rot_src, rot_out, verbose=False)
    rtxt = "".join(p.get_text() for p in pymupdf.open(rot_out)).replace("\n", "").replace(" ", "")
    chk_ids = [idr, "13700001111", "北京市朝阳区建国路88号现代城3号楼1502室", "思远"]
    for probe in chk_ids:
        check("旋转页已抹除 %s" % probe[:14], probe not in rtxt)
    check("旋转页保留了姓氏「周」", "周" in rtxt)
    rp = pymupdf.open(rot_out)[0]
    check("旋转页输出为 0°（已固化，坐标不再错位）", rp.rotation == 0)

    # --- 8. 无标签场景（检验是否只靠关键字） ---
    print("\n[8] 无标签 / 变体写法场景")
    hard = out("刁难文档_无标签.pdf")
    subprocess.run([sys.executable, os.path.join(HERE, "make_hard_pdf.py")],
                   check=True, capture_output=True, env=ENV)
    hdoc, hfs = pdfmask.detect_document(hard)
    htext = "".join(p.get_text() for p in hdoc)
    hgot = [f["text"] for f in hfs]
    # 表头只有「人员」，数据行无任何关键字 → 姓名仍应识别
    for nm in ("周敏", "郑伟成", "李静"):
        check("表头列无标签姓名 %s" % nm, any(nm == g for g in hgot))
    # 纯叙述段落里裸奔的号码
    for probe in ("13812346780", "320582199207180019", "6222021001123456789",
                  "chenjiahao1992@163.com"):
        check("无标签号码/邮箱 %s" % probe[:12], any(probe in g for g in hgot))
    check("无标签地址被识别", any(f["type"] == "address" for f in hfs))
    # 出生词写在日期后面
    check("「1992年7月18日出生」后置写法被识别",
          any(f["type"] == "birth" and "1992年7月18日" == f["text"] for f in hfs))
    # 「34岁」无「周岁」
    check("「34岁」简写被识别为年龄",
          any(f["type"] == "age" and f["text"] == "34" for f in hfs))
    # 校验位写错 / Luhn 不通过 → 标签兜底仍要打
    check("校验位写错的身份证仍被识别",
          any(f["type"] == "idcard" and f["text"] == "320582199207180018" for f in hfs))
    check("校验位不对的身份证仍被识别",
          any(f["type"] == "idcard" and f["text"] == "310104198811230021" for f in hfs))
    check("Luhn 不通过的银行卡仍被识别",
          any(f["type"] == "bankcard" and f["text"] == "6222021001123456788" for f in hfs))
    check("字距被拉开的邮箱被还原识别",
          any(f["type"] == "email" and f["text"] == "chenjiahao1992@163.com"
              and f.get("note") == "字距还原" for f in hfs))
    # 普通日期一个都不能动
    for d in ("2026年03月05日", "2026年03月01日", "2026年01月08日",
              "2020年05月20日", "2027年04月11日"):
        check("普通日期未被误打 %s" % d, not any(d in g for g in hgot))
    # 有标签但没有敏感内容 → 不能乱打
    fp = out("_fp.pdf")
    if os.path.exists(fp):
        fdoc, ffs = pdfmask.detect_document(fp)
        bad = [f for f in ffs if f["type"] in ("idcard", "name", "bankcard", "phone")]
        check("有「身份证/姓名」字样但无号码时不误打", not bad,
              "误打 %d 处" % len(bad))

    # --- 9. 纯段落无标签（刁难文档 2.0：一整段叙述 + 隐私与干扰混排） ---
    print("\n[9] 纯段落 · 隐私与干扰混排")
    subprocess.run([sys.executable, os.path.join(HERE, "make_hard2_pdf.py")],
                   check=True, capture_output=True, env=ENV)
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "test_hard2.py")],
                        capture_output=True, text=True, env=ENV,
                        encoding="utf-8", errors="replace")
    for ln in (r2.stdout or "").splitlines():
        if any(k in ln for k in ("召回:", "误报:", "隐私残留", "干扰保留", "正文字数")):
            print("      " + ln.strip())
    check("纯段落：13 项隐私全召回 / 0 误报 / 干扰全保留", r2.returncode == 0)

    # --- 10. 假阳性专项：完全无隐私的长文不应认错任何东西 ---
    print("\n[10] 假阳性专项（1100+ 字纯净说明文）")
    r3 = subprocess.run([sys.executable, os.path.join(HERE, "test_no_false_positive.py")],
                        capture_output=True, text=True, env=ENV,
                        encoding="utf-8", errors="replace")
    for ln in (r3.stdout or "").splitlines():
        if any(k in ln for k in ("文档字数", "检出总数")):
            print("      " + ln.strip())
    check("无隐私长文被误判 0 处", r3.returncode == 0 and "检出总数: 0" in (r3.stdout or ""))

    # --- 11. 视觉回归图 ---
    print("\n[11] 生成视觉对比图")
    for i in range(doc2.page_count):
        doc2[i].get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(
            out("after_p%d.png" % (i + 1)))
    a = next(f for f in findings if f["type"] == "idcard")
    cl = pymupdf.Rect(a["rect"].x0 - 6, a["rect"].y0 - 6, a["rect"].x0 + 130, a["rect"].y1 + 6)
    doc0[a["page"]].get_pixmap(clip=cl, matrix=pymupdf.Matrix(6, 6)).save(
        out("zoom_before.png"))
    doc2[a["page"]].get_pixmap(clip=cl, matrix=pymupdf.Matrix(6, 6)).save(
        out("zoom_after.png"))
    print("      对比图输出到: %s" % OUT_DIR)

    # --- 12. 注释 / 书签 ---
    # 这两类对象不在正文文字流里，必须单独验；并进主流程，免得改别处时忘跑。
    print("\n[12] 注释与书签")
    r = subprocess.run([sys.executable, os.path.join(HERE, "test_scrub_notes.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV)
    ok = r.returncode == 0
    check("注释/书签里的隐私已清（含只出现在注释里的姓名、地址）", ok,
          "" if ok else (r.stdout or r.stderr or "")[-300:])
    if not ok:
        print((r.stdout or "")[-1200:])

    print("\n" + "=" * 72)
    print("产物目录:", OUT_DIR, "（不在仓库内，git 工作区保持干净）")
    print("自检结论:", "全部通过" if ok_all else "存在未通过项")
    print("=" * 72)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
