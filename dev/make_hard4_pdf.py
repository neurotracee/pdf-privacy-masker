# -*- coding: utf-8 -*-
"""刁难文档 4.0「扫描件硬核版」：8 页真实单据，全部是图片、没有文字层。

针对 v1.4.6 新增的「扫描件 / 图片型 PDF 自动识别」下刀子：

* 每一页都是**纯文字段落**（简历、合同、病历、对账单、面单、通知、
  理赔单、家长登记），不摆表格——真实扫描件大多是这种版面；
* 每页多人、多号码、多地址，单页敏感项 6~12 条；
* 整页渲染成 150~220 dpi 灰度图，再叠加轻微倾斜、噪点、光照不均、
  JPEG 压缩痕迹，模拟真机扫描 / 手机拍照转 PDF；
* **最终 PDF 里没有一行文字层**，程序只能靠自己 OCR。

本脚本只负责造文档，不参与识别与打码。识别、打码、验证全部交给
`pdfmask.py` 与 `dev/test_hard4.py`——不给程序任何提示，也不替它作弊。

真值随文档写到 `test/hard4/刁难文档4_扫描件.truth.json`：
  secrets  必须打掉（打码后不得再被提取）
  noise    必须保留（业务编号、金额、日期、公开信息）
"""
import json
import os
import sys

import pymupdf
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "test", "hard4")

A4 = pymupdf.paper_rect("a4")
MARGIN = 46
BODY = 10.5
LEAD = 16.5

CASES = []
PAGES = []          # [(page_no, [(line, size, bold)])]


def fontfile():
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc",
              "C:/Windows/Fonts/simhei.ttf",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if os.path.isfile(p):
            return p
    return None


FF = fontfile()


class Sheet(object):
    """一页「原件」：先排文字，稍后整页渲染成图。"""

    def __init__(self, title, dpi=200, angle=0.6):
        self.title = title
        self.dpi = dpi
        self.angle = angle
        self.lines = []          # [(text, size, bold, indent)]
        self.cases = []

    def head(self, s):
        self.lines.append((s, 15, True, 0))

    def para(self, s, indent=0, size=BODY, bold=False):
        self.lines.append((s, size, bold, indent))

    def blank(self):
        self.lines.append(("", BODY, False, 0))

    def case(self, cid, category, text, secrets=(), noise=(), level="must", note=""):
        self.cases.append({"id": cid, "category": category, "text": text,
                           "secrets": list(secrets), "noise": list(noise),
                           "level": level, "note": note})


# --------------------------------------------------------------------------
# 八页真实单据
# --------------------------------------------------------------------------

def sheet_resume():
    s = Sheet("求职简历", dpi=300, angle=0.5)
    s.head("个人简历")
    s.blank()
    s.para("姓名：李秀英　　性别：女　　年龄：32 岁　　出生日期：1994 年 3 月 8 日")
    s.para("手机：139-1111-2222　　电子邮箱：lixiuying94@example.com.cn")
    s.para("现居地址：上海市徐汇区漕溪北路 398 号 3 号楼 1502 室")
    s.para("身份证号：320106199403081234")
    s.blank()
    s.para("教育背景")
    s.para("2012 年 9 月至 2016 年 6 月，华东师范大学，计算机科学与技术，本科。")
    s.blank()
    s.para("工作经历")
    s.para("2016 年 7 月至 2021 年 9 月，在上海云枢信息技术有限公司任后端开发工程师，")
    s.para("负责订单系统与结算模块。离职前月薪 18000 元。")
    s.para("2021 年 10 月至今，在杭州数聚科技有限公司任高级开发工程师，负责数据平台。")
    s.blank()
    s.para("紧急联系人：张伟，关系：配偶，电话：137-3333-4444。")
    s.blank()
    s.para("工资卡开户行：招商银行上海徐汇支行", indent=0)
    s.para("卡号：6225 8801 2345 6789", indent=0)
    s.case("R-1", "简历/姓名", "姓名：李秀英", secrets=["李秀英"])
    s.case("R-2", "简历/性别年龄", "性别：女 年龄：32 岁", secrets=["32"])
    s.case("R-3", "简历/生日", "出生日期：1994 年 3 月 8 日", secrets=["1994年3月8日"])
    s.case("R-4", "简历/手机", "手机：139-1111-2222", secrets=["13911112222"])
    s.case("R-5", "简历/邮箱", "lixiuying94@example.com.cn", secrets=["lixiuying94@example.com.cn"])
    s.case("R-6", "简历/地址", "上海市徐汇区漕溪北路 398 号 3 号楼 1502 室",
           secrets=["漕溪北路398号"])
    s.case("R-7", "简历/身份证", "身份证号：320106199403081234", secrets=["320106199403081234"])
    s.case("R-8", "简历/联系人", "紧急联系人：张伟", secrets=["张伟"])
    s.case("R-9", "简历/联系人电话", "137-3333-4444", secrets=["13733334444"])
    s.case("R-10", "简历/银行卡", "6225 8801 2345 6789", secrets=["6225880123456789"])
    s.case("R-N1", "简历/干扰", "2012 年 9 月至 2016 年 6 月", noise=["2012", "2016"])
    s.case("R-N2", "简历/干扰", "月薪 18000 元", noise=["18000"])
    return s


def sheet_contract():
    s = Sheet("房屋租赁合同", dpi=280, angle=0.9)
    s.head("房屋租赁合同（节选）")
    s.blank()
    s.para("出租方（甲方）：王建国，身份证号 310104197805123456，")
    s.para("联系电话 138 0013 8000，通讯地址 上海市黄浦区南京东路 100 号 802 室。")
    s.blank()
    s.para("承租方（乙方）：陈晓雯，身份证号 310105199611204321，")
    s.para("联系电话 137-6666-8888，电子邮箱 chenxw1996@mail.example.com。")
    s.blank()
    s.para("第一条　房屋坐落于上海市徐汇区漕溪北路 398 号 3 号楼 1502 室，")
    s.para("建筑面积 89.6 平方米，月租金人民币 8500 元整，押金 17000 元。")
    s.para("第二条　租金由乙方于每月 5 日前转入甲方账户，")
    s.para("开户行：中国工商银行上海分行，账号 6222 0210 0112 3456 789。")
    s.para("第三条　租赁期限自 2026 年 1 月 1 日起至 2026 年 12 月 31 日止。")
    s.blank()
    s.para("甲方签字：王建国　　乙方签字：陈晓雯　　签订日期：2025 年 12 月 20 日")
    s.case("C-1", "合同/甲方姓名", "出租方（甲方）：王建国", secrets=["王建国"])
    s.case("C-2", "合同/甲方身份证", "310104197805123456", secrets=["310104197805123456"])
    s.case("C-3", "合同/甲方手机", "138 0013 8000", secrets=["13800138000"])
    s.case("C-4", "合同/甲方地址", "上海市黄浦区南京东路 100 号 802 室", secrets=["南京东路100号"])
    s.case("C-5", "合同/乙方姓名", "承租方（乙方）：陈晓雯", secrets=["陈晓雯"])
    s.case("C-6", "合同/乙方身份证", "310105199611204321", secrets=["310105199611204321"])
    s.case("C-7", "合同/乙方手机", "137-6666-8888", secrets=["13766668888"])
    s.case("C-8", "合同/乙方邮箱", "chenxw1996@mail.example.com", secrets=["chenxw1996@mail.example.com"])
    s.case("C-9", "合同/收款卡", "6222 0210 0112 3456 789", secrets=["6222021001123456789"])
    s.case("C-N1", "合同/干扰", "月租金人民币 8500 元整", noise=["8500"])
    s.case("C-N2", "合同/干扰", "建筑面积 89.6 平方米", noise=["89.6"])
    s.case("C-N3", "合同/干扰", "2026 年 12 月 31 日", noise=["2026"])
    return s


def sheet_medical():
    s = Sheet("门诊病历", dpi=300, angle=0.4)
    s.head("门诊病历首页")
    s.blank()
    s.para("就诊卡号：MZ2026111400386　　就诊日期：2026 年 11 月 14 日")
    s.para("姓名：张国强　　性别：男　　年龄：58 岁　　出生日期：1968-04-12")
    s.para("联系电话：(021) 6432-8899　　手机：13900139000")
    s.para("家庭住址：上海市长宁区延安西路 1088 号 6 号楼 302 室")
    s.para("身份证号：310110196804125678　　医保卡号：YB310110196804125678")
    s.blank()
    s.para("主诉：反复胸闷 3 月余，加重 1 周。")
    s.para("现病史：患者 3 月前无明显诱因出现胸闷，多于活动后发作，持续数分钟，")
    s.para("休息后可缓解。近 1 周发作频繁，每日 2 至 3 次。")
    s.para("既往史：高血压病史 8 年，长期口服氨氯地平 5mg 每日一次，血压控制在")
    s.para("130/85 mmHg 左右。否认糖尿病、肝炎及结核病史。")
    s.blank()
    s.para("体格检查：体温 36.5 摄氏度，脉搏 78 次每分，血压 138/86 mmHg。")
    s.para("辅助检查：心电图示窦性心律，ST 段轻度压低。")
    s.blank()
    s.para("初步诊断：冠状动脉粥样硬化性心脏病待排；原发性高血压 2 级。")
    s.para("处理意见：完善心脏彩超与运动平板试验，两周后门诊复诊。")
    s.blank()
    s.para("接诊医师：刘敏　　科室：心血管内科　　门诊楼 3 层 306 诊室")
    s.case("M-1", "病历/姓名", "姓名：张国强", secrets=["张国强"])
    s.case("M-2", "病历/生日", "出生日期：1968-04-12", secrets=["19680412"])
    s.case("M-3", "病历/座机", "(021) 6432-8899", secrets=["02164328899"])
    s.case("M-4", "病历/手机", "手机：13900139000", secrets=["13900139000"])
    s.case("M-5", "病历/地址", "上海市长宁区延安西路 1088 号 6 号楼 302 室", secrets=["延安西路1088号"])
    s.case("M-6", "病历/身份证", "310110196804125678", secrets=["310110196804125678"])
    s.case("M-7", "病历/年龄", "年龄：58 岁", secrets=["58"])
    s.case("M-N1", "病历/干扰", "体温 36.5 摄氏度", noise=["36.5"])
    s.case("M-N2", "病历/干扰", "血压 138/86", noise=["138/86"])
    s.case("M-N3", "病历/干扰", "口服氨氯地平 5mg", noise=["5mg"])
    return s


def sheet_bank():
    s = Sheet("银行对账单", dpi=280, angle=1.1)
    s.head("个人账户对账单")
    s.blank()
    s.para("户名：周文斌　　账号：6217 0012 3456 7890 123")
    s.para("开户网点：中国建设银行上海静安支行　　对账期间：2026 年 10 月 1 日至 10 月 31 日")
    s.para("预留手机：13655556666　　电子邮箱：zhouwb@example.org")
    s.para("通讯地址：上海市静安区南京西路 1601 号 1808 室")
    s.blank()
    s.para("交易明细：")
    s.para("10 月 3 日　工资代发　入账　18500.00　余额 42310.55")
    s.para("10 月 8 日　房租转账　出账　8500.00　余额 33810.55")
    s.para("10 月 12 日　水费代扣　出账　86.40　余额 33724.15")
    s.para("10 月 19 日　消费　出账　1280.00　余额 32444.15")
    s.para("10 月 26 日　跨行转入　入账　3000.00　余额 35444.15")
    s.blank()
    s.para("合计：入账 21500.00 元，出账 9866.40 元。")
    s.para("如有疑问请致电客户经理 021-5566-7788 转 8021，或拨打预留手机。")
    s.blank()
    s.para("打印时间：2026 年 11 月 2 日 09:41:07　　流水号 202611020000381")
    s.case("B-1", "对账单/户名", "户名：周文斌", secrets=["周文斌"])
    s.case("B-2", "对账单/卡号", "6217 0012 3456 7890 123", secrets=["6217001234567890123"])
    s.case("B-3", "对账单/手机", "预留手机：13655556666", secrets=["13655556666"])
    s.case("B-4", "对账单/邮箱", "zhouwb@example.org", secrets=["zhouwb@example.org"])
    s.case("B-5", "对账单/地址", "上海市静安区南京西路 1601 号 1808 室", secrets=["南京西路1601号"])
    s.case("B-N1", "对账单/干扰", "余额 42310.55", noise=["42310.55"])
    s.case("B-N2", "对账单/干扰", "入账 18500.00", noise=["18500.00"])
    s.case("B-N3", "对账单/干扰", "流水号 202611020000381", noise=["202611020000381"])
    # 座机一律打码（含单位总机）是有意为之：宁可多糊一块，也不靠「这是不是私人号码」去猜。
    # 所以这一条不列进 noise，只在报告里留作观察项。
    return s


def sheet_waybill():
    s = Sheet("快递面单", dpi=220, angle=0.3)   # 面单字号大、分辨率低
    s.head("电子面单")
    s.blank()
    s.para("运单号：SF1234567890123", size=13)
    s.para("收件人：赵敏　　手机：13700001111", size=13)
    s.para("收件地址：浙江省杭州市西湖区文三路 259 号 7 幢 402 室", size=13)
    s.blank()
    s.para("寄件人：孙丽华　　手机：15900002222", size=12)
    s.para("寄件地址：江苏省南京市鼓楼区中山北路 200 号 2 单元 601 室", size=12)
    s.blank()
    s.para("内件：文件　　数量：1　　计费重量：0.5 千克　　运费：18.00 元")
    s.para("下单时间：2026 年 11 月 13 日 20:15:33")
    s.blank()
    s.para("派件员：吴强　　工号 8823　　联系电话 13511113333")
    s.case("W-1", "面单/收件人", "收件人：赵敏", secrets=["赵敏"])
    s.case("W-2", "面单/收件人手机", "手机：13700001111", secrets=["13700001111"])
    s.case("W-3", "面单/收件地址", "浙江省杭州市西湖区文三路 259 号 7 幢 402 室",
           secrets=["文三路259号"])
    s.case("W-4", "面单/寄件人", "寄件人：孙丽华", secrets=["孙丽华"])
    s.case("W-5", "面单/寄件人手机", "手机：15900002222", secrets=["15900002222"])
    s.case("W-6", "面单/寄件地址", "江苏省南京市鼓楼区中山北路 200 号 2 单元 601 室",
           secrets=["中山北路200号"])
    s.case("W-7", "面单/派件员", "派件员：吴强", secrets=["吴强"])
    s.case("W-8", "面单/派件员电话", "联系电话 13511113333", secrets=["13511113333"])
    s.case("W-N1", "面单/干扰", "运单号：SF1234567890123", noise=["SF1234567890123"])
    s.case("W-N2", "面单/干扰", "运费：18.00 元", noise=["18.00"])
    return s


def sheet_notice():
    s = Sheet("会议通知", dpi=260, angle=0.7)
    s.head("关于召开年度供应商大会的通知")
    s.blank()
    s.para("各有关单位：")
    s.para("　　定于 2026 年 12 月 3 日上午 9 时，在上海市浦东新区世纪大道 1 号")
    s.para("国际会议中心 2 层多功能厅召开年度供应商大会，会期一天。")
    s.blank()
    s.para("　　会务联系人：何静，手机 13866668888，座机 021-5888-1234，")
    s.para("邮箱 hejing@example.net。")
    s.para("　　材料接收人：郑海涛，手机 13977775555，")
    s.para("地址 上海市浦东新区世纪大道 1 号国际会议中心 B 座 1806 室。")
    s.blank()
    s.para("　　请参会单位于 11 月 28 日前将回执发送至会务邮箱，逾期视为放弃。")
    s.para("　　联系人：何静（13866668888）")
    s.blank()
    s.para("　　　　　　　　　　　　　　主办单位：华东供应链管理协会")
    s.para("　　　　　　　　　　　　　　2026 年 11 月 10 日")
    s.case("N-1", "通知/联系人", "会务联系人：何静", secrets=["何静"])
    s.case("N-2", "通知/手机", "手机 13866668888", secrets=["13866668888"])
    s.case("N-3", "通知/座机", "座机 021-5888-1234", secrets=["02158881234"])
    s.case("N-4", "通知/邮箱", "hejing@example.net", secrets=["hejing@example.net"])
    s.case("N-5", "通知/第二联系人", "材料接收人：郑海涛", secrets=["郑海涛"])
    s.case("N-6", "通知/第二手机", "手机 13977775555", secrets=["13977775555"])
    s.case("N-N1", "通知/干扰", "2026 年 12 月 3 日上午 9 时", noise=["9 时"])
    s.case("N-N2", "通知/干扰", "国际会议中心 2 层多功能厅", noise=["2 层"])
    return s


def sheet_claim():
    s = Sheet("保险理赔申请", dpi=280, angle=0.8)
    s.head("人身保险理赔申请书")
    s.blank()
    s.para("保单号：P2025000123456　　报案号：BA2026111400088")
    s.para("被保险人：林志强　　性别：男　　出生日期：1985 年 7 月 19 日　　年龄 41 岁")
    s.para("身份证号：350102198507192345　　手机号码：13612345678")
    s.para("现住址：福建省福州市鼓楼区五四路 128 号 3 座 1101 室")
    s.para("电子邮箱：linzq1985@example.com")
    s.blank()
    s.para("受益人：林小雨，与被保险人关系：子女，联系电话 13787654321。")
    s.para("理赔款接收账户：")
    s.para("开户行 中国银行福州分行营业部，账号 6217 8888 0011 2233 445")
    s.blank()
    s.para("事故经过：2026 年 10 月 21 日 18 时 30 分许，被保险人骑行电动车")
    s.para("途经福州市鼓楼区五四路与湖东路交叉口时与机动车发生碰撞，")
    s.para("经福州协和医院诊断为左侧胫骨骨折，住院 12 天，医疗费用共计 38650.00 元。")
    s.blank()
    s.para("申请人签字：林志强　　申请日期：2026 年 11 月 14 日")
    s.case("L-1", "理赔/被保险人", "被保险人：林志强", secrets=["林志强"])
    s.case("L-2", "理赔/生日", "出生日期：1985 年 7 月 19 日", secrets=["1985年7月19日"])
    s.case("L-3", "理赔/年龄", "年龄 41 岁", secrets=["41"])
    s.case("L-4", "理赔/身份证", "350102198507192345", secrets=["350102198507192345"])
    s.case("L-5", "理赔/手机", "手机号码：13612345678", secrets=["13612345678"])
    s.case("L-6", "理赔/地址", "福建省福州市鼓楼区五四路 128 号 3 座 1101 室", secrets=["五四路128号"])
    s.case("L-7", "理赔/邮箱", "linzq1985@example.com", secrets=["linzq1985@example.com"])
    s.case("L-8", "理赔/受益人", "受益人：林小雨", secrets=["林小雨"])
    s.case("L-9", "理赔/受益人电话", "13787654321", secrets=["13787654321"])
    s.case("L-10", "理赔/银行卡", "6217 8888 0011 2233 445", secrets=["6217888800112233445"])
    s.case("L-N1", "理赔/干扰", "医疗费用共计 38650.00 元", noise=["38650.00"])
    s.case("L-N2", "理赔/干扰", "住院 12 天", noise=["12 天"])
    return s


def sheet_school():
    s = Sheet("学生家长信息登记", dpi=300, angle=1.2)
    s.head("学生及家长信息登记表（文字说明）")
    s.blank()
    s.para("学生姓名：王梓涵　　性别：女　　出生日期：2016 年 9 月 2 日　　年级：四年级")
    s.para("学籍号：G310104201609020123　　班级：四年级 3 班")
    s.blank()
    s.para("父亲：王建军，身份证号 310104198203154567，手机 13812345678，")
    s.para("工作单位：上海某建筑设计院，邮箱 wangjj@example.cn。")
    s.para("母亲：刘晓燕，身份证号 310104198506227890，手机 13987654321，")
    s.para("工作单位：上海某三甲医院，邮箱 liuxy@example.cn。")
    s.blank()
    s.para("家庭住址：上海市徐汇区田林路 88 弄 12 号 501 室")
    s.para("紧急联系地址：上海市闵行区莘庄镇莘松路 200 号 3 号楼 202 室（外婆家）")
    s.blank()
    s.para("接送人：王建军（父亲），联系电话 13812345678。")
    s.para("备注：学生有轻度花粉过敏，请老师留意。")
    s.case("S-1", "家校/学生姓名", "学生姓名：王梓涵", secrets=["王梓涵"])
    s.case("S-2", "家校/学生生日", "出生日期：2016 年 9 月 2 日", secrets=["2016年9月2日"])
    s.case("S-3", "家校/父亲", "父亲：王建军", secrets=["王建军"])
    s.case("S-4", "家校/父亲身份证", "310104198203154567", secrets=["310104198203154567"])
    s.case("S-5", "家校/父亲手机", "手机 13812345678", secrets=["13812345678"])
    s.case("S-6", "家校/父亲邮箱", "wangjj@example.cn", secrets=["wangjj@example.cn"])
    s.case("S-7", "家校/母亲", "母亲：刘晓燕", secrets=["刘晓燕"])
    s.case("S-8", "家校/母亲身份证", "310104198506227890", secrets=["310104198506227890"])
    s.case("S-9", "家校/母亲手机", "手机 13987654321", secrets=["13987654321"])
    s.case("S-10", "家校/母亲邮箱", "liuxy@example.cn", secrets=["liuxy@example.cn"])
    s.case("S-11", "家校/住址", "上海市徐汇区田林路 88 弄 12 号 501 室", secrets=["田林路88弄"])
    s.case("S-12", "家校/紧急地址", "上海市闵行区莘庄镇莘松路 200 号 3 号楼 202 室",
           secrets=["莘松路200号"])
    s.case("S-N1", "家校/干扰", "学籍号：G310104201609020123", noise=["G310104201609020123"])
    s.case("S-N2", "家校/干扰", "四年级 3 班", noise=["3 班"])
    return s


SHEETS = [sheet_resume, sheet_contract, sheet_medical, sheet_bank,
          sheet_waybill, sheet_notice, sheet_claim, sheet_school]


def render_sheet(sheet, path_png):
    """把一页文字排进 PDF，再渲染成带噪点的灰度扫描图"""
    doc = pymupdf.open()
    page = doc.new_page(width=A4.width, height=A4.height)
    ff = FF
    if ff:
        page.insert_font(fontname="F0", fontfile=ff)
    y = MARGIN + 16
    for text, size, bold, indent in sheet.lines:
        if text:
            page.insert_text((MARGIN + indent, y), text,
                             fontname="F0" if ff else "china-s", fontsize=size,
                             color=(0, 0, 0) if bold else (0.08, 0.08, 0.08))
        y += LEAD + (4 if size > 12 else 0)
    pix = page.get_pixmap(dpi=sheet.dpi, colorspace=pymupdf.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    doc.close()

    # 轻微倾斜 + 噪点 + 不均匀光照 + JPEG 压缩，模拟真实扫描
    import io
    import numpy as np
    rnd = np.random.default_rng(sheet.dpi)
    if sheet.angle:
        img = img.rotate(sheet.angle, resample=Image.BICUBIC, expand=False,
                         fillcolor=255)
    a = np.asarray(img, dtype=np.float32)
    h, w = a.shape
    # 光照不均：中间亮、上下略暗，再叠一点横向条纹
    grad = 1.0 - 0.06 * np.abs(np.arange(h)[:, None] - h / 2.0) / h
    grad = grad - 0.015 * (np.sin(np.arange(w)[None, :] / 37.0) > 0.9)
    a = a * grad
    a = a + rnd.normal(0, 3.5, size=a.shape)
    a = np.clip(a, 0, 255).astype(np.uint8)
    img = Image.fromarray(a, "L")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=84)
    with open(path_png, "wb") as f:
        f.write(buf.getvalue())
    return buf.getvalue()


def build(name="刁难文档4_扫描件.pdf"):
    os.makedirs(OUT_DIR, exist_ok=True)
    out_pdf = os.path.join(OUT_DIR, name)
    truth = os.path.join(OUT_DIR, os.path.splitext(name)[0] + ".truth.json")
    tmp = os.path.join(OUT_DIR, "_tmp_scan.jpg")

    out = pymupdf.open()
    all_cases = []
    for i, maker in enumerate(SHEETS, 1):
        sheet = maker()
        jpg = render_sheet(sheet, tmp)
        page = out.new_page(width=A4.width, height=A4.height)
        page.insert_image(pymupdf.Rect(0, 0, A4.width, A4.height), stream=jpg)
        for c in sheet.cases:
            c["page"] = i
            c["sheet"] = sheet.title
            all_cases.append(c)
        print("  P%d %-12s %d 行 · 真值 %d 条" % (i, sheet.title,
                                                 len(sheet.lines), len(sheet.cases)))
    out.insert_pdf(out, from_page=0, to_page=0) if False else None
    out.set_metadata({"title": "刁难文档 4.0 扫描件", "author": "dev/make_hard4_pdf.py",
                      "subject": "scanned adversarial sample", "keywords": "test"})
    out.save(out_pdf, deflate=True, garbage=3)
    out.close()
    os.path.isfile(tmp) and os.remove(tmp)

    with open(truth, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"source": name, "pages": len(SHEETS), "count": len(all_cases),
                   "note": "扫描件：整页为图片，无文字层；秘密项必须在打码后不可提取",
                   "cases": all_cases}, f, ensure_ascii=False, indent=1)

    must = [c for c in all_cases if c["level"] == "must"]
    print("已生成：%s（%d 页，%d 条真值，其中 must %d 条）"
          % (out_pdf, len(SHEETS), len(all_cases), len(must)))
    if not FF:
        print("  [注意] 未找到中英混排字体，内置字体可能把 ASCII 画成全角，量出来会失真")
    return out_pdf, truth


def main():
    build(sys.argv[1] if len(sys.argv) > 1 else "刁难文档4_扫描件.pdf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
