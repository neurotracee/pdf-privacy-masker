# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 项目创作时为初中生
#
# This file is part of PDF 隐私打码工具 (PDF Privacy Masker).
#
# PDF 隐私打码工具 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.  You should have received a copy of the license along with this
# program.  If not, see <https://www.gnu.org/licenses/>.
#
# ---------------------------------------------------------------------------
# 附加条款（AGPL-3.0 第 7 条 b 项）· Additional terms
#
# 二次开发或商用必须保留下列内容，详见 ADDITIONAL-TERMS.md：
#   1. 作者署名：指导作者「项目创作时为初中生」 / 由 腾讯 WorkBuddy × DeepSeek-V4.1-Flash 开发
#   2. 原项目地址，且必须让使用者看得见（「关于」窗口 / 页脚 / --about 输出）
#   3. 修改过的版本必须注明「本程序基于 <原项目地址> 修改，非原作者发布」
# 程序名称「PDF 隐私打码工具」与图标不在授权范围内（AGPL-3.0 第 7 条 e 项）。
# ---------------------------------------------------------------------------
"""
PDF 隐私打码工具  (本地离线 · 单文件运行)

- 自动识别：手机号 / 身份证号 / 银行卡号 / 邮箱 / 姓名 / 座机号 / 地址 / 出生日期 / 性别 / 年龄
- 姓名保留姓氏，仅打码名字
- 带「出生 / 生日」语义的日期打码，普通会议、合同日期不打码
- 真马赛克：像素级重采样，字形不可还原，同时抹除底层文本层
- 全程本机处理，不联网、不上传；输出新文件，原文件不动

作者 / Authors
-------------
指导作者  : 项目创作时为初中生 —— 需求、识别规则的设计、验收测试全部由本人完成
            维护频率很低（作者时间精力有限，约一两个月看一次），欢迎任何人 fork 改进
开发      : 腾讯 WorkBuddy × DeepSeek-V4.1-Flash（在指导作者的指令与验收下实现）

许可 / License
--------------
GNU Affero General Public License v3.0 or later（AGPL-3.0-or-later）
可自由使用、修改、再分发，也可商用；但分发（含打包后的 exe）或把修改版
作为网络服务提供时，必须同时公开完整源代码，并保留原作者署名。
详见 LICENSE 文件。
"""

import io
import json
import os
import random
import re
import sys
import threading
import time
import uuid

import pymupdf
from PIL import Image

from thanks_asset import QR_PNG_B64  # 赞赏码图片（base64 内嵌，单文件打包不丢）

APP_NAME = "PDF 隐私打码工具"
VERSION = "1.4.1"

# ---- 署名信息（开源后请勿删除，AGPL-3.0 第 5 条要求保留版权声明） ----
AUTHOR = "项目创作时为初中生"
AUTHOR_ROLE = "项目指导作者"
DEVELOPER = "腾讯 WorkBuddy × DeepSeek-V4.1-Flash"
LICENSE_NAME = "AGPL-3.0-or-later"
PROJECT_URL = "https://github.com/neurotracee/pdf-privacy-masker"

# ---- 检查更新（只读一个版本号，不上传任何本地内容） ----
RELEASES_URL = PROJECT_URL + "/releases/latest"
RELEASES_API = "https://api.github.com/repos/neurotracee/pdf-privacy-masker/releases?per_page=20"
UPDATE_ASSET_SUFFIX = ".exe"          # 这个平台看 .exe 资产
UPDATE_TIMEOUT = 8                    # 秒，超时就当失败，界面自己给兜底

CREDIT_LINE = "指导作者：%s · 由 %s 开发 · %s 开源" % (
    AUTHOR, DEVELOPER, LICENSE_NAME)

# ---- 附加条款（AGPL-3.0 第 7 条 b 项）：二次开发 / 商用必须标注原项目地址 ----
# 这几行会出现在首页页脚、「关于」窗口和 --about 输出里，删掉即违反附加条款。
URL_SHORT = PROJECT_URL.replace("https://", "").replace("http://", "")
ATTRIB_NOTICE = ("二次开发或商用必须保留作者署名，并在程序中标注原项目地址：%s"
                 % PROJECT_URL)
FORK_NOTICE = ("本程序基于 %s 修改，非原作者发布。" % PROJECT_URL)

# ---- 用户设置（保存位置等）存到 %APPDATA%\PDF隐私打码工具\settings.json ----
SETTINGS_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), "PDF隐私打码工具")
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.json")

# saveDir    : 默认保存目录（空 = 跟随原 PDF 所在目录，临时文件则为「下载」）
# rememberDir: 记住上一次选择的目录，下次作为默认值
# noAsk      : 不再每次都问，直接存到 saveDir
# lang       : 界面语言 zh / en
DEFAULT_SETTINGS = {"saveDir": "", "rememberDir": True, "noAsk": False, "lang": "zh"}


def _L(zh, en):
    """后端要回给界面的提示，按当前语言选一条"""
    try:
        return en if _get_settings().get("lang") == "en" else zh
    except Exception:
        return zh


# 马赛克渲染倍率：4 倍 ≈ 288 DPI，放大后仍是清晰方块
MOSAIC_ZOOM = 4.0

# ---------------------------------------------------------------------------
# 词表
# ---------------------------------------------------------------------------

SURNAME_1 = (
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
    "常温康施文牛樊葛邢安齐易乔伍庞颜倪庄聂章鲁岳翟殷詹申欧耿关兰焦俞左柳甘祝包宁尚符舒阮柯纪梅童凌毕单季裴霍涂成苗谷盛曲翁冉骆蓝路游辛靳管柴蒙鲍华喻祁蒲房滕屈饶解牟艾尤阳时穆农司卓古吉缪简车项连芦麦褚娄窦戚岑景"
)
COMPOUND_SURNAME = [
    "欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙", "慕容", "长孙",
    "宇文", "司徒", "夏侯", "令狐", "独孤", "南宫", "西门", "百里", "钟离", "轩辕",
]

# 非姓名的常见词，避免「地址」「性别」等被当成人名
NAME_STOP = set("""
姓名 名字 性别 年龄 民族 籍贯 住址 地址 电话 手机 邮箱 邮箱 单位 部门 职务 职位 学历 本科 硕士 博士 专科
高中 初中 已婚 未婚 离异 丧偶 男 女 先生 女士 同志 客户 本人 本人 签字 签名 盖章 日期 备注 编号 序号
中国 北京 上海 天津 重庆 广东 江苏 浙江 山东 河南 河北 湖南 湖北 四川 福建 安徽 江西 陕西 山西 云南
贵州 广西 海南 辽宁 吉林 黑龙 内蒙 甘肃 青海 宁夏 新疆 西藏 香港 澳门 台湾 省市 区县 街道 社区 小区
开户 银行 支行 分行 公司 集团 有限 责任 股份 中心 学校 大学 学院 医院 机构 机关 事业 企业 工厂 商店
身份 证件 号码 联系 紧急 关系 父亲 母亲 配偶 子女 兄弟 姐妹 以上 以下 如下 签字 确认 承诺 本人 声明
合计 总计 小计 金额 人民币 元整 现金 转账 支付 票据 合同 协议 附件 页码 共页 第页 内容 项目 名称 型号
程序 办法 方式 期间 部门 单位 情况 标准 规范 要求 说明 系统 记录 数据 信息 文件 材料 流程 规定 制度 格式
办法 事项 工作 业务 服务 产品 技术 管理 安全 质量 效率 成本 费用 时间 地点 原因 结果 问题 方案 计划 报告
""".split())

# 全局标签词表：用于截断「值」的边界
LABEL_WORDS = [
    "姓名", "名字", "曾用名", "性别", "年龄", "民族", "籍贯", "出生日期", "出生年月日", "出生年月",
    "生日", "出生地", "身份证号码", "身份证号", "身份证件号", "证件号码", "证件号", "证件类型",
    "手机号码", "手机号", "手机", "联系电话", "电话", "座机", "固话", "办公电话", "传真",
    "电子邮箱", "邮箱", "Email", "E-mail", "地址", "住址", "现住址", "家庭住址", "通讯地址",
    "联系地址", "单位地址", "邮寄地址", "收货地址", "户籍地址", "注册地址", "办公地址", "居住地址",
    "邮编", "邮政编码", "银行卡号", "卡号", "账号", "开户行", "开户银行", "开户名称", "户名",
    "工作单位", "单位", "职务", "职位", "部门", "岗位", "学历", "学位", "婚姻状况", "婚否",
    "紧急联系人", "联系人", "关系", "与本人关系", "备注", "签名", "签字", "日期", "填表日期",
    "入职日期", "合同编号", "编号", "序号", "金额", "大写", "小写",
    "收件人", "签收人", "核验人", "审核人", "经办人", "授权人", "委托人", "代理人", "证明人",
    "见证人", "收款人", "付款人", "开户名", "配偶", "父亲", "母亲", "子女", "家属",
]
LABEL_ALT = "|".join(sorted((re.escape(w) for w in LABEL_WORDS), key=len, reverse=True))
RE_ANY_LABEL = re.compile("(?:%s)" % LABEL_ALT, re.I)

# 日期
DATE_BODY = r"[0-9]{4}\s*[年\-/\.]\s*[0-9]{1,2}\s*[月\-/\.]\s*[0-9]{1,2}\s*日?"
RE_ANY_DATE = re.compile(DATE_BODY)
RE_BIRTH_LABEL = re.compile(
    r"(?:出生日期|出生年月日|出生年月|出生地|生\s*日|出\s*生|生于|DOB|Date\s*of\s*Birth)\s*"
    r"(?:是|为|于)?\s*[:：]?\s*"
    r"(%s|[0-9]{8})" % DATE_BODY,
    re.I,
)
# 明确属于「出生」语境的关键词（仅用于判断日期是否打码）
BIRTH_CTX = re.compile(r"(出生|生日|生于|诞辰|DOB|birth)", re.I)

RE_MOBILE = re.compile(r"(?<![0-9])1[3-9][0-9]{9}(?![0-9])")
RE_MOBILE_SEP = re.compile(r"(?<![0-9])1[3-9][0-9][\s\-][0-9]{4}[\s\-][0-9]{4}(?![0-9])")
RE_TEL = re.compile(r"(?<![0-9\-])0[0-9]{2,3}[\-\s]?[0-9]{7,8}(?:[\-转][0-9]{1,6})?(?![0-9])")
RE_TEL_LABEL = re.compile(r"(?:座机|固话|办公电话|联系电话|电话|传真|Tel|TEL)\s*[:：]?\s*([0-9][0-9\-\s\(\)]{6,20})")
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
RE_ID18 = re.compile(r"(?<![0-9A-Za-z])[0-9]{17}[0-9Xx](?![0-9A-Za-z])")
RE_ID15 = re.compile(r"(?<![0-9A-Za-z])[0-9]{15}(?![0-9A-Za-z])")
RE_BANK = re.compile(r"(?<![0-9])[0-9]{16,19}(?![0-9])")

# 校验位/校验和不过时的兜底：字段名明确就照打（应对 OCR 错一位）
RE_ID_LABEL_FB = re.compile(
    r"(?:身份证|公民身份号码|证件号|证件号码|证号|ID\s*No)\s*[:：]?\s*"
    r"([0-9]{17}[0-9Xx]|[0-9]{15})"
)
RE_BANK_LABEL_FB = re.compile(
    r"(?:银行卡号|卡\s*号|账\s*号|账号|账户号)\s*[:：]?\s*([0-9]{16,19})"
)

RE_NAME_LABEL = re.compile(
    r"(?:姓\s*名|名\s*字|申请人|联系人|客户姓名|被保险人|投保人|持卡人|户\s*名|开户名|收件人|签收人|"
    r"员工姓名|本人姓名|签字人|经办人|授权人|委托人|代理人|核验人|审核人|证明人|见证人|收款人|"
    r"配偶|父亲|母亲)\s*[:：]?\s*"
    r"([\u4e00-\u9fa5·]{2,8})"
)
RE_NAME_HONOR = re.compile(r"([\u4e00-\u9fa5·]{2,4})(?=先生|女士|同学|老师|经理|总监)")
# 「本人某某，」「我叫某某。」这类无标签自指姓名
RE_NAME_SELF = re.compile(
    r"(?:本人|我\s*叫|申请人|甲方|乙方|丙方|借款人|出借人|出租人|承租人)\s*([\u4e00-\u9fa5·]{2,4})"
    r"(?=[，,。、；;：:\s（）()]|$)"
)
RE_NAME_SIGN = re.compile(r"(?:签名|签字|盖章)\s*[:：]?\s*([\u4e00-\u9fa5·]{2,4})")
# 无标签、无表头、无称谓的人名：姓名 + 后接人做的事（言说/动作/时间状语）。
# 刻意只认「后接动词或时间词」，不认标点，避免把「徐家汇。」「王府井，」当地名吃掉。
RE_NAME_BARE = re.compile(
    r"(?:^|(?<=[，,。、；;：:（()！？\s的是了和与跟由对把被让给从]))([\u4e00-\u9fa5]{2,3})"
    r"(?=今天|今年|昨天|明年|说|表示|称|告诉|提到|认为|觉得|问|答|"
    r"拎|带|拿|提|走|来|去|打|找|笑|坐|站|给|让|向|把|被|在|"
    r"整理|核对|负责|提交|填写|签字|确认|主持|汇报|参加|出示|介绍|审核|审批|"
    r"办理|操作|到场|陪同|记录|统计|经手|承办|接收|递交|"
    r"已经|正在|刚|也|还|就|又|都)"
)

# 出生词在日期「之后」的写法：1992年7月18日出生 / 本人生于… / 1992年07月18日生
RE_BIRTH_SUFFIX = re.compile(
    r"(%s)\s*(?:出\s*生|诞\s*辰|生(?!\s*效|产|育|成|还|活))" % DATE_BODY
)

# 人名枚举：「张三、李四、王五三个人」「张三和王五」
RE_NAME_LIST = re.compile(
    r"(?<![\u4e00-\u9fa5、])([\u4e00-\u9fa5]{2,3}(?:、[\u4e00-\u9fa5]{2,3}){1,8})"
)
RE_NAME_CONJ = re.compile(
    r"([\u4e00-\u9fa5]{2,3})(?:和|与|跟)([\u4e00-\u9fa5]{2,3})"
)
# 「同行的某某」「随行的某某」「另一位某某」这类带引入语的人名
RE_NAME_CTX = re.compile(
    r"(?:同行|随行|同组|同事|另一位|另外一位|名叫|名为|叫做|分别是|包括|带着|由)\s*的?\s*"
    r"([\u4e00-\u9fa5·]{2,3})"
)

# ---------------------------------------------------------------------------
# 名字常用字表：纯叙述文本里没有「姓名：」这种标签，也没法靠后面的词穷举，
# 就把「姓氏之后的字必须是人名常用字」当成主要判据。
# 刻意剔除了「于/在/的/和/中/国/家/庄/村/山/河/海/城/市/路/街…」这类
# 既是人名用字、又极容易构成地名词尾的字，宁可漏掉个别人名，不误伤正文。
# ---------------------------------------------------------------------------
GIVEN_CHARS = set("""
伟 强 磊 军 勇 杰 涛 明 超 刚 峰 辉 鹏 宇 浩 鑫 斌 波 健 凯 亮 龙 飞 俊 帅 帆 豪 阳 旭
恒 毅 楠 睿 泽 洋 川 康 宁 安 邦 才 昌 畅 朝 辰 晨 成 诚 承 冲 崇 楚 传 春 聪 达 岱 道 德
登 迪 典 鼎 冬 栋 敦 铎 发 凡 芳 菲 斐 丰 锋 逢 凤 福 甫 富 钢 戈 庚 耿 功 冠 光 广 贵 桂
国 晗 涵 寒 翰 航 昊 皓 禾 赫 衡 宏 洪 鸿 厚 桦 怀 欢 焕 晖 徽 惠 慧 吉 纪 佳 嘉 坚 建 洁
捷 金 津 锦 晋 京 晶 敬 静 炯 巨 炬 涓 君 骏 坤 昆 来 岚 朗 雷 蕾 莉 立 丽 利 力 良 琳 玲
凌 铃 灵 璐 露 律 仑 曼 茂 梅 美 萌 蒙 孟 米 苗 妙 民 敏 铭 慕 牧 娜 男 妮 培 佩 平 萍 珀 璞
奇 琪 棋 齐 启 千 茜 倩 乔 巧 钦 勤 青 清 卿 庆 琼 秋 泉 群 然 冉 仁 荣 容 蓉 锐 瑞 若 森 沙
珊 善 尚 绍 申 深 升 胜 晟 诗 石 仕 守 帅 双 顺 硕 思 斯 松 颂 素 穗 泰 桃 陶 天
铁 婷 庭 挺 彤 薇 为 纬 卫 文 雯 稳 希 熙 曦 喜 仙 贤 显 献 祥 翔 肖 笑 心 新 欣 信 星 幸 雄
修 秀 旭 轩 宣 煊 雪 勋 迅 雅 亚 延 研 艳 燕 扬 尧 耀 业 叶 烨 伊 依 仪 怡 宜 义 艺 忆 逸 银
引 英 瑛 颖 影 映 咏 优 悠 友 幼 娱 羽 雨 玉 育 钰 元 源 远 苑 月 玥 岳 悦 越 云 芸 允 运 韵
载 赞 增 展 章 昭 钊 哲 振 镇 正 政 芝 知 志 智 忠 钟 洲 舟 竹 柱 祝 壮 卓 子 紫 宗 祖 佐 愉
恺 锐 祁 楚 楷 楷 曦 瀚 淼 焱 垚 犇 骞 麒 麟 泓 沛 沐 洛 淇 添 湘 湛 灏 炎 煜 炜 炫 煜 珺 琦
瑜 瑾 璟 璇 瑶 玺 玟 玥 珩 睿 祺 禧 筱 笃 箫 缤 绮 维 绵 翔 翀 翼 耘 肜 舒 航 芊 芮 芯 芷 芸
苑 若 茉 茗 荔 莞 菡 萌 萱 葵 蓉 蕊 蕾 藜 虹 蝶 诗 语 诺 谨 谷 丰 豫 贝 贺 超 跃 轶 辰 迎
邦 郁 钰 铮 锋 锡 锦 长 阔 阳 雁 青 靓 韬 顺 颖 风 香 驰 骏 高 鸿 鹏 鹤 黎 默 龄 龙
晓 兰 晴 红 翠 娟 英 华 国 民 志 凤 娥 菊 荷 莲 柳 柏 鹤 鸿 雁 玲 珑 琴 书 墨 韵 律 声 歌
舞 姿 妍 姝 媛 婉 娴 淑 慈 恩 情 意 忠 孝 仁 义 礼 智 信 温 良 恭 俭 谦 逊 敬 慎 勤 朴 诚 实
真 善 妙 优 秀 卓 越 灿 烂 辉 煌 昌 盛 兴 旺 富 贵 寿 喜 庆 吉 祥 瑞 康 泰 稳 久 伟 雄 壮 猛
毅 坚 韧 奋 努 拼 搏 进 取 开 拓 创 新 发 展 腾 翔 跃 奔 驰 骋 航 攀 登 岩 溪 涧 潭 泊 波 涛
潮 汐 霜 雾 霞 霓 雷 电 夏 秋 冬 竹 槐 榕 樟 杉 桐 樱 杏 桃 梨 菱 藕 稻 麦 芽 果 藤 草 苔 笋
珠 银 铜 铁 钢 宝 晶 陶 瓷 绸 缎 绣 纱 丝 绳 结 织 染 绘 雕 塑 铸 锻 磨 镀 涂 装 饰 筑 东
""".split())

# 姓名后面紧跟的字——一句话里人名的下一字，几乎总落在这些「谓语/介词/副词」上
RIGHT_PRED = set("""
于 在 到 向 把 被 让 给 从 和 与 跟 对 为 将 已 才 便 却 就 也 还 都 又 再 先 后 曾 正 刚 仍
未 会 要 想 可 能 需 应 该 不 没 得 是 的 有 去 来 回 进 出 上 下 起 过 打 找 叫 问 答 说 讲
称 谈 提 拿 带 拎 抬 搬 送 接 收 交 发 填 写 签 盖 按 领 取 放 挂 开 关 推 拉 站 坐 走 跑 赶
陪 帮 替 代 介 通 告 联 排 组 负 主 参 办 处 核 审 复 确 同 拒 表 认 觉 反 汇 记 统 整 准 完
递 示 阅 看 查 登 预 等 离 返 前 请 入 调 转 派 落 执 馈 沟 协 配 承 经 受 立 申 顺 另 当 今
昨 明 次 每 此 遂 即 则 惟 愿 肯 敢 愿 会 亦 皆 均 尚 且 或 若 如 由 自 至 往 朝 沿 随 依 靠
牵 率 担 监 督 促 迎 待 候 托 委 命 令 邀 约 拜 访 探 寻 求 供 属 归 涉 抵 达 赴 承 蒙
""".split())

# 人名左侧允许出现的「软边界」：单个字
LEFT_SOFT_CHARS = set("由让给和与跟向对请派邀叫找是的了在都也还就又再才便却已将被从同陪带替帮交送到见知说问据经系")
# 人名左侧允许出现的「软边界」：词
LEFT_SOFT_WORDS = (
    "安排", "委托", "交给", "联系", "通知", "见到", "认识", "包括", "其中", "还有", "后来",
    "随后", "目前", "现在", "另外", "同时", "以及", "分别", "比如", "例如", "一位", "两位",
    "三名", "这名", "那位", "名叫", "叫做", "名为", "夫妻", "同事", "同行", "随行", "朋友",
    "客户", "对方", "双方", "介绍", "推荐", "指派", "派遣", "透过", "关于", "对于", "至于",
    # 真实公文/报告里高频的「动作 + 人」组合
    "代表", "发现", "确认", "任命", "聘请", "邀请", "拜托", "致电", "告知", "转告", "请示",
    "汇报", "呈报", "呈送", "抄送", "送达", "送交", "转交", "交付", "经办", "承办", "主办",
    "协办", "负责", "监督", "检查", "审查", "审批", "核准", "批准", "同意", "支持", "帮助",
    "协助", "配合", "陪同", "跟随", "带领", "转给", "移交", "接手", "跟踪", "跟进", "落实",
    "指派给", "授权", "委派", "代管", "接替", "顶替", "代理", "合作", "对接", "洽商", "沟通",
)

# 「看起来像人名、其实是普通词」的黑名单。词的第二个字往往正好是名字常用字，
# 只靠字表挡不住（白天/高尚/文明/简单/成功…），必须点名排除。
COMMON_WORD_STOP = set("""
高尚 高明 高贵 高级 高效 高原 高温 高压 高手 高大 高深 高强 高层 高档
白天 白色 白菜 白酒 白发 白银 白纸 白杨 白桦 白水
文明 文字 文件 文章 文化 文学 文艺 文雅 文书
安全 安排 安静 安心 安慰 安装 安然 安详
方法 方面 方向 方式 方案 方便 方圆 方才
马上 马虎 马路 马匹 马车
牛奶 牛肉 牛年
江面 江水 江河 江边
林木 林区 林场 林带
石头 石桥 石阶 石壁 石油
黄金 黄河 黄色 黄土 黄昏 黄沙
李子 梨子 桃子 杏子 橘子 柚子 柿子 栗子 瓜子 筷子 杯子 盘子 瓶子 盖子 架子 柜子 椅子
桌子 凳子 箱子 袋子 瓶子 绳子 轮子 珠子 镜子
孙子 孙女 妻子 儿子 女子 男子 孩子
柱子 竹子 叶子 树枝 树根 树干
王子 王国 王室 王府 王宫 王朝 王牌 王后 王冠
包子 毛巾 毛病 毛线 毛衣
田里 田间 田地 田野 田园 田埂
谷子 谷物 谷底
夏天 夏日 夏季
雷达 雷同 雷雨
孔子 孔雀
祝福
关心 关于 关注 关系 关键 关闭 关联 关照
纪律 纪念 纪录 纪要
梅雨 梅花 梅子
凌晨
成功 成本 成分 成员 成品
蓝天 蓝色 蓝图
管道 管理 管辖
蒙古
华丽 华夏 华人 华侨 华语
房子 房间 房屋
阳光 阳台 阳面
农业 农村 农户 农历
卓越
古代 古典 古老 古人
吉祥
简单 简称 简洁 简历 简易
麦子
群众 群体
任何 任务 任何
何时 何况 何必
许多 许可 许久
陆续 陆续
路程 路线
费用 费力 费心
重要 重复 重来
金属 金秋 金鱼
玉石 玉米 玉兰
石榴 石柱
花园 花木
苹果 苗圃 苗木
幸福 幸运 幸好
胜利 胜任
江湖 江山
沙漠 沙子
田地
王牌
石油
礼服 礼貌
贵重 贵宾 贵阳
丰收 丰富
冬季 冬装
秋季 春风 春秋
夏季
常规 常识 常见 常年
温暖 温度 温柔
康复 康乐
齐全 齐心
容易
孔子
毛遂
享受 享用
纪律
商量 商品 商务
商业 商标
周年 周末 周期 周围 周边
周末
账户 账目
订阅 郑重 郑州
""".split())

# 表格表头里的「姓名类」列名：出现在表头上时，该列下方所有短中文名都按姓名处理
NAME_COL_HEADERS = [
    "姓名", "名字", "人员", "人员姓名", "客户", "客户姓名", "员工", "员工姓名", "职工",
    "当事人", "持有人", "户名", "开户名", "联系人", "申请人", "被保险人", "投保人",
    "持卡人", "收件人", "签收人", "患者", "病人", "学生", "成员", "参会人", "经办人",
    "核验人", "审核人", "证明人", "见证人", "收款人", "付款人", "原告", "被告", "签字人",
]

RE_GENDER = re.compile(r"(?:性\s*别|性\s*别)\s*[:：]?\s*([男女])")
RE_GENDER_2 = re.compile(r"^\s*([男女])\s*$")
# 不带「性别」字样的写法：夹在两个逗号之间，后面紧跟年龄或出生年份。
# 「…出生，女，今年30岁」「李四，男，1990年…」都是简历/通报里的常见句式。
RE_GENDER_BARE_1 = re.compile(r"[，,]\s*([男女])\s*[，,]\s*(?:今年)?\s*[0-9]{1,3}\s*(?:岁|周岁)")
RE_GENDER_BARE_2 = re.compile(r"[，,]\s*([男女])\s*[，,]\s*[0-9]{4}\s*[年\-/\.]")
RE_GENDER_BARE_3 = re.compile(r"(?:出生|生\s*于|诞\s*辰)[^。；;，,]{0,30}[，,]\s*([男女])\s*[，,]")
RE_AGE = re.compile(r"(?:年\s*龄)\s*[:：]?\s*([0-9]{1,3})\s*(?:岁|周岁)?")
RE_AGE_2 = re.compile(r"(?<![0-9])([0-9]{1,3})\s*周岁(?![0-9])")
RE_AGE_3 = re.compile(r"(?<![0-9])([0-9]{1,3})\s*岁(?![数])")

RE_ADDR_LABEL = re.compile(
    r"(?:家庭住址|现住址|通讯地址|联系地址|单位地址|邮寄地址|收货地址|户籍地址|注册地址|办公地址|"
    r"居住地址|住\s*址|地\s*址|居住地)\s*[:：]?\s*([^\s]{4,80})"
)
RE_ADDR_FREE = re.compile(
    r"(?:[\u4e00-\u9fa5]{2,8}(?:省|自治区|特别行政区))?[\u4e00-\u9fa5]{2,8}(?:市|自治州|地区)"
    r"[\u4e00-\u9fa5]{1,8}(?:区|县|市|旗)"
    r"[\u4e00-\u9fa5A-Za-z0-9]{1,20}(?:路|街|道|巷|胡同|大道)"
    r"[\u4e00-\u9fa5A-Za-z0-9]{0,12}[0-9]{1,5}\s*(?:号|弄)"
    r"(?:[\u4e00-\u9fa5A-Za-z0-9\-]{0,30})?"
)

TYPE_NAME = {
    "phone": "手机号",
    "idcard": "身份证号",
    "bankcard": "银行卡号",
    "email": "邮箱",
    "name": "姓名",
    "tel": "座机号",
    "address": "地址",
    "birth": "出生日期",
    "gender": "性别",
    "age": "年龄",
    "manual": "手动框选",
}
TYPE_ORDER = ["idcard", "bankcard", "phone", "tel", "email", "address", "name", "birth", "gender", "age", "manual"]


# ---------------------------------------------------------------------------
# 基础校验
# ---------------------------------------------------------------------------

def _id18_ok(s):
    if len(s) != 18:
        return False
    w = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    m = "10X98765432"
    try:
        tot = sum(int(s[i]) * w[i] for i in range(17))
    except ValueError:
        return False
    return m[tot % 11] == s[17].upper()


def _id_plausible(s):
    """结构合理性：省份码 + 出生年月日都在真实范围内

    长数字串里滑动取 18 位时，单靠校验位仍有约 1/11 的误命中，
    加上省份码和日期范围可以把误命中压到极低。
    """
    if len(s) != 18 or not s[:17].isdigit():
        return False
    if s[:2] not in ("11", "12", "13", "14", "15", "21", "22", "23", "31", "32", "33",
                     "34", "35", "36", "37", "41", "42", "43", "44", "45", "46",
                     "50", "51", "52", "53", "54", "61", "62", "63", "64", "65",
                     "71", "81", "82", "91"):
        return False
    y, m, d = int(s[6:10]), int(s[10:12]), int(s[12:14])
    return 1900 <= y <= 2026 and 1 <= m <= 12 and 1 <= d <= 31


def _luhn_ok(s):
    if not s.isdigit():
        return False
    tot, alt = 0, False
    for ch in reversed(s):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        tot += d
        alt = not alt
    return tot % 10 == 0


def _id15_ok(s):
    if len(s) != 15 or not s.isdigit():
        return False
    mm, dd = int(s[8:10]), int(s[10:12])
    return 1 <= mm <= 12 and 1 <= dd <= 31 and s[:2] in ("11", "12", "13", "14", "15", "21", "22", "23", "31",
                                                       "32", "33", "34", "35", "36", "37", "41", "42", "43",
                                                       "44", "45", "46", "50", "51", "52", "53", "54", "61",
                                                       "62", "63", "64", "65", "71", "81", "82", "91")


def _looks_name(word):
    if not word or len(word) < 2 or len(word) > 4:
        return False
    if word in NAME_STOP:
        return False
    if any(c.isdigit() for c in word):
        return False
    if word[0] in COMPOUND_SURNAME and len(word) >= 3:
        return True
    if word[0] not in SURNAME_1:
        return False
    # 明显的地名 / 机构后缀排除
    if word[-1] in "省市区县镇乡村街道路号楼层室栋幢园湖山河桥站厂店铺堂馆院校系部处科室":
        return False
    return True


# ---------------------------------------------------------------------------
# 纯叙述文本里的姓名（无标签、无表头）
# ---------------------------------------------------------------------------

_HAN = "\u4e00"
_HAN_END = "\u9fa5"

# 姓名末字里「极可能是地名/机构尾字」的，一律不当姓名
# 注意：栋/城/江/海 这类既是地名尾字又是常见名用字的，不列入，否则「王栋」会被漏
NAME_TAIL_BAD = set("省市区县镇乡村街道路号楼层室幢园湖山河桥站厂店铺堂馆院校系部处科室庄屯苑府坊里沟湾岛")

# 左侧硬边界：句读、引号括号、空白、数字之后都算「新的一截」
LEFT_HARD = set("，,。、；;：:！？!?（）()【】《》〈〉「」『』“”‘’\"'·—…%& 　\t")


def _is_han(c):
    return _HAN <= c <= _HAN_END


def _scan_names_prose(text):
    """无标签叙述文本里的人名。

    判据组合（三个同时满足才算）：
      1) 左侧是硬边界（标点/空白/数字）或「由、让、安排、通知…」这类引导字词；
      2) 首字是常见姓氏（或复姓），其后 1~2 字全部是名字常用字；
      3) 右边界是人名后常见的谓语字、或标点/数字/结尾。

    与老的 RE_NAME_BARE 相比，不再要求「后面必须出现白名单里的某个词」，
    因此「某某于……」「某某负责……」「某某称……」这类写法不会再漏。
    """
    out = []
    n = len(text)
    if n < 2:
        return out

    def left_ok(p):
        if p <= 0:
            return True
        c = text[p - 1]
        if not _is_han(c):
            return True
        if c in LEFT_HARD or c in LEFT_SOFT_CHARS:
            return True
        if p >= 2 and text[p - 2:p] in LEFT_SOFT_WORDS:
            return True
        return False

    def right_ok(q):
        if q >= n:
            return True
        c = text[q]
        if not _is_han(c):
            return True
        return c in RIGHT_PRED

    p = 0
    while p < n - 1:
        ch = text[p]
        if not _is_han(ch) or ch in NAME_STOP:
            p += 1
            continue
        # 先猜姓氏长度：复姓 2 字，单姓 1 字
        sur = []
        if p + 1 < n and text[p:p + 2] in COMPOUND_SURNAME:
            sur.append(2)
        if ch in SURNAME_1:
            sur.append(1)
        if not sur or not left_ok(p):
            p += 1
            continue
        hit = None
        for k in sur:
            for g in (2, 1):
                q = p + k + g
                if q > n:
                    continue
                given = text[p + k:q]
                if not given or any((ch2 not in GIVEN_CHARS) for ch2 in given):
                    continue
                if not right_ok(q):
                    continue
                cand = text[p:q]
                if cand in NAME_STOP or cand in COMMON_WORD_STOP:
                    continue
                # 名字最后一个字不能是地名/机构常见尾字（徐家汇、王府井这类）
                if cand[-1] in NAME_TAIL_BAD:
                    continue
                hit = (p, q, cand)
                break
            if hit:
                break
        if hit:
            out.append(hit)
            p = hit[1]
        else:
            p += 1
    return out


# ---------------------------------------------------------------------------
# 版面还原：把字符拼成「视觉行」
# ---------------------------------------------------------------------------

def _visual_lines(page):
    """返回 [(line_text, entries)]，entries[i] = (char, Rect) 或 (" ", None)

    以 span（字体片段）为单位拼装视觉行：同一 span 内字符顺序天然正确，
    span 之间按 x 排序用空格分隔，避免文字横向重叠时串字。
    """
    data = page.get_text("rawdict")
    spans = []
    for blk in data.get("blocks", []):
        if blk.get("type", 0) != 0:
            continue
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                chars = []
                for ch in span.get("chars", []):
                    c = ch.get("c", "")
                    if not c or c in "\r\n\t\u3000" or c.strip() == "":
                        continue
                    x0, y0, x1, y1 = ch["bbox"]
                    if x1 - x0 < 0.2 or y1 - y0 < 0.2:
                        continue
                    if (x1 - x0) > (y1 - y0) * 1.8:  # 竖排 / 旋转字符
                        continue
                    chars.append((c, pymupdf.Rect(x0, y0, x1, y1)))
                if not chars:
                    continue
                xs0 = min(c[1].x0 for c in chars)
                ys0 = min(c[1].y0 for c in chars)
                xs1 = max(c[1].x1 for c in chars)
                ys1 = max(c[1].y1 for c in chars)
                spans.append({"rect": pymupdf.Rect(xs0, ys0, xs1, ys1), "chars": chars})
    if not spans:
        return []

    spans.sort(key=lambda s: (s["rect"].y0, s["rect"].x0))
    groups = []
    for sp in spans:
        cy = (sp["rect"].y0 + sp["rect"].y1) / 2.0
        hh = sp["rect"].height
        hit = None
        for g in groups:
            if abs(g["cy"] - cy) <= max(2.0, max(g["h"], hh) * 0.42):
                hit = g
                break
        if hit is None:
            groups.append({"cy": cy, "h": hh, "spans": [sp]})
        else:
            hit["spans"].append(sp)
            hit["h"] = max(hit["h"], hh)

    out = []
    for g in groups:
        seq = sorted(g["spans"], key=lambda s: s["rect"].x0)
        text_parts, entries = [], []
        prev_x1 = None
        prev_h = g["h"]
        for sp in seq:
            if prev_x1 is not None and sp["rect"].x0 - prev_x1 > max(0.9, min(prev_h, sp["rect"].height) * 0.42):
                text_parts.append(" ")
                entries.append((" ", None))
            prev_x1 = None
            for c, r in sp["chars"]:
                if prev_x1 is not None and r.x0 - prev_x1 > max(1.2, r.height * 0.62):
                    text_parts.append(" ")
                    entries.append((" ", None))
                text_parts.append(c)
                entries.append((c, r))
                prev_x1 = r.x1 if prev_x1 is None else max(prev_x1, r.x1)
            prev_h = sp["rect"].height
        out.append(("".join(text_parts), entries))
    return out


def _span_rect(entries, start, end):
    rs = [entries[i][1] for i in range(start, min(end, len(entries)))
          if i < len(entries) and entries[i][1] is not None]
    if not rs:
        return None
    r = rs[0]
    for x in rs[1:]:
        r = r | x
    return r


_PUNCT = " :：,，、;；。.|·-—_"


def _clip_value(text, value_start):
    """从 value_start 起截断到下一个标签词之前，并去掉首尾标点"""
    s = value_start
    while s < len(text) and text[s] in " :：·":
        s += 1
    seg = text[s:]
    m = RE_ANY_LABEL.search(seg)
    end = s + (m.start() if m else len(seg))
    for stop in "。；;":
        i = text.find(stop, s, end)
        if i > s:
            end = i
            break
    i = text.find("，", s, end)
    while i > s:
        tail = text[i + 1:end].lstrip()
        if tail and RE_ANY_LABEL.match(tail):
            end = i
            break
        i = text.find("，", i + 1, end)
    while end > s and text[end - 1] in _PUNCT:
        end -= 1
    while s < end and text[s] in " :：·":
        s += 1
    return s, end


def _trim_addr_prefix(text, s, e):
    """去掉「现居住于 / 家里住在 / 位于」这类引导词"""
    for pre in ("现居住于", "现居住在", "现居于", "现居住", "居住于", "居住地", "住所在", "家住",
                "住在", "居所", "位于", "地址为", "为", "在"):
        if text[s:e].startswith(pre) and (e - s) - len(pre) >= 4:
            return s + len(pre)
    # 兜底：前几个字里出现「在 / 于」，说明地址从它后面开始
    for k in range(min(6, e - s)):
        if text[s + k] in "在于" and (e - (s + k + 1)) >= 4:
            return s + k + 1
    return s


# ---------------------------------------------------------------------------
# 单行扫描
# ---------------------------------------------------------------------------

def _scan_line(text, entries, pno):
    found = []
    taken = []  # 已占用的 (start,end)，避免重复命中

    def add(kind, start, end, raw=None, note=""):
        for (a, b) in taken:
            if start < b and end > a:
                return
        r = _span_rect(entries, start, end)
        if r is None or (r.width < 0.8 and r.height < 0.8):
            return
        taken.append((start, end))
        found.append({
            "type": kind,
            "text": raw if raw is not None else text[start:end].strip(),
            "rect": r,
            "page": pno,
            "note": note,
        })

    # 1. 身份证
    for m in RE_ID18.finditer(text):
        if _id18_ok(m.group(0)):
            add("idcard", m.start(), m.end(), m.group(0))
    for m in RE_ID15.finditer(text):
        if _id15_ok(m.group(0)):
            add("idcard", m.start(), m.end(), m.group(0))
    # 校验位不通过但字段名明确 → 照打（扫描/OCR 错一位很常见）
    for m in RE_ID_LABEL_FB.finditer(text):
        add("idcard", m.start(1), m.end(1), m.group(1), "标签兜底")

    # 2. 银行卡（16-19 位，Luhn 校验）
    for m in RE_BANK.finditer(text):
        s = m.group(0)
        if _luhn_ok(s) and len(set(s)) >= 5:
            add("bankcard", m.start(), m.end(), s)
    for m in RE_BANK_LABEL_FB.finditer(text):
        add("bankcard", m.start(1), m.end(1), m.group(1), "标签兜底")

    # 3. 手机号
    for rx in (RE_MOBILE, RE_MOBILE_SEP):
        for m in rx.finditer(text):
            add("phone", m.start(), m.end(), m.group(0))

    # 3.5 长数字串拆分：表格里相邻单元格没有分隔时，
    #     「手机号 + 身份证号」会被拼成一整串 29 位数字，正则的边界断言全部失效。
    #     这里在串内滑动取窗口，把合法号码逐段挖出来。
    for m in re.finditer(r"[0-9]{11,}", text):
        run, base = m.group(0), m.start()
        used = [False] * len(run)

        def free(i, n):
            return not any(used[i:i + n])

        def take(i, n, kind, note):
            for k in range(i, i + n):
                used[k] = True
            add(kind, base + i, base + i + n, run[i:i + n], note)

        # 先取身份证（校验位 + 省份码 + 日期三重约束，最不容易撞）
        for i in range(0, len(run) - 17):
            seg = run[i:i + 18]
            if free(i, 18) and _id18_ok(seg) and _id_plausible(seg):
                take(i, 18, "idcard", "长串拆分")
        # 再取银行卡（Luhn）
        for n in (19, 18, 17, 16):
            for i in range(0, len(run) - n + 1):
                seg = run[i:i + n]
                if free(i, n) and _luhn_ok(seg) and len(set(seg)) >= 5:
                    take(i, n, "bankcard", "长串拆分")
        # 再取手机号
        for i in range(0, len(run) - 10):
            seg = run[i:i + 11]
            if free(i, 11) and re.fullmatch(r"1[3-9][0-9]{9}", seg):
                take(i, 11, "phone", "长串拆分")
        # 结构合理但校验位对不上（OCR 错一位最常见）：只在「明显是多段号码粘连」
        # 的长串里兜底，避免误伤快递单号、发票号这类 13~20 位业务编号。
        if len(run) >= 22:
            for i in range(0, len(run) - 17):
                seg = run[i:i + 18]
                if free(i, 18) and _id_plausible(seg) and 1940 <= int(seg[6:10]) <= 2010:
                    take(i, 18, "idcard", "长串拆分·校验位异常")
        # 剩下还不短的数字段（≥24 位，必定是多段号码粘在一起）：整段打掉
        i = 0
        while i < len(run):
            if used[i]:
                i += 1
                continue
            j = i
            while j < len(run) and not used[j]:
                j += 1
            if j - i >= 24:
                take(i, j - i, "idcard", "粘连长串")
            i = j

    # 4. 邮箱
    for m in RE_EMAIL.finditer(text):
        add("email", m.start(), m.end(), m.group(0))
    # 字距被拉开的邮箱：去掉空格后再匹配，再把位置映射回原串
    if " " in text and "@" in text:
        idx = [i for i, ch in enumerate(text) if ch != " "]
        flat = "".join(text[i] for i in idx)
        for m in RE_EMAIL.finditer(flat):
            s0 = idx[m.start()]
            s1 = idx[m.end() - 1] + 1
            if s1 - s0 > m.end() - m.start():
                add("email", s0, s1, m.group(0), "字距还原")

    # 5. 座机（0xx-xxxxxxxx / 带标签的电话号码）
    for m in RE_TEL.finditer(text):
        add("tel", m.start(), m.end(), m.group(0))
    for m in RE_TEL_LABEL.finditer(text):
        val = m.group(1).strip()
        if re.fullmatch(r"[0-9\-\s\(\)]{7,20}", val) and val.count("-") <= 2:
            add("tel", m.start(1), m.start(1) + len(val), val.strip())

    # 6. 出生日期（必须带出生/生日语义）
    for m in RE_BIRTH_LABEL.finditer(text):
        add("birth", m.start(1), m.end(1), m.group(1).strip(), "标签:出生")
    # 出生词写在日期后面的写法：1992年7月18日出生 / 本人1992年07月18日生
    for m in RE_BIRTH_SUFFIX.finditer(text):
        add("birth", m.start(1), m.end(1), m.group(1).strip(), "后缀:出生")

    # 7. 性别
    for m in RE_GENDER.finditer(text):
        add("gender", m.start(1), m.end(1), m.group(1))
    for rx, nte in ((RE_GENDER_BARE_1, "逗号夹注"), (RE_GENDER_BARE_2, "逗号夹注"),
                    (RE_GENDER_BARE_3, "出生后夹注")):
        for m in rx.finditer(text):
            add("gender", m.start(1), m.end(1), m.group(1), nte)
    if not found and len(text.strip()) == 1 and text.strip() in "男女":
        idx = text.index(text.strip())
        add("gender", idx, idx + 1, text.strip())

    # 8. 年龄
    for m in RE_AGE.finditer(text):
        add("age", m.start(1), m.end(1), m.group(1))
    for m in RE_AGE_2.finditer(text):
        add("age", m.start(1), m.end(1), m.group(1))
    for m in RE_AGE_3.finditer(text):
        try:
            v = int(m.group(1))
        except ValueError:
            continue
        if 1 <= v <= 120:
            add("age", m.start(1), m.end(1), m.group(1))

    # 9. 地址
    for m in RE_ADDR_LABEL.finditer(text):
        s, e = _clip_value(text, m.start(1))
        s = _trim_addr_prefix(text, s, e)
        if e - s >= 4:
            add("address", s, e, text[s:e])
    for m in RE_ADDR_FREE.finditer(text):
        s, e = _trim_addr_prefix(text, m.start(), m.end()), m.end()
        add("address", s, e, text[s:e])

    # 10. 姓名：保留姓氏，只打码名字
    def add_name(s, e, cand):
        cand = (cand or "").strip()
        while cand and cand[-1] in _PUNCT:
            cand = cand[:-1]
            e -= 1
        if not cand or cand in NAME_STOP or not _looks_name(cand):
            return
        keep = 2 if (len(cand) >= 3 and cand[:2] in COMPOUND_SURNAME) else 1
        if len(cand) - keep < 1:
            return
        add("name", s + keep, e, cand, "保留姓氏:%s" % cand[:keep])

    for rx in (RE_NAME_LABEL, RE_NAME_SIGN, RE_NAME_SELF):
        for m in rx.finditer(text):
            s, e = _clip_value(text, m.start(1))
            cand = text[s:e]
            if not _looks_name(cand.strip()):
                s, e = m.start(1), m.end(1)
                cand = text[s:e]
            add_name(s, e, cand)
    for m in RE_NAME_HONOR.finditer(text):
        add_name(m.start(1), m.end(1), m.group(1))

    # 11. 完全无提示的人名
    #    11a 叙述文本通用规则：姓氏 + 名字常用字（覆盖 2 字、3 字、复姓 4 字）
    for (s, e, cand) in _scan_names_prose(text):
        keep = 2 if (len(cand) >= 3 and cand[:2] in COMPOUND_SURNAME) else 1
        if len(cand) - keep < 1:
            continue
        add("name", s + keep, e, cand, "叙述·保留姓氏:%s" % cand[:keep])
    #    11b 老的动词白名单规则，作为补充
    for m in RE_NAME_BARE.finditer(text):
        cand = m.group(1)
        if cand in NAME_STOP or cand in COMMON_WORD_STOP:
            continue
        # 地名/机构名常见的第三字，宁可放过
        if cand[-1] in NAME_TAIL_BAD:
            continue
        # 「施工方」「合格率」「完成度」这类量词/属性词尾，不是人名
        if cand[-1] in "方性率度值量费价额份项类批次率":
            continue
        add_name(m.start(1), m.end(1), cand)

    # 12. 人名枚举：「王欣、龚宇、姚玲三个人一起到了现场」
    for m in RE_NAME_LIST.finditer(text):
        parts = m.group(1).split("、")
        # 枚举末尾容易把量词吃进来（「姚玲三」），先削掉
        if parts and len(parts[-1]) == 3 and parts[-1][2] in "个人名位两三四五六七八九十几十多余":
            parts[-1] = parts[-1][:2]
        ok = [p for p in parts if _looks_name(p)]
        if len(ok) < 2 or len(ok) < len(parts):
            continue
        pos = m.start(1)
        for p in parts:
            idx = text.find(p, pos)
            if idx >= 0:
                add_name(idx, idx + len(p), p)
                pos = idx + len(p)

    # 13. 并列人名：「张三和李四都到了」
    for m in RE_NAME_CONJ.finditer(text):
        a, b = m.group(1), m.group(2)
        if _looks_name(a) and _looks_name(b):
            add_name(m.start(1), m.end(1), a)
            add_name(m.start(2), m.end(2), b)

    # 14. 带引入语的人名：「同行的金悦在旁边核对清单」
    for m in RE_NAME_CTX.finditer(text):
        cand = m.group(1)
        if cand in NAME_STOP or not _looks_name(cand):
            continue
        add_name(m.start(1), m.end(1), cand)

    return found


# ---------------------------------------------------------------------------
# 文档级检测
# ---------------------------------------------------------------------------

def _to_page_rect(r, page):
    if page.rotation:
        return (r * page.rotation_matrix).normalize()
    return r


# ---------------------------------------------------------------------------
# 表单域（AcroForm）：真实表单类 PDF 里大量字段值存在这里，
# 普通打码（redact）动不了它，必须单独清理，否则文字会原样留在成品里。
# ---------------------------------------------------------------------------

_W_LABELS = [
    ("birth", r"出生|生日|DOB|birth"),
    ("idcard", r"身份|证件|证\s*号|ID\s*No|idcard|\bid\b"),
    ("bankcard", r"卡\s*号|账\s*号|账户|开户|bank|card|account"),
    ("phone", r"手机|电话|联系方式|mobile|phone|tel"),
    ("email", r"邮箱|邮件|e-?mail|mail"),
    ("address", r"地址|住址|address|addr"),
    ("name", r"姓名|名字|人员|客户|申请人|本人|员工|职工|name"),
]
_W_LABEL_RX = [(k, re.compile(p, re.I)) for k, p in _W_LABELS]


def _widget_label(page, rect):
    """取表单域「左侧 / 上方」最近的文字，用来判断这个字段装的是什么"""
    try:
        blocks = page.get_text("blocks")
    except Exception:
        return ""
    parts = []
    for b in blocks:
        try:
            x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4]
        except Exception:
            continue
        if not str(txt).strip():
            continue
        cy = (y0 + y1) / 2.0
        if x1 <= rect.x0 + 3 and rect.y0 - 8 <= cy <= rect.y1 + 8 and rect.x0 - x1 < 300:
            parts.append(str(txt))
        elif y1 <= rect.y0 + 2 and rect.y0 - y1 < 70 and \
                abs((x0 + x1) / 2.0 - (rect.x0 + rect.x1) / 2.0) < rect.width / 2.0 + 80:
            parts.append(str(txt))
    return " ".join(parts)[:200]


def _classify_value(v, hint):
    """先靠号码自身的结构判定，结构不明时再看字段名/旁边标签"""
    v = (v or "").strip()
    if not v:
        return None
    flat = v.replace(" ", "")
    if re.fullmatch(r"[0-9]{17}[0-9Xx]", flat) and (_id18_ok(flat) or _id_plausible(flat)):
        return "idcard"
    if RE_EMAIL.fullmatch(flat):
        return "email"
    if re.fullmatch(r"1[3-9][0-9]{9}", flat):
        return "phone"
    if re.fullmatch(r"[0-9]{16,19}", flat) and (_luhn_ok(flat) or not hint):
        return "bankcard"
    if re.fullmatch(r"0[0-9]{2,3}-?[0-9]{7,8}", flat):
        return "tel"
    if re.fullmatch(r"[0-9]{4}\s*[年\-/\.]\s*[0-9]{1,2}\s*[月\-/\.]\s*[0-9]{1,2}\s*日?", v):
        return "birth" if re.search(r"出生|生日|DOB|birth", hint, re.I) else None
    if RE_ADDR_FREE.fullmatch(flat) or (re.search(r"路|街|区|县|省|市", flat) and len(flat) >= 8):
        if re.search(r"地址|住址|address|addr", hint, re.I):
            return "address"
    if 2 <= len(flat) <= 4 and _looks_name(flat) and re.search(r"姓名|名字|人员|客户|申请人|本人|员工|职工|name", hint, re.I):
        return "name"
    if re.fullmatch(r"[0-9]{15,18}", flat) and re.search(r"身份|证件|证\s*号", hint, re.I):
        return "idcard"
    return None


def scan_widgets(page, pno):
    """把表单域里填的值也纳入检测。返回 findings 列表。"""
    out = []
    try:
        widgets = list(page.widgets())
    except Exception:
        return out
    for w in widgets:
        try:
            val = w.field_value
        except Exception:
            continue
        if not isinstance(val, str) or not val.strip():
            continue
        try:
            rect = pymupdf.Rect(w.rect)
        except Exception:
            continue
        if rect.is_empty or rect.width < 2 or rect.height < 2:
            continue
        hint = " ".join([str(getattr(w, "field_name", "") or ""), _widget_label(page, rect)])
        kind = _classify_value(val.strip(), hint)
        if not kind:
            continue
        out.append({"type": kind, "text": val.strip(), "rect": rect, "page": pno,
                    "note": "表单域·字段名:%s" % (getattr(w, "field_name", "") or "")})
    return out


def _line_box(entries):
    rs = [r for _, r in entries if r is not None]
    if not rs:
        return None
    b = rs[0]
    for r in rs[1:]:
        b = b | r
    return b


def _header_cols(page_lines, headers):
    """找出表头写着 headers 里任一词的那一列的横向区间。

    真实表单最常见的情况：表头写着「姓名 / 性别 / 人员」，
    下方数据行里却完全没有关键字。这时只能靠列对齐来判定。
    """
    cols = []
    for text, entries in page_lines:
        box = _line_box(entries)
        if box is None:
            continue
        hdr = []
        for h in headers:
            i = 0
            while True:
                j = text.find(h, i)
                if j < 0:
                    break
                i = j + len(h)
                left = text[j - 1] if j > 0 else ""
                right = text[j + len(h)] if j + len(h) < len(text) else ""
                if left and "\u4e00" <= left <= "\u9fa5":
                    continue
                if right and "\u4e00" <= right <= "\u9fa5":
                    continue
                r = _span_rect(entries, j, j + len(h))
                if r is not None:
                    hdr.append(r.x0)
        if not hdr:
            continue
        starts = []
        for m in RE_ANY_LABEL.finditer(text):
            r = _span_rect(entries, m.start(), m.end())
            if r is not None:
                starts.append(r.x0)
        starts = sorted(set(starts))
        for x0 in hdr:
            right = [s for s in starts if s > x0 + 2]
            x1 = (min(right) - 3) if right else (x0 + box.width * 0.25)
            cols.append((x0 - 8, max(x1, x0 + 10), box.y1))
    return cols


def _name_columns(page_lines):
    return _header_cols(page_lines, NAME_COL_HEADERS)


def _cell_chars(entries, cx0, cx1, hy):
    out = []
    for ch, r in entries:
        if r is None or r.y0 < hy - 1:
            continue
        if cx0 <= (r.x0 + r.x1) / 2.0 <= cx1:
            out.append((ch, r))
    return out


def _scan_gender_columns(page_lines, pno):
    """表头写「性别」，单元格里只有一个「男 / 女」"""
    cols = _header_cols(page_lines, ["性别", "性 别"])
    if not cols:
        return []
    out = []
    for text, entries in page_lines:
        for (cx0, cx1, hy) in cols:
            cand = _cell_chars(entries, cx0, cx1, hy)
            s = "".join(c[0] for c in cand).strip()
            if s in ("男", "女") and cand:
                ch, r = cand[0]
                out.append({"type": "gender", "text": s, "rect": r, "page": pno,
                            "note": "表头列"})
    return out


def _scan_name_columns(page_lines, pno):
    """按「姓名列」把列下方的短中文名识别成姓名"""
    cols = _name_columns(page_lines)
    if not cols:
        return []
    out = []
    for text, entries in page_lines:
        for (cx0, cx1, hy) in cols:
            cand = _cell_chars(entries, cx0, cx1, hy)
            if not cand:
                continue
            s = "".join(c[0] for c in cand).strip().strip(_PUNCT)
            if not (2 <= len(s) <= 4) or not _looks_name(s):
                continue
            keep = 2 if (len(s) >= 3 and s[:2] in COMPOUND_SURNAME) else 1
            if len(s) - keep < 1:
                continue
            masked = cand[keep:]
            rect = masked[0][1]
            for c in masked[1:]:
                rect = rect | c[1]
            out.append({"type": "name", "text": s, "rect": rect, "page": pno,
                        "note": "表头列·保留姓氏:%s" % s[:keep]})
    return out


def _spread_confirmed_names(doc, findings):
    """已确认的姓名，在全文其它位置独立出现时同样打码。

    否则「表格里认出来了、正文叙述里又裸奔一次」这种真实场景会漏。
    """
    names = {}
    for f in findings:
        if f["type"] == "name" and f.get("text"):
            names[f["text"]] = True
    if not names:
        return findings
    extra = []
    for pno in range(doc.page_count):
        for text, entries in _visual_lines(doc[pno]):
            for nm in names:
                start = 0
                while True:
                    i = text.find(nm, start)
                    if i < 0:
                        break
                    start = i + 1
                    befor = text[i - 1] if i > 0 else ""
                    aftr = text[i + len(nm)] if i + len(nm) < len(text) else ""
                    # 已确认是人名，只要任一侧不是「实词汉字」就认。
                    # 两侧都是汉字时，只有它们属于「的/是/和/与/在…」这类虚词才认，
                    # 否则可能是更长词语的一部分（如「江苏」嵌在「江苏省」里）。
                    soft = "的是了和与跟由对把被让给从在、，。；："
                    left_ok = (not befor) or not ("\u4e00" <= befor <= "\u9fa5") or befor in soft
                    right_ok = (not aftr) or not ("\u4e00" <= aftr <= "\u9fa5") or aftr in soft
                    if not (left_ok or right_ok):
                        continue
                    keep = 2 if (len(nm) >= 3 and nm[:2] in COMPOUND_SURNAME) else 1
                    r = _span_rect(entries, i + keep, i + len(nm))
                    if r is None:
                        continue
                    extra.append({"type": "name", "text": nm, "rect": r,
                                  "page": pno, "note": "同名扩散:%s" % nm[:keep]})
    if not extra:
        return findings
    for f in extra:
        f["rect"] = _to_page_rect(f["rect"], doc[f["page"]])
    return findings + extra


def _scan_birth_across_lines(lines, pno):
    """「1996年3月24日出 / 生，女」——「出生」被换行拆开时，逐行扫描会整条漏掉。

    这里检查相邻两行：上一行以日期结尾、下一行以「生」开头，就按出生日期处理。
    """
    out = []
    for i in range(len(lines) - 1):
        t1, e1 = lines[i]
        t2 = lines[i + 1][0].lstrip()
        # 两种拆法都要认：「…日」+「出生，」  和  「…日出」+「生，」
        if not (t2.startswith("生") or t2.startswith("出生")):
            continue
        body = t1.rstrip()
        m = re.search(r"(%s)\s*出?$" % DATE_BODY, body)
        if not m:
            continue
        s, e = m.start(1), m.end(1)
        r = _span_rect(e1, s, e)
        if r is None:
            continue
        out.append({"type": "birth", "text": m.group(1), "rect": r, "page": pno,
                    "note": "跨行:出生"})
    return out


def _scan_names_suspect(doc, findings):
    """兜底：列出「像人名但证据不够」的候选，交给用户勾选。

    规则：首字是姓氏、后面 1~2 字全是名字常用字、左边是标点/行首，
    但后面跟的字不在「谓语字表」里（所以自动规则不敢直接打码）。
    再要求这个候选在全文中出现 ≥2 次——同一个「姓+名用字」反复出现，
    基本可以确定是个人名，而不是偶然撞上的普通词。
    """
    taken = {}
    for f in findings:
        if f["type"] == "name":
            taken[f["text"]] = True

    cand = {}   # text -> [(page, rect)]
    for pno in range(doc.page_count):
        page = doc[pno]
        for text, entries in _visual_lines(page):
            n = len(text)
            p = 0
            while p < n - 1:
                ch = text[p]
                if not _is_han(ch):
                    p += 1
                    continue
                if p > 0:
                    prev = text[p - 1]
                    if _is_han(prev) and prev not in LEFT_HARD and prev not in LEFT_SOFT_CHARS:
                        p += 1
                        continue
                sur = 0
                if p + 1 < n and text[p:p + 2] in COMPOUND_SURNAME:
                    sur = 2
                elif ch in SURNAME_1:
                    sur = 1
                if not sur:
                    p += 1
                    continue
                hit = None
                for g in (2, 1):
                    q = p + sur + g
                    if q > n:
                        continue
                    given = text[p + sur:q]
                    if not given or any(c not in GIVEN_CHARS for c in given):
                        continue
                    cand_full = text[p:q]
                    if cand_full in NAME_STOP or cand_full in COMMON_WORD_STOP:
                        continue
                    if cand_full[-1] in NAME_TAIL_BAD:
                        continue
                    # 已经自动打码过的，不用再列
                    if cand_full in taken:
                        hit = (p, q, cand_full)
                        break
                    # 右侧必须是「句子还能往下走」的边界，否则多半是更长词语的一部分
                    if q < n:
                        nxt = text[q]
                        if _is_han(nxt) and (nxt in GIVEN_CHARS or nxt in RIGHT_PRED):
                            continue
                    hit = (p, q, cand_full)
                    break
                if hit:
                    # 只遮名字，姓氏留给用户看
                    r = _span_rect(entries, hit[0] + sur, hit[1])
                    if r is not None and r.width * r.height > 0.5:
                        cand.setdefault(hit[2], []).append((pno, r))
                    p = hit[1]
                else:
                    p += 1

    out = []
    for nm, lst in cand.items():
        if len(lst) < 2 or nm in taken:
            continue
        keep = 2 if (len(nm) >= 3 and nm[:2] in COMPOUND_SURNAME) else 1
        if len(nm) - keep < 1:
            continue
        for (pno, r) in lst:
            out.append({"type": "name", "text": nm, "rect": r, "page": pno,
                        "note": "疑似·保留姓氏:%s" % nm[:keep], "suspect": True})
    return out


def detect(doc, only_pages=None):
    findings = []
    for pno in range(doc.page_count):
        if only_pages is not None and pno not in only_pages:
            continue
        page = doc[pno]
        lines = _visual_lines(page)
        for text, entries in lines:
            for f in _scan_line(text, entries, pno):
                f["rect"] = _to_page_rect(f["rect"], page)
                findings.append(f)
        for f in _scan_birth_across_lines(lines, pno):
            f["rect"] = _to_page_rect(f["rect"], page)
            findings.append(f)
        for f in _scan_name_columns(lines, pno):
            f["rect"] = _to_page_rect(f["rect"], page)
            findings.append(f)
        for f in _scan_gender_columns(lines, pno):
            f["rect"] = _to_page_rect(f["rect"], page)
            findings.append(f)
        for f in scan_widgets(page, pno):
            f["rect"] = _to_page_rect(f["rect"], page)
            findings.append(f)
    findings = _dedupe(findings)
    findings = _dedupe(_spread_confirmed_names(doc, findings))
    # 疑似人名：证据不足、默认不打码，但列出来让用户一眼确认
    try:
        sus = _scan_names_suspect(doc, findings)
        if sus:
            for f in sus:
                f["rect"] = _to_page_rect(f["rect"], doc[f["page"]])
            findings = _dedupe(findings + sus)
    except Exception:
        pass
    for i, f in enumerate(findings):
        f["id"] = "f%d" % i
    return findings


def _dedupe(findings):
    prio = {t: i for i, t in enumerate(TYPE_ORDER)}
    findings.sort(key=lambda f: (prio.get(f["type"], 99), -f["rect"].get_area()))
    kept = []
    for f in findings:
        r = f["rect"]
        dup = False
        for k in kept:
            if k["page"] != f["page"]:
                continue
            inter = r & k["rect"]
            if inter.is_empty:
                continue
            if inter.get_area() >= min(r.get_area(), k["rect"].get_area()) * 0.6:
                dup = True
                break
        if not dup:
            kept.append(f)
    kept.sort(key=lambda f: (f["page"], round(f["rect"].y0, 1), round(f["rect"].x0, 1)))
    return kept


# ---------------------------------------------------------------------------
# 马赛克
# ---------------------------------------------------------------------------

def _mask_text(kind, s):
    s = (s or "").strip()
    if kind == "phone" and len(s) >= 7:
        return s[:3] + "****" + s[-4:]
    if kind == "idcard":
        return (s[:4] + "*" * (len(s) - 8) + s[-4:]) if len(s) > 8 else "*" * len(s)
    if kind == "bankcard":
        return (s[:4] + " **** **** " + s[-4:]) if len(s) >= 10 else "*" * len(s)
    if kind == "email" and "@" in s:
        a, b = s.split("@", 1)
        return (a[:2] + "***@" + b) if len(a) > 2 else ("***@" + b)
    if kind == "name" and len(s) >= 2:
        return s[0] + "*" * (len(s) - 1)
    if kind == "address":
        return s[:3] + "……（共 %d 字）" % len(s)
    if kind == "birth":
        return s[:4] + "年**月**日"
    return s


def _pixelate(img, block, seed=0, flatten=0.30, darken=0.85):
    """真正的马赛克：
    1) 按 block 尺寸做块均值降采样——块内字形信息被直接丢弃；
    2) 再向区域均色压平 flatten 比例——抹掉残留的笔画灰度分布；
    3) 叠加确定性随机扰动并整体压暗，使像素与原文无对应关系。
    """
    w, h = img.size
    bw = max(1, w // max(1, block))
    bh = max(1, h // max(1, block))
    small = img.convert("RGB").resize((bw, bh), Image.BOX)
    px = small.load()
    tot = [0, 0, 0]
    for y in range(bh):
        for x in range(bw):
            r, g, b = px[x, y]
            tot[0] += r
            tot[1] += g
            tot[2] += b
    n = float(bw * bh)
    mean = (tot[0] / n, tot[1] / n, tot[2] / n)
    rnd = random.Random(hash((seed, w, h, block)) & 0xFFFFFFFF)
    for y in range(bh):
        for x in range(bw):
            r, g, b = px[x, y]
            r = r * (1 - flatten) + mean[0] * flatten
            g = g * (1 - flatten) + mean[1] * flatten
            b = b * (1 - flatten) + mean[2] * flatten
            j = rnd.randint(-8, 8)
            px[x, y] = (max(0, min(255, int(r * darken + j))),
                        max(0, min(255, int(g * darken + j))),
                        max(0, min(255, int(b * darken + j))))
    return small.resize((w, h), Image.NEAREST)


def _merge_rects(rects, pad=0.35):
    """相交的框合并成一块，避免马赛克互相切割出缝隙"""
    items = [pymupdf.Rect(r) + (-pad, -pad, pad, pad) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        for b in items:
            hit = -1
            for i, a in enumerate(out):
                if not (a & b).is_empty:
                    hit = i
                    break
            if hit >= 0:
                out[hit] = out[hit] | b
                changed = True
            else:
                out.append(b)
        items = out
    return items


def redact(doc, findings, review_rects=None):
    """执行打码：先按原文渲染像素 → 马赛克 → 抹除文本层 → 贴回马赛克块"""
    by_page = {}
    for f in findings:
        by_page.setdefault(f["page"], []).append(pymupdf.Rect(f["rect"]))
    for pno, rects in by_page.items():
        page = doc[pno]
        prect = page.rect
        clusters = []
        for r in _merge_rects(rects):
            r = pymupdf.Rect(r)
            r.x0 = max(r.x0, prect.x0)
            r.y0 = max(r.y0, prect.y0)
            r.x1 = min(r.x1, prect.x1)
            r.y1 = min(r.y1, prect.y1)
            if r.width > 0.5 and r.height > 0.5:
                clusters.append(r)
        patches = []
        for r in clusters:
            clip = pymupdf.Rect(r)
            try:
                pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(MOSAIC_ZOOM, MOSAIC_ZOOM), alpha=False)
            except Exception:
                continue
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # 块尺寸 ≈ 字高的 1/3：每个汉字被切成 3×3 个色块，笔画结构彻底打散
            block = max(6, int(round(r.height * MOSAIC_ZOOM * 0.42)))
            img = _pixelate(img, block, seed=hash((pno, round(r.y0, 1))))
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            patches.append((clip, pymupdf.Pixmap(buf.getvalue())))
        # 抹除文本层（不动图片、线框、表格线）
        # 表单域单独处理：redact 动不了 widget，字段值会整条留在成品里
        try:
            for w in list(page.widgets()):
                try:
                    wr = pymupdf.Rect(w.rect)
                except Exception:
                    continue
                hit = any(not (wr & r).is_empty for r in clusters)
                if not hit:
                    try:
                        hit = bool(_classify_value(str(w.field_value or ""),
                                                   str(getattr(w, "field_name", "") or "")))
                    except Exception:
                        hit = False
                if hit:
                    page.delete_widget(w)
        except Exception:
            pass
        for r in clusters:
            page.add_redact_annot(r, fill=False)
        try:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                                  text=pymupdf.PDF_REDACT_TEXT_REMOVE)
        except TypeError:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        for clip, pm in patches:
            page.insert_image(clip + (-0.4, -0.4, 0.4, 0.4), pixmap=pm, overlay=True, keep_proportion=False)
    # 清理可能残留隐私的元数据
    try:
        doc.set_metadata({})
    except Exception:
        pass
    return doc


def detect_document(path):
    doc = load_normalized(path)[0]
    fs = detect(doc)
    return doc, fs


def load_normalized(src):
    """把 /Rotate 页面旋转「固化」进内容，统一成 0° 工作副本。

    旋转页上 get_pixmap 用显示坐标、redact/insert_image 用内容坐标，两套坐标系
    不一致会导致打码错位。固化后全部统一，非旋转页原样拷贝（保留书签与链接）。
    """
    if isinstance(src, str):
        src = pymupdf.open(src)
        own = True
    else:
        own = False
    if src.page_count == 0 or all(p.rotation % 360 == 0 for p in src):
        return src, False
    out = pymupdf.open()
    for i in range(src.page_count):
        p = src[i]
        if p.rotation % 360 == 0:
            out.insert_pdf(src, from_page=i, to_page=i)
        else:
            r = p.rect
            np_ = out.new_page(width=r.width, height=r.height)
            np_.show_pdf_page(pymupdf.Rect(0, 0, r.width, r.height), src, i, rotate=0)
    if own:
        src.close()
    return out, True


def cli(inp, outp, verbose=True):
    doc, fs = detect_document(inp)
    auto = [f for f in fs if not f.get("suspect")]
    sus = [f for f in fs if f.get("suspect")]
    n_pages = doc.page_count
    redact(doc, auto)
    doc.save(outp, garbage=4, deflate=True, clean=True)
    doc.close()
    if verbose:
        # 署名与来源走 stderr，避免污染 stdout 上的 JSON 结果
        print("%s v%s | %s | %s" % (APP_NAME, VERSION, CREDIT_LINE, PROJECT_URL),
              file=sys.stderr)
        rep = {
            "pages": n_pages,
            "count": len(auto),
            "suspect": len(sus),
            "by_type": {},
            "items": [{"type": f["type"], "text": f["text"],
                       "page": f["page"] + 1,
                       "rect": [round(v, 2) for v in f["rect"]]} for f in auto],
        }
        if sus:
            rep["suspect_items"] = [{"text": f["text"], "page": f["page"] + 1} for f in sus]
        for f in auto:
            k = TYPE_NAME.get(f["type"], f["type"])
            rep["by_type"][k] = rep["by_type"].get(k, 0) + 1
        print(json.dumps(rep, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------
# 本地 HTTP 服务（只监听 127.0.0.1，不出本机）
# ---------------------------------------------------------------------------

import http.server
import secrets
import shutil
import tempfile
import urllib.parse

from PIL import ImageDraw

SERVE_TOKEN = secrets.token_hex(16)
TMPROOT = tempfile.mkdtemp(prefix="pdfmask_")
DOCS = {}
OUTS = {}
LOCK = threading.Lock()
BOOT_PATH = ""


def _cleanup_tmp():
    """退出时销毁临时目录，避免敏感文件残留在磁盘上"""
    try:
        shutil.rmtree(TMPROOT, ignore_errors=True)
    except Exception:
        pass


def _cleanup_stale():
    """启动时清理上次异常退出遗留的临时目录（超过 1 天的）"""
    import glob
    now = time.time()
    try:
        for p in glob.glob(os.path.join(tempfile.gettempdir(), "pdfmask_*")):
            if os.path.abspath(p) == os.path.abspath(TMPROOT):
                continue
            try:
                if now - os.path.getmtime(p) > 86400:
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass


def _hard_exit(code=0):
    """先清临时文件再退出（os._exit 不会触发 atexit）"""
    _cleanup_tmp()
    os._exit(code)


import atexit  # noqa: E402

atexit.register(_cleanup_tmp)

TYPE_COLOR = {
    "phone": (245, 158, 11),
    "idcard": (229, 72, 77),
    "bankcard": (124, 92, 255),
    "email": (18, 161, 80),
    "name": (47, 107, 255),
    "tel": (234, 88, 12),
    "address": (10, 162, 192),
    "birth": (214, 64, 159),
    "gender": (120, 128, 140),
    "age": (120, 128, 140),
    "manual": (17, 24, 39),
}


class DocState:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        raw = pymupdf.open(path)
        if raw.needs_pass:
            raise ValueError("该 PDF 有密码保护，请先解除密码后再处理")
        if raw.page_count == 0:
            raise ValueError("这个 PDF 没有任何页面")
        self.doc, _ = load_normalized(raw)
        if _:
            raw.close()
        self.pages = []
        for p in self.doc:
            self.pages.append({
                "w": round(p.rect.width, 2),
                "h": round(p.rect.height, 2),
                "hasText": bool(p.get_text().strip()),
                "rot": p.rotation,
            })
        self.findings = detect(self.doc)
        self.manual_n = 0

    def payload(self):
        items = []
        for f in self.findings:
            items.append({
                "id": f["id"],
                "type": f["type"],
                "label": TYPE_NAME.get(f["type"], f["type"]),
                "mask": _mask_text(f["type"], f["text"]) if f["type"] != "manual" else "手动框选区域",
                "page": f["page"],
                "rect": [round(v, 2) for v in f["rect"]],
                "note": f.get("note", ""),
                "suspect": bool(f.get("suspect")),
            })
        stats = {}
        for f in items:
            if f["suspect"]:
                continue
            stats[f["label"]] = stats.get(f["label"], 0) + 1
        return {
            "docId": self.doc_id,
            "name": self.name,
            "size": os.path.getsize(self.path) if os.path.exists(self.path) else 0,
            "pages": self.pages,
            "findings": items,
            "stats": stats,
            "scanned": [i for i, p in enumerate(self.pages) if not p["hasText"]],
            "outDir": _default_out_dir(self.path),
        }


# ---------------------------------------------------------------------------
# 用户设置：默认保存位置 / 是否每次询问
# ---------------------------------------------------------------------------

SETTINGS = dict(DEFAULT_SETTINGS)
SETTINGS_LOCK = threading.Lock()


def _load_settings():
    """读配置文件；任何异常都退回默认值，绝不因为配置坏掉而启动失败。"""
    out = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            if isinstance(raw.get("saveDir"), str):
                out["saveDir"] = raw["saveDir"].strip().strip('"')
            out["rememberDir"] = bool(raw.get("rememberDir", True))
            out["noAsk"] = bool(raw.get("noAsk", False))
            out["lang"] = "en" if raw.get("lang") == "en" else "zh"
    except Exception:
        pass
    return out


def _save_settings(cfg):
    """写配置文件（原子替换）。失败不抛异常，只返回 False。"""
    try:
        os.makedirs(SETTINGS_DIR, exist_ok=True)
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, SETTINGS_PATH)
        return True
    except Exception:
        return False


def _get_settings():
    with SETTINGS_LOCK:
        return dict(SETTINGS)


def _update_settings(**kw):
    with SETTINGS_LOCK:
        for k, v in kw.items():
            if k in DEFAULT_SETTINGS:
                SETTINGS[k] = v
        cfg = dict(SETTINGS)
    _save_settings(cfg)
    return cfg


# ---------------------------------------------------------------------------
# 检查更新：只去 GitHub 读一个版本号，不发送任何本地文件或个人信息
# ---------------------------------------------------------------------------

def _ver_tuple(text):
    """把 v1.4.0 / 1.4 / 1.4.0-beta 之类统一成 (1,4,0)，取不出数字就返回 None"""
    nums = re.findall(r"\d+", text or "")
    if not nums:
        return None
    t = [int(x) for x in nums[:3]]
    while len(t) < 3:
        t.append(0)
    return tuple(t)


def _asset_ver(name):
    """从文件名里抠版本：PDFPrivacyMasker-1.4.0.exe → (1,4,0)"""
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", name or "")
    return _ver_tuple(m.group(1)) if m else None


def _fetch_releases():
    """取 releases 列表。先直连，失败再放宽证书校验试一次（个别电脑装了抓包/加速软件会拦证书）。"""
    import ssl
    import urllib.request

    last = ""
    for relaxed in (False, True):
        try:
            ctx = None
            if relaxed:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(RELEASES_API, headers={
                "User-Agent": "PDFPrivacyMasker/" + VERSION,
                "Accept": "application/vnd.github+json",
            })
            with urllib.request.urlopen(req, timeout=UPDATE_TIMEOUT, context=ctx) as r:
                return json.loads(r.read().decode("utf-8", "replace")), ""
        except Exception as e:
            last = "%s: %s" % (e.__class__.__name__, str(e)[:120])
    return None, last


def _parse_releases(data):
    """从 releases 里挑出本平台能用的最新版本。

    优先用资产文件名里的版本（每个平台各自一个文件，最准）；
    资产名里没有版本号时退回 tag_name（例如 v1.4.0）。
    """
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return None
    best = None      # (ver, url, asset)
    tag_only = None  # (ver, page, tag)
    for rel in data:
        if not isinstance(rel, dict) or rel.get("draft"):
            continue
        page = rel.get("html_url") or RELEASES_URL
        tag = (rel.get("tag_name") or "").strip()
        tv = _ver_tuple(tag)
        if tv and (tag_only is None or tv > tag_only[0]):
            tag_only = (tv, page, tag)
        for a in rel.get("assets") or []:
            name = a.get("name") or ""
            if not name.lower().endswith(UPDATE_ASSET_SUFFIX):
                continue
            v = _asset_ver(name)
            if not v:
                continue
            if best is None or v > best[0]:
                best = (v, a.get("browser_download_url") or page, name)
    if best:
        return {"ver": best[0], "url": best[1], "asset": best[2], "source": "asset"}
    if tag_only:
        return {"ver": tag_only[0], "url": tag_only[1], "asset": "", "source": "tag"}
    return None


def check_update():
    """返回给界面的字典。任何失败都转成 ok=False + 兜底链接，绝不让界面卡住。"""
    cur = _ver_tuple(VERSION) or (0, 0, 0)
    data, err = _fetch_releases()
    if data is None:
        return {
            "ok": False,
            "current": VERSION,
            "error": _L("连不上 GitHub，可能是网络、代理或安全软件拦住了。",
                        "Cannot reach GitHub — network, proxy or security software may be blocking it."),
            "detail": err or "",
            "url": RELEASES_URL,
            "releasesUrl": RELEASES_URL,
        }
    got = _parse_releases(data)
    if not got:
        return {
            "ok": False,
            "current": VERSION,
            "error": _L("仓库里还没有适用于本平台的安装包，可以去发布页手动看看。",
                        "No build for this platform in the releases yet — have a look at the releases page."),
            "detail": "",
            "url": RELEASES_URL,
            "releasesUrl": RELEASES_URL,
        }
    latest = "%d.%d.%d" % got["ver"]
    return {
        "ok": True,
        "current": VERSION,
        "latest": latest,
        "hasUpdate": got["ver"] > cur,
        "url": got["url"],
        "asset": got["asset"],
        "source": got["source"],
        "releasesUrl": RELEASES_URL,
    }


_USER_DIRS_CACHE = []

# 系统已知文件夹（被 OneDrive 接管、改成中文名时也能定位到真实路径）
_KNOWN_FOLDERS = (
    ("374DE290-123F-4565-9164-39C4925E467B", "Downloads"),
    ("B4BFCC3A-DB2C-424C-B029-7FE99A87C641", "Desktop"),
    ("FDD39AD0-238F-46AF-ADB4-6C85480369C7", "Documents"),
)


def _known_folder(guid_text):
    """取 Windows 已知文件夹的真实路径（如「桌面」中文名 / OneDrive 重定向）。"""
    try:
        import ctypes
        from ctypes import wintypes as wt

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD),
                        ("Data4", ctypes.c_ubyte * 8)]

        g = GUID()
        ctypes.memmove(ctypes.byref(g), uuid.UUID(guid_text).bytes_le, 16)
        out = ctypes.c_wchar_p()
        shell32 = ctypes.windll.shell32
        shell32.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_void_p,
                                                 ctypes.POINTER(ctypes.c_wchar_p)]
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        if shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out)) != 0:
            return ""
        path = out.value or ""
        try:
            ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(out, ctypes.c_void_p))
        except Exception:
            pass
        return path
    except Exception:
        return ""


def _user_dirs():
    """候选的用户可用目录，按优先级排列。"""
    if _USER_DIRS_CACHE:
        return list(_USER_DIRS_CACHE)
    home = os.path.expanduser("~")
    cands = [_known_folder(g) for g, _ in _KNOWN_FOLDERS]
    cands += [os.path.join(home, "Downloads"), os.path.join(home, "Desktop"),
              os.path.join(home, "Documents"), home]
    out = []
    for c in cands:
        if c and os.path.isdir(c) and c not in out:
            out.append(c)
    if not out:
        out = [home]
    _USER_DIRS_CACHE[:] = out
    return list(out)


def _fallback_dir():
    for cand in _user_dirs():
        if os.path.isdir(cand):
            return cand
    return TMPROOT


def _default_out_dir(src_path):
    """没设置过保存位置时的默认目录：原 PDF 所在目录；临时上传则用「下载」。"""
    try:
        if not (src_path and os.path.abspath(src_path).startswith(os.path.abspath(TMPROOT))):
            d = os.path.dirname(os.path.abspath(src_path))
            if d and os.path.isdir(d):
                return d
    except Exception:
        pass
    return _fallback_dir()


def _settings_payload(src_path=None):
    cfg = _get_settings()
    hint = _default_out_dir(src_path) if src_path else _fallback_dir()
    saved = cfg["saveDir"]
    return {
        "saveDir": saved,
        "rememberDir": cfg["rememberDir"],
        "noAsk": cfg["noAsk"],
        "defaultDir": hint,
        # 已设过就用设置里的（哪怕目录暂时不存在，保存时会自动创建），否则跟随原文件
        "effectiveDir": saved or hint,
        "configured": bool(saved),
        "settingsPath": SETTINGS_PATH,
        "lang": cfg.get("lang", "zh"),
        "version": VERSION,
    }


# ---------------------------------------------------------------------------
# Windows 原生「选择文件夹」对话框（ctypes 调 IFileDialog，零额外依赖）
# ---------------------------------------------------------------------------

def _pick_directory(title="选择保存位置", initial=""):
    """弹出系统原生的文件夹选择框。

    返回 (路径, 状态)：状态 "ok" / "cancel" / "error"。
    实现在 ctypes 里手搓 COM 调用，避免引入 tkinter（单文件 exe 会因此胖 10MB）。
    """
    try:
        import ctypes
        from ctypes import wintypes as wt
    except Exception:
        return "", "error"

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD),
                    ("Data4", ctypes.c_ubyte * 8)]

    def _guid(text):
        g = GUID()
        ctypes.memmove(ctypes.byref(g), uuid.UUID(text).bytes_le, 16)
        return g

    CLSID_FILE_OPEN = _guid("DC1C5A9C-E88A-4DDE-A5A1-60F82A20AEF7")
    IID_IFILE_DIALOG = _guid("42F85136-DB7E-439C-85F1-E4075D135FC8")
    IID_ISHELL_ITEM = _guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")

    FOS_PICKFOLDERS = 0x00000020
    FOS_FORCEFILESYSTEM = 0x00000040
    FOS_PATHMUSTEXIST = 0x00000800
    SIGDN_FILESYSPATH = 0x80058000
    ERROR_CANCELLED = 0x800704C7

    def vtbl(obj, index, restype, *argtypes):
        """取 COM 对象的第 index 个虚函数。"""
        table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        return proto(table[index])

    ole32 = ctypes.windll.ole32
    shell32 = ctypes.windll.shell32
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, wt.DWORD]
    ole32.CoInitializeEx.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD,
                                       ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole32.CoTaskMemFree.restype = None

    pdlg = ctypes.c_void_p()
    item = ctypes.c_void_p()
    ctx = ctypes.c_void_p()
    hr_init = ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
    try:
        hr = ole32.CoCreateInstance(ctypes.byref(CLSID_FILE_OPEN), None, 1,
                                    ctypes.byref(IID_IFILE_DIALOG), ctypes.byref(pdlg))
        if hr != 0 or not pdlg:
            return "", "error"

        get_options = vtbl(pdlg, 10, ctypes.c_long, ctypes.POINTER(wt.DWORD))
        set_options = vtbl(pdlg, 9, ctypes.c_long, wt.DWORD)
        opts = wt.DWORD(0)
        if get_options(pdlg, ctypes.byref(opts)) == 0:
            set_options(pdlg, wt.DWORD(
                opts.value | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST))

        set_title = vtbl(pdlg, 17, ctypes.c_long, ctypes.c_wchar_p)
        set_title(pdlg, title)

        # 初始定位到上次用的目录
        start = initial if (initial and os.path.isdir(initial)) else _fallback_dir()
        try:
            shell32.SHCreateItemFromParsingName.argtypes = [
                ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_void_p)]
            shell32.SHCreateItemFromParsingName.restype = ctypes.c_long
            if shell32.SHCreateItemFromParsingName(
                    start, None, ctypes.byref(IID_ISHELL_ITEM), ctypes.byref(item)) == 0 and item:
                set_folder = vtbl(pdlg, 12, ctypes.c_long, ctypes.c_void_p)
                set_folder(pdlg, item)
        except Exception:
            pass

        show = vtbl(pdlg, 3, ctypes.c_long, ctypes.c_void_p)
        owner = None
        try:
            # 挂在当前前台窗口（通常是浏览器）上，避免对话框被浏览器挡住
            fg = ctypes.windll.user32.GetForegroundWindow()
            if fg:
                owner = ctypes.c_void_p(fg)
        except Exception:
            owner = None
        hr = show(pdlg, owner)
        if hr != 0:
            # 0x800704C7 = 用户点了取消，属正常操作
            return "", ("cancel" if (hr & 0xFFFFFFFF) == ERROR_CANCELLED else "error")

        get_result = vtbl(pdlg, 20, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
        picked = ctypes.c_void_p()
        if get_result(pdlg, ctypes.byref(picked)) != 0 or not picked:
            return "", "error"

        try:
            get_name = vtbl(picked, 5, ctypes.c_long, wt.DWORD,
                            ctypes.POINTER(ctypes.c_wchar_p))
            buf = ctypes.c_wchar_p()
            if get_name(picked, wt.DWORD(SIGDN_FILESYSPATH), ctypes.byref(buf)) != 0:
                return "", "error"
            path = buf.value or ""
            try:
                ole32.CoTaskMemFree(ctypes.cast(buf, ctypes.c_void_p))
            except Exception:
                pass
        finally:
            vtbl(picked, 2, ctypes.c_ulong)(picked)

        return (path, "ok" if path else "cancel")
    except Exception:
        return "", "error"
    finally:
        try:
            if pdlg:
                vtbl(pdlg, 2, ctypes.c_ulong)(pdlg)
        except Exception:
            pass
        try:
            if item:
                vtbl(item, 2, ctypes.c_ulong)(item)
        except Exception:
            pass
        try:
            if hr_init == 0:
                ctypes.windll.ole32.CoUninitialize()
        except Exception:
            pass


def _ensure_dir(path):
    """确认目录可用；不存在就尝试建。返回 (目录, 错误信息)。"""
    p = (path or "").strip().strip('"').strip("'")
    if not p:
        return "", "请先选择保存位置"
    p = os.path.abspath(os.path.expandvars(os.path.expanduser(p)))
    if os.path.isfile(p):
        return "", "这个路径是一个文件，请选择文件夹"
    if not os.path.isdir(p):
        try:
            os.makedirs(p, exist_ok=True)
        except Exception as e:
            return "", "无法创建这个文件夹：%s" % e
    if not os.access(p, os.W_OK):
        return "", "这个文件夹没有写入权限"
    return p, ""


def _unique_path(folder, base, suffix):
    p = os.path.join(folder, base + suffix + ".pdf")
    i = 2
    while os.path.exists(p):
        p = os.path.join(folder, base + suffix + " (%d).pdf" % i)
        i += 1
    return p


def _output_dir(src_path):
    return _default_out_dir(src_path)


def _preview_png(state, pno, zoom, sel, show_mask, hi):
    page = state.doc[pno]
    zoom = max(0.5, min(3.0, float(zoom)))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if show_mask:
        for f in state.findings:
            if f["page"] != pno or f["id"] not in sel:
                continue
            r = f["rect"]
            box = (int(round(r.x0 * zoom)), int(round(r.y0 * zoom)),
                   int(round(r.x1 * zoom)), int(round(r.y1 * zoom)))
            x0, y0 = max(0, box[0]), max(0, box[1])
            x1, y1 = min(img.width, box[2]), min(img.height, box[3])
            if x1 - x0 > 1 and y1 - y0 > 1:
                crop = img.crop((x0, y0, x1, y1))
                block = max(3, int(round(r.height * zoom * 0.42)))
                img.paste(_pixelate(crop, block, seed=abs(hash(f["id"]))), (x0, y0))
    dr = ImageDraw.Draw(img, "RGBA")
    for f in state.findings:
        if f["page"] != pno:
            continue
        r = f["rect"]
        box = [r.x0 * zoom, r.y0 * zoom, r.x1 * zoom, r.y1 * zoom]
        c = TYPE_COLOR.get(f["type"], (120, 120, 120))
        if f["id"] in sel:
            dr.rectangle(box, outline=c + (255,), width=2, fill=c + (34,))
        else:
            dr.rectangle(box, outline=(160, 166, 178, 210), width=1)
        if hi and f["id"] == hi:
            dr.rectangle([box[0] - 3, box[1] - 3, box[2] + 3, box[3] + 3],
                         outline=(255, 64, 96, 255), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _build_output(state, ids, out_dir=""):
    sel = [f for f in state.findings if f["id"] in set(ids)]
    if not sel:
        raise ValueError("没有选中任何需要打码的内容")
    folder, err = _ensure_dir(out_dir or _default_out_dir(state.path))
    if err:
        raise ValueError(err)
    src = pymupdf.open(state.path)
    work, _made = load_normalized(src)
    if not _made:
        work = src
    else:
        src.close()
    redact(work, sel)
    total_pages = work.page_count
    base = os.path.splitext(state.name)[0]
    outp = _unique_path(folder, base, "_已打码")
    try:
        work.save(outp, garbage=4, deflate=True, clean=True)
    except Exception as e:
        work.close()
        raise ValueError("保存失败：%s\n请换一个保存位置，或关掉正在打开的同名文件再试" % e)
    work.close()
    tok = uuid.uuid4().hex[:16]
    stats = {}
    for f in sel:
        lab = TYPE_NAME.get(f["type"], f["type"])
        stats[lab] = stats.get(lab, 0) + 1
    OUTS[tok] = outp
    return {
        "token": tok,
        "path": outp,
        "dir": os.path.dirname(outp),
        "name": os.path.basename(outp),
        "size": os.path.getsize(outp),
        "count": len(sel),
        "stats": stats,
        "pages": total_pages,
        "hitPages": len(set(f["page"] for f in sel)),
    }


class QuietServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    last_seen = time.time()

    def handle_error(self, request, client_address):
        import sys as _sys
        if _sys.exc_info()[0] in (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return
        super().handle_error(request, client_address)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "PDFMask/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    # ---- helpers -------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        try:
            self.server.last_seen = time.time()
        except Exception:
            pass
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _err(self, msg, code=400):
        self._json({"error": str(msg)}, code)

    def _authed(self):
        if self.headers.get("X-Token") != SERVE_TOKEN:
            self._err("unauthorized", 403)
            return False
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._err("bad host", 403)
            return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        chunks = []
        left = n
        while left > 0:
            b = self.rfile.read(min(65536, left))
            if not b:
                break
            chunks.append(b)
            left -= len(b)
        return b"".join(chunks)

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            html = HTML_UI.replace("__TOKEN__", SERVE_TOKEN).replace(
                "__BOOT__", json.dumps(BOOT_PATH, ensure_ascii=False)).replace(
                "__VERSION__", VERSION).replace(
                "__AUTHOR__", AUTHOR).replace(
                "__DEVELOPER__", DEVELOPER).replace(
                "__LICENSE__", LICENSE_NAME).replace(
                "__URL__", PROJECT_URL).replace(
                "__CREDIT__", CREDIT_LINE).replace(
                "__URLSHORT__", URL_SHORT).replace(
                "__THANKS__", QR_PNG_B64)
            self._send(200, html, "text/html; charset=utf-8")
            return
        if u.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return
        if u.path == "/api/ping":
            self._json({"ok": True})
            return
        if u.path == "/api/settings":
            if not self._authed():
                return
            st = DOCS.get(q.get("doc", [""])[0])
            return self._json(_settings_payload(st.path if st else None))
        if u.path == "/api/preview":
            try:
                st = DOCS.get(q.get("doc", [""])[0])
                if not st:
                    return self._err("文档已失效，请重新选择文件", 404)
                pno = max(0, min(st.doc.page_count - 1, int(q.get("page", ["0"])[0])))
                zoom = float(q.get("zoom", ["1.2"])[0])
                sel = set(x for x in (q.get("sel", [""])[0]).split(",") if x)
                mask = q.get("mask", ["1"])[0] == "1"
                hi = q.get("hi", [""])[0]
                png = _preview_png(st, pno, zoom, sel, mask, hi)
                self._send(200, png, "image/png")
            except Exception as e:
                self._err(e, 500)
            return
        if u.path == "/api/download":
            tok = q.get("token", [""])[0]
            p = OUTS.get(tok)
            if not p or not os.path.exists(p):
                return self._err("文件不存在", 404)
            data = open(p, "rb").read()
            fn = urllib.parse.quote(os.path.basename(p))
            self._send(200, data, "application/pdf",
                       {"Content-Disposition": "attachment; filename*=UTF-8''%s" % fn})
            return
        self._err("not found", 404)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if not self._authed():
            return
        try:
            if u.path == "/api/upload":
                return self._upload()
            if u.path == "/api/open":
                data = json.loads(self._body() or b"{}")
                return self._open_path(data.get("path", ""))
            if u.path == "/api/manual":
                data = json.loads(self._body() or b"{}")
                st = DOCS.get(data.get("doc", ""))
                if not st:
                    return self._err("文档已失效")
                r = [float(v) for v in data["rect"]]
                st.manual_n += 1
                fid = "m%d" % st.manual_n
                st.findings.append({
                    "id": fid, "type": "manual", "text": "",
                    "rect": pymupdf.Rect(r[0], r[1], r[2], r[3]),
                    "page": int(data.get("page", 0)), "note": "手动框选",
                })
                return self._json({"ok": True, "id": fid})
            if u.path == "/api/render":
                data = json.loads(self._body() or b"{}")
                st = DOCS.get(data.get("doc", ""))
                if not st:
                    return self._err("文档已失效")
                out_dir = data.get("dir") or ""
                res = _build_output(st, data.get("ids", []), out_dir)
                # 记住用户这次的选择（勾选项只影响「下次」，不改变本次结果）
                kw = {}
                if data.get("remember"):
                    kw["rememberDir"] = True
                    kw["saveDir"] = res["dir"]
                if data.get("noAsk"):
                    kw["rememberDir"] = True
                    kw["noAsk"] = True
                    kw["saveDir"] = res["dir"]
                if kw:
                    _update_settings(**kw)
                return self._json(res)
            if u.path == "/api/pickdir":
                data = json.loads(self._body() or b"{}")
                path, status = _pick_directory(
                    "选择打码后 PDF 的保存位置", data.get("initial") or "")
                return self._json({"path": path, "status": status})
            if u.path == "/api/settings":
                data = json.loads(self._body() or b"{}")
                kw = {}
                if isinstance(data.get("saveDir"), str):
                    kw["saveDir"] = data["saveDir"].strip().strip('"')
                if "rememberDir" in data:
                    kw["rememberDir"] = bool(data["rememberDir"])
                if "noAsk" in data:
                    kw["noAsk"] = bool(data["noAsk"])
                if data.get("lang") in ("zh", "en"):
                    kw["lang"] = data["lang"]
                cfg = _update_settings(**kw)
                return self._json({"ok": True, "settings": cfg,
                                   "path": SETTINGS_PATH})
            if u.path == "/api/check_update":
                # 只读 GitHub 上的版本号；用户主动点「检查更新」才会走到这里
                return self._json(check_update())
            if u.path == "/api/openurl":
                data = json.loads(self._body() or b"{}")
                link = (data.get("url") or "").strip()
                if not link.startswith(("http://", "https://")):
                    return self._err("链接无效")
                _browser_open(link)
                return self._json({"ok": True, "url": link})

            if u.path == "/api/copyout":
                data = json.loads(self._body() or b"{}")
                p = OUTS.get(data.get("token", ""))
                if not p or not os.path.exists(p):
                    return self._err("文件不存在", 404)
                folder, err = _ensure_dir(data.get("dir") or "")
                if err:
                    return self._err(err)
                base = os.path.splitext(os.path.basename(p))[0]
                dst = _unique_path(folder, base, "")
                shutil.copy2(p, dst)
                return self._json({"ok": True, "path": dst})
            if u.path in ("/api/openfile", "/api/showfolder"):
                tok = json.loads(self._body() or b"{}").get("token", "")
                p = OUTS.get(tok)
                if not p or not os.path.exists(p):
                    return self._err("文件不存在", 404)
                target = p if u.path == "/api/openfile" else os.path.dirname(p)
                os.startfile(target)  # noqa: S606  (Windows 本地打开)
                return self._json({"ok": True})
            if u.path == "/api/quit":
                self._json({"ok": True})
                threading.Thread(target=lambda: (time.sleep(0.3), _hard_exit(0)), daemon=True).start()
                return
        except Exception as e:
            return self._err(e, 500)
        self._err("not found", 404)

    def _upload(self):
        raw = self._body()
        if not raw:
            return self._err("没有收到文件")
        name = urllib.parse.unquote(self.headers.get("X-File-Name") or "document.pdf")
        name = os.path.basename(name) or "document.pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        did = uuid.uuid4().hex[:12]
        path = os.path.join(TMPROOT, did + ".pdf")
        with open(path, "wb") as fh:
            fh.write(raw)
        try:
            st = DocState(path, name)
        except Exception as e:
            return self._err("无法解析这个 PDF：%s" % e)
        st.doc_id = did
        DOCS[did] = st
        self._json(st.payload())

    def _open_path(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path) or not path.lower().endswith(".pdf"):
            return self._err("文件不存在或不是 PDF")
        try:
            st = DocState(path, os.path.basename(path))
        except Exception as e:
            return self._err("无法解析这个 PDF：%s" % e)
        st.doc_id = uuid.uuid4().hex[:12]
        DOCS[st.doc_id] = st
        self._json(st.payload())


HTML_UI = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PDF 隐私打码工具</title>
<style>
:root{
  --bg:#f4f5f7; --panel:#fff; --ink:#15181d; --ink2:#5b6472; --ink3:#8b94a3;
  --line:#e4e7ec; --line2:#eef0f3; --accent:#2f6bff; --accent-d:#1f4fd8;
  --danger:#e5484d; --ok:#12a150; --radius:14px;
}
*{box-sizing:border-box}
[hidden]{display:none !important}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 -apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;overflow:hidden}
button{font-family:inherit}
.app{height:100%;display:flex;flex-direction:column}
header{height:66px;flex:0 0 66px;display:flex;align-items:center;justify-content:space-between;
  padding:0 22px;background:#fff;border-bottom:1px solid var(--line);position:relative;z-index:5}
.brand{display:flex;align-items:center;gap:12px}
.logo{width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#2f6bff,#6a4cff);
  display:grid;place-items:center;color:#fff;box-shadow:0 4px 12px rgba(47,107,255,.28)}
.brand h1{font-size:15.5px;margin:0;line-height:1.3;letter-spacing:.2px}
.brand p{margin:2px 0 0;font-size:11.5px;color:var(--ink3);line-height:1.2}
.top-right{display:flex;align-items:center;gap:12px}
.quit{font-size:12px;color:var(--ink3);cursor:pointer;padding:5px 9px;border-radius:8px;border:1px solid transparent}
.quit:hover{background:#f5f6f8;color:var(--danger);border-color:var(--line)}
.about-link{font-size:12px;color:var(--ink3);cursor:pointer;padding:5px 9px;border-radius:8px;border:1px solid transparent}
.about-link:hover{background:#f5f6f8;color:var(--ink);border-color:var(--line)}
/* ---------- 关于 ---------- */
.about-mask{position:fixed;inset:0;background:rgba(20,24,32,.42);backdrop-filter:blur(2px);
  display:grid;place-items:center;z-index:400;padding:24px}
.about-box{width:min(520px,100%);max-height:88vh;overflow:auto;background:#fff;border-radius:16px;
  padding:26px 28px 22px;box-shadow:0 30px 70px -30px rgba(15,24,40,.5)}
.about-box h3{margin:0 0 3px;font-size:17px;letter-spacing:.2px}
.about-box .ver{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--ink3)}
.about-box dl{margin:16px 0 0;display:grid;grid-template-columns:88px 1fr;gap:9px 12px;font-size:12.5px}
.about-box dt{color:var(--ink3)}
.about-box dd{margin:0;color:var(--ink);word-break:break-word}
.about-note{margin:16px 0 0;padding:12px 14px;background:#f7f9fc;border-left:2px solid var(--accent);
  font-size:12px;line-height:1.75;color:var(--ink2);border-radius:0 8px 8px 0}
.about-note b{color:var(--ink)}
.about-box dd.url{cursor:pointer;color:var(--accent);border-bottom:1px dashed rgba(47,107,255,.4);
  display:inline-block;max-width:100%}
.about-box dd.url:hover{color:#1a4fd6}
.about-thanks{margin:14px 0 0;padding:14px;border:1px solid var(--line);border-radius:12px}
.about-thanks b{display:block;font-size:12.5px;color:var(--ink);margin-bottom:6px}
.about-thanks p{margin:0 0 10px;font-size:11.5px;line-height:1.65;color:var(--ink3)}
.about-thanks img{display:block;width:236px;max-width:100%;height:auto;margin:0 auto;border-radius:8px}
.thanks-cap{margin-top:8px;font-size:10.5px;color:var(--ink3);text-align:center}
.thanks-save-row{display:flex;justify-content:center;margin-top:9px}
.thanks-save-row .btn{padding:5px 16px;font-size:11.5px}
.about-rule{margin:14px 0 0;padding:12px 14px 10px;background:#fff8f0;border:1px solid #f3dfc4;
  border-radius:10px;font-size:12px;line-height:1.7;color:#7a5320}
.about-rule b{color:#8a4f00;font-size:12.5px}
.about-rule ol{margin:7px 0 0;padding-left:18px}
.about-rule li{margin:3px 0}
.about-rule em{font-style:normal;color:#8a4f00;font-weight:600;word-break:break-all}
.about-rule .rule-foot{margin:8px 0 0;color:#96703c;font-size:11.5px}
.about-rule code{font-family:ui-monospace,Consolas,monospace;font-size:11px;
  background:#fdf3e5;padding:1px 4px;border-radius:4px}
.about-actions{margin-top:18px;display:flex;justify-content:flex-end;gap:8px}
.badge-local{display:flex;align-items:center;gap:7px;font-size:12px;color:#0f7b45;
  background:#e9f8f0;border:1px solid #c9eddb;padding:6px 12px;border-radius:99px}
.dot{width:6px;height:6px;border-radius:50%;background:#12a150;box-shadow:0 0 0 3px rgba(18,161,80,.15)}

main{flex:1;min-height:0;display:flex;overflow:hidden}
/* ---------- 上传态 ---------- */
.drop-view{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:30px}
.drop-card{width:min(620px,92%);background:#fff;border:2px dashed #d6dbe4;border-radius:22px;
  padding:48px 32px;text-align:center;transition:.18s;cursor:pointer}
.drop-card:hover,.drop-card.over{border-color:var(--accent);background:#f7faff;
  box-shadow:0 18px 40px -22px rgba(47,107,255,.45)}
.drop-card h2{font-size:19px;margin:16px 0 6px}
.drop-card p{color:var(--ink2);margin:0 0 20px;font-size:13px}
.ico{width:64px;height:64px;margin:0 auto;border-radius:18px;background:#eef3ff;display:grid;place-items:center}
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;border-radius:10px;border:1px solid var(--line);
  background:#fff;color:var(--ink);font-size:13px;cursor:pointer;transition:.15s;white-space:nowrap}
.btn:hover{background:#f7f8fa;border-color:#d3d8e0}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 6px 16px -6px rgba(47,107,255,.6)}
.btn.primary:hover{background:var(--accent-d)}
.btn.ghost{background:transparent}
.btn:disabled{opacity:.5;cursor:not-allowed}
.tips{display:flex;gap:26px;color:var(--ink3);font-size:12px;flex-wrap:wrap;justify-content:center}
.tips span{display:flex;align-items:center;gap:6px}
.credit{font-size:11.5px;color:#a2aab8;text-align:center;line-height:1.7;max-width:620px}
.credit span{display:block}
.credit .credit-url{color:#8b93a3;font-size:11px;margin-top:2px;cursor:pointer;
  word-break:break-all;transition:color .15s}
.credit .credit-url:hover{color:#2f6bff}
/* ---------- 工作态 ---------- */
.work-view{flex:1;min-height:0;display:flex}
.side{width:352px;flex:0 0 352px;background:#fff;border-right:1px solid var(--line);
  display:flex;flex-direction:column;min-height:0}
.file-card{padding:14px 16px;border-bottom:1px solid var(--line2);display:flex;gap:11px;align-items:flex-start}
.file-ico{width:36px;height:36px;border-radius:9px;background:#fff1f1;color:var(--danger);
  display:grid;place-items:center;font-size:10px;font-weight:700;flex:0 0 36px}
.file-meta{min-width:0;flex:1}
.file-name{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-sub{font-size:11.5px;color:var(--ink3);margin-top:2px}
.stats{padding:12px 16px;display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--line2)}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;padding:3px 9px;border-radius:99px;
  background:#f4f6f9;color:#3d4655;border:1px solid var(--line)}
.chip b{font-weight:700}
.chip i{width:6px;height:6px;border-radius:50%;display:inline-block}
.list-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px 8px;
  font-size:12px;color:var(--ink2)}
.link{color:var(--accent);cursor:pointer;font-size:12px;background:none;border:0;padding:2px 4px}
.link:hover{text-decoration:underline}
.list{flex:1;overflow:auto;padding:0 8px 14px}
.grp{font-size:11px;color:var(--ink3);padding:10px 8px 4px;letter-spacing:.3px}
.row{display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:9px;cursor:pointer;
  border:1px solid transparent}
.row:hover{background:#f7f9fc}
.row.on{background:#f2f6ff;border-color:#dbe6ff}
.row input{accent-color:var(--accent);width:15px;height:15px;margin:0;cursor:pointer;flex:0 0 15px}
.badge{font-size:11px;padding:2px 7px;border-radius:6px;background:#f1f3f7;color:#4a5361;
  flex:0 0 auto;font-weight:500}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#3d4655;
  flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sus{flex:0 0 auto;font-size:10px;padding:1px 6px;border-radius:5px;color:#a15c00;
  background:#fff3d6;border:1px solid #ffe0a3}
.pg{font-size:10.5px;color:var(--ink3);flex:0 0 auto}
.empty{padding:40px 18px;text-align:center;color:var(--ink3);font-size:12.5px}
/* viewer */
.viewer{flex:1;min-width:0;display:flex;flex-direction:column;background:#eceef2}
.toolbar{height:48px;flex:0 0 48px;background:#fff;border-bottom:1px solid var(--line);
  display:flex;align-items:center;gap:8px;padding:0 16px}
.tb-group{display:flex;align-items:center;gap:4px;background:#f4f6f9;border:1px solid var(--line);
  border-radius:9px;padding:2px}
.tb-btn{border:0;background:transparent;color:#3d4655;padding:5px 9px;border-radius:7px;cursor:pointer;font-size:12.5px}
.tb-btn:hover{background:#fff;color:var(--ink)}
.tb-btn:disabled{opacity:.35;cursor:default;background:transparent}
.tb-btn.active{background:#fff;color:var(--accent);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.pgnum{font-size:12.5px;color:var(--ink2);min-width:64px;text-align:center}
.spacer{flex:1}
.switch{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--ink2);cursor:pointer;
  user-select:none}
.switch input{display:none}
.track{width:34px;height:19px;border-radius:99px;background:#d5d9e0;position:relative;transition:.18s}
.track::after{content:"";position:absolute;top:2px;left:2px;width:15px;height:15px;border-radius:50%;
  background:#fff;transition:.18s;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.switch input:checked + .track{background:var(--accent)}
.switch input:checked + .track::after{transform:translateX(15px)}
.canvas-wrap{flex:1;overflow:auto;padding:22px;display:flex;justify-content:center;align-items:flex-start;
  position:relative}
.canvas-wrap.draw{cursor:crosshair}
/* 顶部功能提示：能拖框、能双击取消 */
.hint-chip{display:flex;align-items:center;gap:5px;font-size:11.5px;color:#5b6675;
  background:#f4f6f9;border:1px solid var(--line);border-radius:8px;padding:4px 10px;
  white-space:nowrap;user-select:none}
.hint-chip svg{flex:0 0 12px;opacity:.75}
@media (max-width: 1040px){ .hint-chip{display:none} }
.canvas-wrap img{display:block;background:#fff;box-shadow:0 8px 30px -12px rgba(15,24,40,.28);
  border-radius:2px;user-select:none;-webkit-user-drag:none}
.band{position:fixed;border:1.5px dashed #ff2d55;background:rgba(255,45,85,.12);pointer-events:none;z-index:99}
/* action bar */
.actionbar{flex:0 0 66px;height:66px;background:#fff;border-top:1px solid var(--line);
  display:flex;align-items:center;gap:14px;padding:0 22px}
.sum{font-size:13px;color:var(--ink2)}
.sum b{color:var(--ink);font-size:15px}
/* overlay / toast / result */
.overlay{position:fixed;inset:0;background:rgba(244,245,247,.82);backdrop-filter:blur(3px);
  display:grid;place-items:center;z-index:200}
.overlay .box{background:#fff;border-radius:16px;padding:26px 34px;text-align:center;
  box-shadow:0 24px 60px -24px rgba(15,24,40,.4);min-width:260px}
.spin{width:32px;height:32px;border:3px solid #e3e8f0;border-top-color:var(--accent);border-radius:50%;
  margin:0 auto 14px;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.ov-text{font-size:13.5px;color:var(--ink2)}
.toast{position:fixed;left:50%;bottom:84px;transform:translate(-50%,14px);background:#15181d;color:#fff;
  padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;transition:.22s;z-index:300;pointer-events:none;
  max-width:80vw}
.toast.show{opacity:1;transform:translate(-50%,0)}
.toast.err{background:#b42318}
.result{position:fixed;inset:0;background:rgba(15,24,40,.42);display:grid;place-items:center;z-index:250}
.result .card{background:#fff;border-radius:18px;padding:30px 34px;width:min(520px,92%);
  box-shadow:0 30px 70px -30px rgba(0,0,0,.5);text-align:center}
.result h3{margin:14px 0 6px;font-size:18px}
.result .path{font-size:12px;color:var(--ink2);background:#f4f6f9;border:1px solid var(--line);
  border-radius:9px;padding:10px;word-break:break-all;margin:12px 0 18px;text-align:left;
  font-family:ui-monospace,Consolas,monospace}
.ok-ico{width:56px;height:56px;border-radius:50%;background:#e7f8ef;color:var(--ok);
  display:grid;place-items:center;margin:0 auto}
.res-actions{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.warn{background:#fff8e8;border:1px solid #f6e2b3;color:#8a5a00;font-size:12px;padding:8px 12px;
  border-radius:9px;margin:10px 16px 0;line-height:1.5}
/* ---------- 扫描件提示（左上角红字） ---------- */
.nocap{display:inline-block;margin-left:9px;font-size:10.5px;font-weight:700;line-height:1.5;
  color:#e5484d;background:#fdecee;border:1px solid #f7c6cb;border-radius:5px;padding:0 6px;
  vertical-align:1.5px;letter-spacing:.3px;white-space:nowrap;cursor:default}
.brand .hint-draw{color:#b4423f}
/* ---------- 通用弹窗 ---------- */
.modal-mask{position:fixed;inset:0;background:rgba(20,24,32,.42);backdrop-filter:blur(2px);
  display:grid;place-items:center;z-index:420;padding:24px}
.modal{width:min(520px,100%);max-height:88vh;overflow:auto;background:#fff;border-radius:16px;
  padding:22px 24px 18px;box-shadow:0 30px 70px -30px rgba(15,24,40,.5)}
.modal h3{margin:0 0 4px;font-size:16.5px;letter-spacing:.2px}
.modal .sub{color:var(--ink3);font-size:12px;margin:0 0 16px;line-height:1.6}
.field-label{display:block;font-size:12px;color:var(--ink2);margin-bottom:7px}
.path-row{display:flex;gap:8px}
.path-input{flex:1;min-width:0;border:1px solid var(--line);border-radius:10px;padding:9px 11px;
  font:12.5px/1.4 ui-monospace,Consolas,monospace;color:var(--ink);background:#fbfcfd}
.path-input:focus{outline:none;border-color:var(--accent);background:#fff;
  box-shadow:0 0 0 3px rgba(47,107,255,.12)}
.path-input::placeholder{color:#aab2be}
.chk{display:flex;align-items:flex-start;gap:9px;font-size:12.5px;color:var(--ink2);
  margin-top:13px;cursor:pointer;line-height:1.55;user-select:none}
.chk input{appearance:none;-webkit-appearance:none;width:16px;height:16px;flex:0 0 16px;
  margin:1px 0 0;border:1.5px solid #c9d0da;border-radius:5px;cursor:pointer;position:relative;
  background:#fff;transition:.15s}
.chk:hover input{border-color:#a9b4c4}
.chk input:checked{background:var(--accent);border-color:var(--accent)}
.chk input:checked::after{content:"";position:absolute;left:4.6px;top:1.6px;width:4px;height:8px;
  border:solid #fff;border-width:0 2px 2px 0;transform:rotate(42deg)}
.chk b{color:var(--ink);font-weight:600}
.modal-actions{margin-top:20px;display:flex;justify-content:flex-end;gap:9px}
.modal-note{margin-top:15px;padding:9px 12px;background:#f7f9fc;border-radius:9px;
  font-size:11.5px;color:var(--ink3);line-height:1.7}
.modal-note em{font-style:normal;color:var(--ink2)}
/* ---------- 设置：语言 / 检查更新 ---------- */
.set-sec{margin-top:16px;padding-top:14px;border-top:1px solid var(--line2)}
.seg{display:flex;gap:3px;background:#f1f3f7;border-radius:10px;padding:3px}
.seg-btn{flex:1;border:0;background:transparent;padding:8px 0;border-radius:8px;
  font-size:12.5px;color:var(--ink2);cursor:pointer}
.seg-btn.on{background:#fff;color:var(--ink);font-weight:600;box-shadow:0 1px 2px rgba(16,24,40,.08)}
.ver-row{display:flex;align-items:center;gap:10px;justify-content:space-between}
.ver-cur{font-size:12.5px;color:var(--ink2)}
.ver-cur b{color:var(--ink)}
.upd-box{margin-top:10px;padding:11px 12px;border-radius:10px;background:#f7f9fc;
  border:1px solid var(--line2);font-size:12px;line-height:1.7;color:var(--ink2)}
.upd-box.ok{background:#f2fbf5;border-color:#cdeed9}
.upd-box.new{background:#f2f6ff;border-color:#d5e2ff}
.upd-box.fail{background:#fff6f6;border-color:#f7d4d4}
.upd-url{margin-top:7px;font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:var(--ink);
  word-break:break-all;background:#fff;border:1px solid var(--line);border-radius:7px;
  padding:6px 8px;user-select:all;cursor:text}
.upd-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.upd-help{margin-top:9px;font-size:11.5px;color:var(--ink3);line-height:1.8}
.upd-detail{margin-top:5px;font-size:11px;color:var(--ink3);word-break:break-all;line-height:1.6}
.upd-help b{color:var(--ink2)}
.upd-help ol{margin:6px 0 0;padding-left:18px}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand">
      <div class="logo">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1"
             stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 3l7 3v6c0 4.5-3 7.7-7 9-4-1.3-7-4.5-7-9V6l7-3z"/><path d="M9 12l2 2 4-4"/>
        </svg>
      </div>
      <div>
        <h1>PDF 隐私打码工具<span class="nocap" title="扫描件是纯图片、没有文字层，无法自动识别，请用「框选手动打码」">不支持扫描件 PDF</span></h1>
        <p>真马赛克 · 全程本地零上传 · <span class="hint-draw">扫描件可用「框选手动打码」</span></p>
      </div>
    </div>
    <div class="top-right">
      <div class="badge-local"><span class="dot"></span>本机运行 127.0.0.1，文件不出电脑</div>
      <div class="about-link" id="setBtn">设置</div>
      <div class="about-link" id="aboutBtn">关于</div>
      <div class="quit" id="quitBtn" title="关闭程序">退出</div>
    </div>
  </header>

  <main>
    <section class="drop-view" id="dropView">
      <div class="drop-card" id="dropCard">
        <div class="ico">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#2f6bff" stroke-width="1.7"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z"/>
            <path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/>
          </svg>
        </div>
        <h2>把 PDF 拖到这里</h2>
        <p>自动识别手机号、身份证号、银行卡号、邮箱、姓名、座机、地址、出生日期、性别年龄</p>
        <button class="btn primary" id="pickBtn">选择 PDF 文件</button>
        <input type="file" id="fileInput" accept=".pdf,application/pdf" hidden>
      </div>
      <div class="tips">
        <span>· 不上传服务器</span><span>· 原文不可还原</span><span>· 版面保持一致</span>
        <span>· 原文件不改动</span><span>· 保存位置可自定义</span>
      </div>
      <div class="credit">
        <span>__CREDIT__</span>
        <span class="credit-url" id="footUrl" data-url="__URL__" title="点击复制原项目地址">原项目地址：__URLSHORT__</span>
      </div>
    </section>

    <section class="work-view" id="workView" hidden>
      <aside class="side">
        <div class="file-card">
          <div class="file-ico">PDF</div>
          <div class="file-meta">
            <div class="file-name" id="fName">-</div>
            <div class="file-sub" id="fSub">-</div>
          </div>
          <button class="btn ghost" id="reupload" title="重新选择文件" style="padding:6px 10px">换</button>
        </div>
        <div class="stats" id="stats"></div>
        <div class="warn" id="scanWarn" hidden></div>
        <div class="list-head">
          <span>识别结果 <b id="totalCnt">0</b> 处</span>
          <span><button class="link" id="selAll">全选</button> / <button class="link" id="selNone">全不选</button></span>
        </div>
        <div class="list" id="list"></div>
      </aside>

      <div class="viewer">
        <div class="toolbar">
          <div class="tb-group">
            <button class="tb-btn" id="prevPage" title="上一页">‹</button>
            <span class="pgnum" id="pgNum">1 / 1</span>
            <button class="tb-btn" id="nextPage" title="下一页">›</button>
          </div>
          <div class="tb-group">
            <button class="tb-btn" id="zoomOut">−</button>
            <span class="pgnum" id="zoomTxt" style="min-width:44px">120%</span>
            <button class="tb-btn" id="zoomIn">+</button>
          </div>
          <button class="tb-btn" id="drawBtn" style="border:1px solid var(--line);background:#fff;border-radius:9px;padding:6px 11px">
            框选手动打码
          </button>
          <div class="spacer"></div>
          <div class="hint-chip" title="按住鼠标拖动可以框出要打码的区域；双击页面上的方框，可以取消或恢复该处打码">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>
              <path d="M12 11v5"/><path d="M12 8h.01"/></svg>
            拖动框选 · 双击方框取消/恢复打码
          </div>
          <label class="switch">
            <input type="checkbox" id="maskPreview" checked><span class="track"></span>预览打码效果
          </label>
        </div>
        <div class="canvas-wrap" id="canvasWrap">
          <img id="pageImg" alt="页面预览">
        </div>
      </div>
    </section>
  </main>

  <div class="actionbar" id="actionBar" hidden>
    <div class="sum">已选 <b id="selCount">0</b> 处 · 生成后原文将被永久打散</div>
    <div class="spacer"></div>
    <button class="btn" id="backBtn">重新选择文件</button>
    <button class="btn primary" id="goBtn">生成打码 PDF</button>
  </div>
</div>

<div class="overlay" id="overlay" hidden>
  <div class="box"><div class="spin"></div><div class="ov-text" id="ovText">处理中…</div></div>
</div>
<div class="toast" id="toast"></div>

<div class="about-mask" id="aboutMask" hidden>
  <div class="about-box">
    <h3>PDF 隐私打码工具</h3>
    <div class="ver">版本 __VERSION__ · <span id="verNote">本地离线运行</span></div>
    <dl>
      <dt>指导作者</dt><dd>__AUTHOR__。<br>需求、识别规则的设计、验收测试全部由本人完成。</dd>
      <dt>开发</dt><dd>__DEVELOPER__</dd>
      <dt>开源协议</dt><dd>__LICENSE__</dd>
      <dt>原项目地址</dt><dd class="url" id="aboutUrl" data-url="__URL__" title="点击复制">__URL__</dd>
    </dl>
    <p class="about-note" data-en-html='<b>Maintenance:</b> I don’t usually have enough time or energy, so I only check in once every month or two — replies will be slow, don’t expect instant answers. All the code is public: if something doesn’t work for you, feel free to fix it or keep building on it. Commercial use is fine too — no fee, no need to ask me, just follow the three points below.'>
      <b>关于维护：</b>我平时没有充足的时间和精力，大概一两个月才上来看一两次，
      所以回复不会很快，别指望秒回。代码全部公开，修不动的地方欢迎你自己改、自己接着用；
      商用也行，不用付钱也不用问我，照下面三条做就可以。
    </p>
    <div class="about-rule" data-en-html='<b>Forks / commercial use: three requirements</b><ol><li>Keep the credit <em>Advisor: __AUTHOR__</em> and the developer line, unmodified.</li><li>Show the <em>upstream URL</em> where users can see it — the line just above in this window counts.</li><li>Modified builds must state: “Based on that project, not released by the original author.”</li></ol><p class="rule-foot">The above is the additional term under AGPL-3.0 section 7(b); the full text is in <code>ADDITIONAL-TERMS.md</code>. The license itself also requires you to publish the modified source and, for network services, offer that source to users. The program name and icon are not licensed — rename before republishing.</p>'>
      <b>二次开发 / 商用：三条硬要求</b>
      <ol>
        <li>保留署名 <em>指导作者：__AUTHOR__</em> 与开发者信息，不得删改。</li>
        <li>在程序里标注<em>原项目地址</em>，让使用者看得见——本窗口上方那行就是。</li>
        <li>改动过的版本必须注明「本程序基于该地址修改，非原作者发布」。</li>
      </ol>
      <p class="rule-foot">
        以上依据 AGPL-3.0 第 7 条(b) 附加条款，全文见开源包 <code>ADDITIONAL-TERMS.md</code>。
        另外协议本身要求：修改后的源码也要一并开放，网络服务须向使用者提供源码。
        程序名称与图标不在授权范围内，二次发布请改名。
      </p>
    </div>
    <div class="about-thanks">
      <b>如果这个工具帮到了你</b>
      <p data-en-html='It started as a small side project, and I am glad it is useful. If you feel like buying me a milk tea, that would make my day — completely optional. The app stays free and fully featured either way.'>本来就是顺手做的小工具，能派上用场就挺好。要是你愿意请我喝杯奶茶，我会挺开心——
      完全自愿，不打赏也一样免费、功能不缺。</p>
      <img id="thanksQr" src="data:image/png;base64,__THANKS__" alt="赞赏码">
      <div class="thanks-cap">微信扫码 · 金额随意 · 点下面的按钮保存图片</div>
      <div class="thanks-save-row"><button class="btn" id="thanksSave">保存赞赏码</button></div>
    </div>
    <div class="about-actions"><button class="btn primary" id="aboutOk">知道了</button></div>
  </div>
</div>

<div class="modal-mask" id="saveMask" hidden>
  <div class="modal">
    <h3>选择保存位置</h3>
    <p class="sub">打码后的 PDF 会存到这个文件夹，原文件不会被改动。</p>
    <label class="field-label">保存到</label>
    <div class="path-row">
      <input class="path-input" id="savePath" spellcheck="false" placeholder="点右侧「浏览」选一个文件夹">
      <button class="btn" id="saveBrowse">浏览…</button>
    </div>
    <label class="chk"><input type="checkbox" id="optRemember"><span><b>下次默认使用这个路径</b>　以后打开就停在这个文件夹</span></label>
    <label class="chk"><input type="checkbox" id="optNoAsk"><span><b>不再询问</b>　以后直接存到这里，不再弹这个窗口</span></label>
    <div class="modal-note">两个勾选随时能在右上角<em>「设置」</em>里改。都不勾也没关系，下次还会再问一次。</div>
    <div class="modal-actions">
      <button class="btn ghost" id="saveCancel">取消</button>
      <button class="btn primary" id="saveOk">确定</button>
    </div>
  </div>
</div>

<div class="modal-mask" id="setMask" hidden>
  <div class="modal">
    <h3>设置</h3>
    <p class="sub">默认保存位置就是打码文件存放的地方。留空则自动跟随原 PDF 所在的文件夹。</p>
    <label class="field-label">默认保存位置</label>
    <div class="path-row">
      <input class="path-input" id="setPath" spellcheck="false" placeholder="留空 = 跟随原 PDF 所在文件夹">
      <button class="btn" id="setBrowse">浏览…</button>
    </div>
    <label class="chk"><input type="checkbox" id="setAsk"><span><b>每次生成前，先问我保存到哪里</b>　最稳妥，不会存到想不到的地方</span></label>
    <div class="modal-note">
      取消上面那个勾选，程序就会一路静默保存到这里的文件夹，不再弹窗。<br>
      无论怎么设置，原 PDF 都只会被读取，不会被改动或删除。
    </div>

    <div class="set-sec">
      <label class="field-label">界面语言 / Language</label>
      <div class="seg" id="langSeg">
        <button class="seg-btn" data-lang="zh">中文</button>
        <button class="seg-btn" data-lang="en">English</button>
      </div>
    </div>

    <div class="set-sec">
      <label class="field-label">版本与更新</label>
      <div class="ver-row">
        <span class="ver-cur"><span id="verLabel1">当前版本</span> v<b id="curVer">__VERSION__</b> ·
          <span id="verLabel2">仓库最新</span> <b id="latestVer">—</b></span>
        <button class="btn" id="checkBtn">检查更新</button>
      </div>
      <div class="upd-box" id="updBox" hidden>
        <div id="updText"></div>
        <div class="upd-detail" id="updDetail" hidden></div>
        <div class="upd-url" id="updUrl" hidden></div>
        <div class="upd-actions" id="updActions" hidden>
          <button class="btn primary" id="updOpen">用浏览器打开下载</button>
          <button class="btn" id="updCopy">复制链接</button>
        </div>
        <div class="upd-help" id="updHelp" hidden></div>
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn ghost" id="setReset">恢复默认</button>
      <button class="btn primary" id="setOk">保存</button>
    </div>
  </div>
</div>

<script>
const TOKEN = "__TOKEN__";
const BOOT = __BOOT__;
const S = {docId:null, name:'', pages:[], findings:[], sel:new Set(), page:0, zoom:1.2,
           mask:true, drawing:false, hi:null, scanned:[], outDir:'', stats:null, size:0};

const $ = id => document.getElementById(id);

/* ---------- 中英双语 ----------
   静态文字按「原文」查表替换（含 title / placeholder / alt），
   动态提示走 T(中文, English)。切换立即生效，不用重启。 */
let LANG = 'zh';
const DICT = {
  '设置':'Settings', '关于':'About', '退出':'Quit',
  'PDF 隐私打码工具':'PDF Privacy Masker',
  '不支持扫描件 PDF':'No scanned PDFs',
  '真马赛克 · 全程本地零上传 · ':'Real mosaic · 100% local · ',
  '扫描件可用「框选手动打码」':'for scans, use the manual box tool',
  '本机运行 127.0.0.1，文件不出电脑':'Local 127.0.0.1 — files never leave your PC',
  '把 PDF 拖到这里':'Drop a PDF here',
  '自动识别手机号、身份证号、银行卡号、邮箱、姓名、座机、地址、出生日期、性别年龄':
    'Detects phone numbers, ID numbers, bank cards, emails, names, landlines, addresses, birth dates, gender and age',
  '选择 PDF 文件':'Choose a PDF',
  '· 不上传服务器':'· No uploads', '· 原文不可还原':'· Text unrecoverable',
  '· 版面保持一致':'· Layout kept', '· 原文件不改动':'· Original untouched',
  '· 保存位置可自定义':'· Choose where to save',
  '换':'Swap', '识别结果 ':'Detected ', ' 处':' items',
  '全选':'All', '全不选':'None',
  '框选手动打码':'Draw a box',
  '拖动框选 · 双击方框取消/恢复打码':'Drag to draw · double-click a box to mute/unmute',
  '预览打码效果':'Preview mosaic',
  '已选 ':'Selected ', ' 处 · 生成后原文将被永久打散':' items · text will be destroyed for good',
  '重新选择文件':'Choose another file', '生成打码 PDF':'Generate masked PDF',
  '处理中…':'Working…',
  '指导作者':'Advisor', '开发':'Built by', '开源协议':'License', '原项目地址':'Upstream',
  '本地离线运行':'runs fully offline',
  '腾讯 WorkBuddy × DeepSeek-V4.1-Flash':'Tencent WorkBuddy × DeepSeek-V4.1-Flash',
  '需求、识别规则的设计、验收测试全部由本人完成。':
    'Requirements, detection rule design and acceptance testing were all done by the author.',
  '如果这个工具帮到了你':'If this tool helped you',
  '本来就是顺手做的小工具，能派上用场就挺好。要是你愿意请我喝杯奶茶，我会挺开心——':
    'It started as a small side project, and I am glad it is useful. If you feel like buying me a milk tea, that would make my day —',
  '完全自愿，不打赏也一样免费、功能不缺。':
    'completely optional. The app stays free and fully featured either way.',
  '微信扫码 · 金额随意 · 点下面的按钮保存图片':'Scan in WeChat · any amount · use the button below to save',
  '保存赞赏码':'Save the tip QR',
  '赞赏码':'Tip QR code', '知道了':'Got it', '点击复制':'Click to copy',
  '点击复制原项目地址':'Click to copy the upstream URL',
  '选择保存位置':'Choose a folder', '打码后的 PDF 会存到这个文件夹，原文件不会被改动。':
    'The masked PDF goes into this folder; the original is never modified.',
  '保存到':'Save to', '点右侧「浏览」选一个文件夹':'Pick a folder with “Browse”',
  '浏览…':'Browse…', '下次默认使用这个路径':'Remember this folder',
  '不再询问':'Don\'t ask again',
  '以后打开就停在这个文件夹':'next time we start here',
  '以后直接存到这里，不再弹这个窗口':'save straight here from now on',
  '最稳妥，不会存到想不到的地方':'safest — never lands somewhere unexpected',
  '两个勾选随时能在右上角':'Both toggles can be changed anytime under ',
  '「设置」':'“Settings”',
  '里改。都不勾也没关系，下次还会再问一次。':' at the top right. Leaving them unticked is fine — we will ask again next time.',
  '取消':'Cancel', '确定':'OK',
  '默认保存位置就是打码文件存放的地方。留空则自动跟随原 PDF 所在的文件夹。':
    'The default folder is where masked PDFs go. Leave it empty to follow the original PDF.',
  '默认保存位置':'Default save folder', '留空 = 跟随原 PDF 所在文件夹':'Empty = follow the original PDF',
  '每次生成前，先问我保存到哪里':'Ask me where to save before each run',
  '取消上面那个勾选，程序就会一路静默保存到这里的文件夹，不再弹窗。':
    'Untick the box above and the app saves here silently, with no dialog.',
  '无论怎么设置，原 PDF 都只会被读取，不会被改动或删除。':
    'Whatever you choose, the original PDF is only ever read — never modified or deleted.',
  '恢复默认':'Reset', '保存':'Save',
  '版本与更新':'Version & updates', '当前版本':'Current', '仓库最新':'latest',
  '检查更新':'Check for updates', '用浏览器打开下载':'Open download in browser',
  '复制链接':'Copy link',
  '扫描件是纯图片、没有文字层，无法自动识别，请用「框选手动打码」':
    'A scan is just an image with no text layer, so it cannot be detected — use the manual box tool',
  '按住鼠标拖动可以框出要打码的区域；双击页面上的方框，可以取消或恢复该处打码':
    'Hold and drag to draw a box; double-click a box on the page to mute or unmute it',
  '重新选择文件':'Choose another file',
  '关闭程序':'Quit'
};
// 文本节点会被 trim 过再查表，所以键也统一去空白，省得结尾多个空格就漏译
const TK = {};
Object.keys(DICT).forEach(k=>{ TK[k.trim()] = DICT[k]; });

const PREFIX = [
  ['版本 ', 'Version '],
  ['项目创作时为初中生', 'Was a junior high school student when this project was created'],
  ['原项目地址：', 'Upstream: ']
];
const TYPE_EN = {phone:'Phone', idcard:'ID number', bankcard:'Bank card', email:'Email',
  name:'Name', tel:'Landline', address:'Address', birth:'Birth date', gender:'Gender',
  age:'Age', manual:'Manual box'};
const STAT_EN = {'身份证号':'ID number','银行卡号':'Bank card','手机号':'Phone','座机号':'Landline',
  '邮箱':'Email','姓名':'Name','地址':'Address','出生日期':'Birth date','性别':'Gender',
  '年龄':'Age','手动框选':'Manual'};

function T(zh, en){ return LANG === 'en' ? en : zh; }
function labelOf(f){
  if (LANG !== 'en') return f.label;
  return TYPE_EN[f.type] || f.label;
}
const ORIG_TEXT = new WeakMap();
function trNode(node){
  if(!ORIG_TEXT.has(node)) ORIG_TEXT.set(node, node.nodeValue);
  const raw = ORIG_TEXT.get(node);
  const s = raw.trim();
  if(!s) return;
  let out = TK[s];
  if(out === undefined){
    for(const [zh, en] of PREFIX){
      if(s.indexOf(zh) === 0){ out = en + s.slice(zh.length); break; }
    }
  }
  if(out === undefined){ node.nodeValue = raw; return; }
  const lead = raw.match(/^\s*/)[0], tail = raw.match(/\s*$/)[0];
  node.nodeValue = LANG === 'en' ? (lead + out + tail) : raw;
}
function applyLang(){
  // 含行内标签的整段文字，直接整块换成另一种语言（原文存进 dataset，切回来能还原）
  document.querySelectorAll('[data-en-html]').forEach(el=>{
    if(el.dataset.zhHtml === undefined) el.dataset.zhHtml = el.innerHTML;
    el.innerHTML = LANG === 'en' ? el.dataset.enHtml : el.dataset.zhHtml;
  });
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(n){
      const p = n.parentNode;
      if(!p) return NodeFilter.FILTER_REJECT;
      if(p.nodeName === 'SCRIPT' || p.nodeName === 'STYLE') return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }
  });
  let n; while((n = tw.nextNode())) trNode(n);
  document.querySelectorAll('[title],[placeholder],[alt]').forEach(el=>{
    ['title','placeholder','alt'].forEach(a=>{
      if(!el.hasAttribute(a)) return;
      const key = 'i18n' + a;
      if(el.dataset[key] === undefined) el.dataset[key] = el.getAttribute(a);
      const zh = el.dataset[key];
      el.setAttribute(a, LANG === 'en' ? (DICT[zh] || zh) : zh);
    });
  });
  document.documentElement.lang = LANG === 'en' ? 'en' : 'zh-CN';
  document.title = T('PDF 隐私打码工具', 'PDF Privacy Masker');
  document.querySelectorAll('.seg-btn').forEach(b=>b.classList.toggle('on', b.dataset.lang === LANG));
  renderMeta(); renderList(); renderStats(S.stats); syncBar(); renderUpdate();
}

const TYPE_COLOR = {phone:'#f59e0b', idcard:'#e5484d', bankcard:'#7c5cff', email:'#12a150',
  name:'#2f6bff', tel:'#ea580c', address:'#0aa2c0', birth:'#d6409f', gender:'#78808c',
  age:'#78808c', manual:'#111827'};

function esc(s){return (s+'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function toast(msg, err){
  const t = $('toast'); t.textContent = msg; t.className = 'toast show' + (err?' err':'');
  clearTimeout(t._h); t._h = setTimeout(()=>{t.className='toast';}, 2600);
}
/* 复制原项目地址（附加条款要求它必须可见、可留存） */
function copyText(text, okMsg){
  const done = ()=> toast(okMsg + text);
  const fallback = ()=>{
    try{
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position='fixed'; ta.style.opacity='0';
      document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta); done();
    }catch(e){ toast(T('复制失败，请手动记下：', 'Copy failed — write this down: ') + text, true); }
  };
  if (navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  } else fallback();
}
function copyProjectUrl(el){
  copyText(el.dataset.url || el.textContent, T('已复制项目地址：', 'Link copied: '));
}
function overlay(on, text){
  $('overlay').hidden = !on; if (text) $('ovText').textContent = text;
}
async function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({'X-Token':TOKEN}, opts.headers||{});
  const r = await fetch(path, opts);
  const ct = r.headers.get('content-type')||'';
  if (!r.ok){
    let m = T('请求失败', 'Request failed') + ' (' + r.status + ')';
    try{ const j = await r.json(); m = j.error||m; }catch(e){}
    throw new Error(m);
  }
  return ct.indexOf('json')>=0 ? r.json() : r;
}

/* ---------- 上传 / 打开 ---------- */
async function uploadFile(file){
  if(!file) return;
  if(!/\.pdf$/i.test(file.name)) return toast(T('只支持 PDF 文件', 'PDF files only'), true);
  overlay(true, T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const r = await fetch('/api/upload', {method:'POST',
      headers:{'X-Token':TOKEN,'X-File-Name':encodeURIComponent(file.name)}, body:file});
    if(!r.ok){ let m=T('识别失败', 'Scan failed'); try{const j=await r.json(); m=j.error||m;}catch(e){} throw new Error(m); }
    applyDoc(await r.json());
  }catch(e){ toast(e.message, true); }
  finally{ overlay(false); }
}
async function openPath(path){
  overlay(true, T('正在识别敏感信息…', 'Scanning for sensitive data…'));
  try{
    const d = await api('/api/open', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:path})});
    applyDoc(d);
  }catch(e){ toast(e.message, true); }
  finally{ overlay(false); }
}

function applyDoc(d){
  S.docId = d.docId; S.name = d.name; S.pages = d.pages; S.findings = d.findings;
  S.scanned = d.scanned || []; S.outDir = d.outDir || '';
  S.stats = d.stats || {}; S.size = d.size || 0;
  S.sel = new Set(d.findings.filter(f=>!f.suspect).map(f=>f.id)); S.page = 0; S.hi = null;
  $('dropView').hidden = true; $('workView').hidden = false; $('actionBar').hidden = false;
  $('fName').textContent = d.name;
  renderMeta();
  renderStats(S.stats);
  renderList(); refreshPreview(); syncBar();
}

/* 文件摘要 + 扫描件提醒：切换语言时要重算，所以单独抽出来 */
function renderMeta(){
  if(!S.docId) return;
  const kb = (S.size||0)/1024;
  const sz = kb > 1024 ? (kb/1024).toFixed(1)+' MB' : Math.max(1, Math.round(kb))+' KB';
  const hitPages = new Set(S.findings.filter(f=>!f.suspect).map(f=>f.page)).size;
  const nHit = S.findings.filter(f=>!f.suspect).length;
  const nSus = S.findings.filter(f=>f.suspect).length;
  let sub;
  if(LANG === 'en'){
    sub = S.pages.length + ' pages · ' + sz + ' · ' + nHit + ' items (' +
      hitPages + '/' + S.pages.length + ' pages with hits)';
    if(nSus) sub += ', plus ' + nSus + ' possible names to confirm';
  } else {
    sub = S.pages.length + ' 页 · ' + sz + ' · 识别到 ' + nHit + ' 处（' +
      hitPages + '/' + S.pages.length + ' 页有内容）';
    if(nSus) sub += '，另有 ' + nSus + ' 处疑似人名待确认';
  }
  $('fSub').textContent = sub;
  if(S.scanned && S.scanned.length){
    const pages = S.scanned.map(i=>i+1).join(T('、', ', '));
    $('scanWarn').hidden = false;
    $('scanWarn').textContent = T(
      '第 ' + pages + ' 页没有文字层（可能是扫描件），这几页无法自动识别，请用「框选手动打码」补齐。',
      'Page ' + pages + ' has no text layer (probably a scan). Those pages cannot be detected — use the manual box tool.'
    );
  } else {
    $('scanWarn').hidden = true;
  }
}

function renderStats(stats){
  const box = $('stats'); box.innerHTML = '';
  stats = stats || S.stats || {};
  const order = ['身份证号','银行卡号','手机号','座机号','邮箱','姓名','地址','出生日期','性别','年龄','手动框选'];
  let n = 0;
  order.forEach(k=>{
    if(!stats[k]) return;
    n += stats[k];
    const c = TYPE_COLOR[Object.keys(TYPE_COLOR).find(t=>(
      {'身份证号':'idcard','银行卡号':'bankcard','手机号':'phone','座机号':'tel','邮箱':'email',
       '姓名':'name','地址':'address','出生日期':'birth','性别':'gender','年龄':'age',
       '手动框选':'manual'}[k]))] || '#888';
    const el = document.createElement('span');
    el.className = 'chip';
    el.innerHTML = '<i style="background:'+c+'"></i>'+esc(T(k, STAT_EN[k] || k))+' <b>'+stats[k]+'</b>';
    box.appendChild(el);
  });
  if(!n) box.innerHTML = '<span class="chip">' + T('未识别到敏感信息', 'Nothing detected') + '</span>';
  $('totalCnt').textContent = n;
}

function renderList(){
  const list = $('list'); list.innerHTML = '';
  if(!S.findings.length){
    list.innerHTML = '<div class="empty">' + T(
      '没有自动识别到敏感信息。<br>可以点上方「框选手动打码」在页面上手动画框。',
      'Nothing detected automatically.<br>Use “Draw a box” above to mark areas by hand.') + '</div>';
    return;
  }
  const groups = {};
  S.findings.forEach(f=>{ (groups[f.page] = groups[f.page]||[]).push(f); });
  Object.keys(groups).sort((a,b)=>a-b).forEach(pg=>{
    const g = document.createElement('div');
    g.className = 'grp'; g.textContent = T('第 ' + (+pg+1) + ' 页', 'Page ' + (+pg+1));
    list.appendChild(g);
    groups[pg].forEach(f=>{
      const row = document.createElement('div');
      row.className = 'row' + (S.sel.has(f.id)?' on':'');
      row.dataset.id = f.id;
      row.innerHTML = '<input type="checkbox" '+(S.sel.has(f.id)?'checked':'')+'>'
        + '<span class="badge" style="color:'+(TYPE_COLOR[f.type]||'#555')+';background='+
          (TYPE_COLOR[f.type]||'#555')+'1a">'+esc(labelOf(f))+'</span>'
        + '<span class="mono">'+esc(f.mask)+'</span>'
        + (f.suspect ? '<span class="sus">' + T('疑似', 'maybe') + '</span>' : '');
      row.querySelector('input').addEventListener('click', ev=>{
        ev.stopPropagation(); toggle(f.id, ev.target.checked);
      });
      row.addEventListener('click', ()=>{ focusFinding(f); });
      list.appendChild(row);
    });
  });
}

function focusFinding(f){
  S.page = f.page; S.hi = f.id;
  if(!S.sel.has(f.id)){ S.sel.add(f.id); renderList(); syncBar(); }
  refreshPreview();
}
function toggle(id, on){
  if(on) S.sel.add(id); else S.sel.delete(id);
  const row = document.querySelector('.row[data-id="'+id+'"]');
  if(row) row.classList.toggle('on', on);
  syncBar(); refreshPreview();
}
function syncBar(){
  $('selCount').textContent = S.sel.size;
  $('goBtn').disabled = S.sel.size === 0;
  const cnt = {};
  S.findings.forEach(f=>{ cnt[f.page] = (cnt[f.page]||0) + 1; });
  let info = (S.page+1) + ' / ' + S.pages.length;
  if (S.scanned.indexOf(S.page) >= 0) info += T(' · 无文字层', ' · no text layer');
  else info += T(' · 本页 ' + (cnt[S.page]||0) + ' 处', ' · ' + (cnt[S.page]||0) + ' here');
  $('pgNum').textContent = info;
  $('prevPage').disabled = S.page <= 0;
  $('nextPage').disabled = S.page >= S.pages.length-1;
  $('zoomTxt').textContent = Math.round(S.zoom*100) + '%';
}

function refreshPreview(){
  const img = $('pageImg');
  const q = new URLSearchParams({doc:S.docId, page:S.page, zoom:S.zoom,
    sel:[...S.sel].join(','), mask:S.mask?'1':'0', hi:S.hi||'', t:Date.now()});
  img.src = '/api/preview?' + q.toString();
  syncBar();
}

/* ---------- 事件 ---------- */
$('pickBtn').addEventListener('click', ()=>$('fileInput').click());
$('dropCard').addEventListener('click', e=>{ if(e.target.id!=='pickBtn') $('fileInput').click(); });
$('fileInput').addEventListener('change', e=>{ uploadFile(e.target.files[0]); e.target.value=''; });
['dragenter','dragover'].forEach(ev=>document.addEventListener(ev, e=>{
  e.preventDefault(); $('dropCard').classList.add('over');
}));
['dragleave','drop'].forEach(ev=>document.addEventListener(ev, e=>{
  e.preventDefault();
  if(ev==='dragleave' && e.relatedTarget) return;
  $('dropCard').classList.remove('over');
}));
document.addEventListener('drop', e=>{
  e.preventDefault();
  const f = e.dataTransfer.files && e.dataTransfer.files[0];
  if(f) uploadFile(f);
});
$('reupload').addEventListener('click', ()=>{ resetToDrop(); });
$('backBtn').addEventListener('click', ()=>{ resetToDrop(); });
function resetToDrop(){
  $('workView').hidden = true; $('actionBar').hidden = true; $('dropView').hidden = false;
  $('pageImg').src = ''; $('fileInput').click();
}
$('selAll').addEventListener('click', ()=>{
  S.findings.forEach(f=>S.sel.add(f.id)); renderList(); syncBar(); refreshPreview();
});
$('selNone').addEventListener('click', ()=>{
  S.sel.clear(); renderList(); syncBar(); refreshPreview();
});
$('prevPage').addEventListener('click', ()=>{ if(S.page>0){S.page--; S.hi=null; refreshPreview();} });
$('nextPage').addEventListener('click', ()=>{
  if(S.page < S.pages.length-1){ S.page++; S.hi=null; refreshPreview(); }
});
$('zoomIn').addEventListener('click', ()=>{ S.zoom = Math.min(3, +(S.zoom+0.2).toFixed(2)); refreshPreview(); });
$('zoomOut').addEventListener('click', ()=>{ S.zoom = Math.max(0.6, +(S.zoom-0.2).toFixed(2)); refreshPreview(); });
$('maskPreview').addEventListener('change', e=>{ S.mask = e.target.checked; refreshPreview(); });
$('drawBtn').addEventListener('click', ()=>{
  S.drawing = !S.drawing;
  $('drawBtn').classList.toggle('active', S.drawing);
  $('canvasWrap').classList.toggle('draw', S.drawing);
  if(S.drawing) toast(T('在页面上按住鼠标拖动，框出要打码的区域', 'Hold and drag on the page to draw a box'));
});

/* 双击方框：取消 / 恢复这一处打码（自动识别的框和手动框都支持） */
$('canvasWrap').addEventListener('dblclick', e=>{
  const img = $('pageImg');
  if(!img || !img.src || !S.findings.length) return;
  const r = img.getBoundingClientRect();
  if(e.clientX<r.left || e.clientX>r.right || e.clientY<r.top || e.clientY>r.bottom) return;
  const x = (e.clientX - r.left) / S.zoom;
  const y = (e.clientY - r.top) / S.zoom;
  const pad = 6 / S.zoom;               // 小框也点得中
  let hit = null;
  for(let i = S.findings.length - 1; i >= 0; i--){   // 从上往下找，后画的优先
    const f = S.findings[i];
    if(f.page !== S.page) continue;
    const b = f.rect;
    if(x >= b[0]-pad && x <= b[2]+pad && y >= b[1]-pad && y <= b[3]+pad){ hit = f; break; }
  }
  if(!hit) return;
  e.preventDefault();
  const wasOn = S.sel.has(hit.id);
  if(wasOn) S.sel.delete(hit.id); else S.sel.add(hit.id);
  S.hi = wasOn ? null : hit.id;
  renderList(); syncBar(); refreshPreview();
  toast((wasOn ? T('已取消这处打码：', 'Mask removed: ') : T('已恢复这处打码：', 'Mask restored: ')) + labelOf(hit));
});

/* 手动框选 */
let band=null, startPt=null;
$('canvasWrap').addEventListener('mousedown', e=>{
  if(!S.drawing || e.button!==0) return;
  const img = $('pageImg'); if(!img.src) return;
  const r = img.getBoundingClientRect();
  if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom) return;
  e.preventDefault();
  startPt = {x:e.clientX, y:e.clientY};
  band = document.createElement('div'); band.className='band'; document.body.appendChild(band);
  drawBand(startPt, startPt);
});
$('canvasWrap').addEventListener('mousemove', e=>{
  if(band && startPt) drawBand(startPt, {x:e.clientX, y:e.clientY});
});
window.addEventListener('mouseup', async e=>{
  if(!band || !startPt) return;
  const end = {x:e.clientX, y:e.clientY};
  band.remove(); band=null;
  const p0 = startPt; startPt=null;
  const img = $('pageImg'); const r = img.getBoundingClientRect();
  const x0 = Math.min(p0.x,end.x), y0 = Math.min(p0.y,end.y);
  const x1 = Math.max(p0.x,end.x), y1 = Math.max(p0.y,end.y);
  if(x1-x0 < 5 || y1-y0 < 5) return;
  const rect = [ (x0-r.left)/S.zoom, (y0-r.top)/S.zoom, (x1-r.left)/S.zoom, (y1-r.top)/S.zoom ];
  try{
    const res = await api('/api/manual', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({doc:S.docId, page:S.page, rect:rect})});
    S.findings.push({id:res.id, type:'manual', label:T('手动框选', 'Manual box'),
      mask:T('手动框选区域', 'Manual area'), page:S.page, rect:rect, note:'manual'});
    S.sel.add(res.id); S.hi = res.id;
    const sub = $('fSub');
    renderList(); syncBar(); refreshPreview(); toast(T('已添加手动打码区域', 'Manual mask added'));
  }catch(err){ toast(err.message, true); }
});
function drawBand(a,b){
  const x=Math.min(a.x,b.x), y=Math.min(a.y,b.y), w=Math.abs(a.x-b.x), h=Math.abs(a.y-b.y);
  band.style.left=x+'px'; band.style.top=y+'px'; band.style.width=w+'px'; band.style.height=h+'px';
}

/* ---------- 设置 / 保存位置 ---------- */
let CFG = {saveDir:'', rememberDir:true, noAsk:false, defaultDir:'', effectiveDir:''};

async function loadCfg(){
  try{
    const q = S.docId ? ('?doc=' + encodeURIComponent(S.docId)) : '';
    CFG = await api('/api/settings' + q);
  }catch(e){}
  return CFG;
}

async function pickDir(inputId){
  const cur = ($(inputId).value || '').trim();
  try{
    const r = await api('/api/pickdir', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({initial:cur})});
    if(r.path){ $(inputId).value = r.path; }
    else if(r.status === 'error'){
      toast(T('打不开系统的选择框，可以直接把文件夹路径粘贴到输入框里', 'Could not open the folder picker — paste the path into the box instead'), true);
    }
  }catch(e){ toast(e.message, true); }
}

async function saveCopyAs(token, initial){
  try{
    const r = await api('/api/pickdir', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({initial:initial || ''})});
    if(r.status === 'cancel') return;
    if(!r.path) return toast(T('打不开系统的选择框', 'Could not open the folder picker'), true);
    const res = await api('/api/copyout', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:token, dir:r.path})});
    toast(T('已另存到 ', 'Saved a copy to ') + res.path);
  }catch(e){ toast(e.message, true); }
}

async function doRender(opt){
  if(!S.sel.size) return;
  overlay(true, T('正在生成打码 PDF…', 'Generating masked PDF…'));
  try{
    const body = {doc:S.docId, ids:[...S.sel]};
    if(opt){ body.dir = opt.dir || ''; body.remember = !!opt.remember; body.noAsk = !!opt.noAsk; }
    const d = await api('/api/render', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    overlay(false);
    if(opt) await loadCfg();
    showResult(d);
  }catch(e){ overlay(false); toast(e.message, true); }
}

/* 生成：先决定要不要问保存位置 */
$('goBtn').addEventListener('click', async ()=>{
  if(!S.sel.size) return;
  await loadCfg();
  if(CFG.noAsk && CFG.effectiveDir){
    doRender({dir:CFG.effectiveDir, remember:true, noAsk:true});
    return;
  }
  const def = CFG.saveDir || S.outDir || CFG.defaultDir || '';
  $('savePath').value = def;
  $('optRemember').checked = CFG.rememberDir !== false;
  $('optNoAsk').checked = !!CFG.noAsk;
  $('saveMask').hidden = false;
  $('savePath').focus();
});

$('saveBrowse').addEventListener('click', ()=>pickDir('savePath'));
$('saveCancel').addEventListener('click', ()=>{ $('saveMask').hidden = true; });
$('saveMask').addEventListener('click', e=>{ if(e.target === $('saveMask')) $('saveMask').hidden = true; });
$('saveOk').addEventListener('click', async ()=>{
  const dir = ($('savePath').value || '').trim();
  if(!dir) return toast(T('请先选一个保存文件夹', 'Pick a folder first'), true);
  const remember = $('optRemember').checked, noAsk = $('optNoAsk').checked;
  $('saveMask').hidden = true;
  doRender({dir:dir, remember:remember, noAsk:noAsk});
});

/* 设置面板 */
$('setBtn').addEventListener('click', async ()=>{
  await loadCfg();
  $('setPath').value = CFG.saveDir || '';
  $('setAsk').checked = !CFG.noAsk;
  $('setMask').hidden = false;
  applyLang();                 // 顺带把语言按钮的选中态同步一下
  if (UPD) renderUpdate();
});
$('setBrowse').addEventListener('click', ()=>pickDir('setPath'));
$('setMask').addEventListener('click', e=>{ if(e.target === $('setMask')) $('setMask').hidden = true; });
$('setOk').addEventListener('click', async ()=>{
  const v = ($('setPath').value || '').trim();
  const ask = $('setAsk').checked;
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({saveDir:v, noAsk:!ask})});
    await loadCfg();
    $('setMask').hidden = true;
    toast(T('设置已保存', 'Settings saved'));
  }catch(e){ toast(e.message, true); }
});
$('setReset').addEventListener('click', async ()=>{
  $('setPath').value = ''; $('setAsk').checked = true;
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({saveDir:'', noAsk:false})});
    await loadCfg(); toast(T('已恢复默认设置', 'Defaults restored'));
  }catch(e){ toast(e.message, true); }
});

/* ---------- 界面语言 / 检查更新 ---------- */
$('langSeg').addEventListener('click', async e=>{
  const b = e.target.closest('.seg-btn');
  if(!b) return;
  LANG = b.dataset.lang === 'en' ? 'en' : 'zh';
  applyLang();
  try{
    await api('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({lang:LANG})});
  }catch(err){}
});

let UPD = null;      // {r: 后端返回, opened: 浏览器是否被成功唤起}

function setHelp(){
  $('updHelp').innerHTML = T(
    '还是打不开？按顺序试：<ol>' +
    '<li><b>查权限</b>：安全软件 / 家长控制有没有拦浏览器；系统「设置 → 网络和 Internet → 代理」是不是还开着；防火墙有没有拦本程序联网。</li>' +
    '<li><b>复制链接</b>，自己粘到浏览器地址栏里打开。</li>' +
    '<li>都不行就<b>截屏这一屏</b>，用微信「提取文字」或相册的文字识别把链接抠出来，手动输入。</li></ol>',
    'Still blocked? Try in order:<ol>' +
    '<li><b>Check permissions</b>: is a security suite or parental control blocking your browser? Is a proxy still on under Settings → Network & Internet → Proxy? Is the firewall blocking this app?</li>' +
    '<li><b>Copy the link</b> and paste it into your browser yourself.</li>' +
    '<li>If that fails, <b>screenshot this window</b> and use text recognition (WeChat “Extract text”, or your photo app) to pull the link out by hand.</li></ol>'
  );
}

function renderUpdate(){
  if(!UPD) return;
  const r = UPD.r;
  const box = $('updBox'), txt = $('updText');
  const urlBox = $('updUrl'), acts = $('updActions'), help = $('updHelp');
  box.hidden = false;
  urlBox.hidden = true; acts.hidden = true; help.hidden = true;
  const detail = $('updDetail');
  detail.hidden = true; detail.textContent = '';
  if(!r || !r.ok){
    box.className = 'upd-box fail';
    txt.textContent = T('检查失败：', 'Check failed: ') +
      ((r && r.error) || T('网络不通。', 'network error.')) +
      T(' 可以直接去发布页手动看看，也可以按下面的步骤排查。',
        ' You can also open the releases page yourself, or work through the steps below.');
    if(r && r.detail){ detail.hidden = false; detail.textContent = r.detail; }
    urlBox.textContent = (r && (r.url || r.releasesUrl)) || '';
    urlBox.hidden = !urlBox.textContent;
    acts.hidden = false; help.hidden = false;
    setHelp();
    return;
  }
  $('latestVer').textContent = 'v' + r.latest;
  if(!r.hasUpdate){
    box.className = 'upd-box ok';
    txt.textContent = T('已是最新版本（v' + r.current + '）。',
                        'You are on the latest version (v' + r.current + ').');
    return;
  }
  box.className = 'upd-box new';
  txt.textContent = UPD.opened
    ? T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），已经让浏览器去下载了。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '). Your browser is downloading it now.')
    : T('发现新版本 v' + r.latest + '（当前 v' + r.current + '），但没能自动打开浏览器，点下面的按钮再试一次。',
        'New version v' + r.latest + ' is out (you have v' + r.current + '), but the browser did not open — try the button below.');
  urlBox.textContent = r.url || '';
  urlBox.hidden = !urlBox.textContent;
  acts.hidden = false; help.hidden = false;
  setHelp();
}

async function openUpdateUrl(url){
  if(!url) return false;
  try{
    await api('/api/openurl', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:url})});
    return true;
  }catch(err){
    toast(T('打不开默认浏览器：', 'Could not launch a browser: ') + err.message, true);
    return false;
  }
}

$('checkBtn').addEventListener('click', async ()=>{
  const btn = $('checkBtn');
  btn.disabled = true;
  btn.textContent = T('检查中…', 'Checking…');
  $('updBox').hidden = false;
  $('updBox').className = 'upd-box';
  $('updText').textContent = T('正在连接 GitHub 查询最新版本…', 'Contacting GitHub for the latest release…');
  $('updUrl').hidden = true; $('updActions').hidden = true; $('updHelp').hidden = true;

  let r;
  try{ r = await api('/api/check_update'); }
  catch(e){ r = {ok:false, error:e.message}; }
  let opened = false;
  if(r && r.ok && r.hasUpdate){
    // 有新版本才跳浏览器，直接指向安装包
    opened = await openUpdateUrl(r.url);
  }
  UPD = {r:r, opened:opened};
  btn.disabled = false;
  btn.textContent = T('检查更新', 'Check for updates');
  renderUpdate();
});

$('updOpen').addEventListener('click', async ()=>{
  const url = (UPD && UPD.r && (UPD.r.url || UPD.r.releasesUrl)) || '';
  const ok = await openUpdateUrl(url);
  if(ok && UPD){ UPD.opened = true; renderUpdate(); }
});
$('updCopy').addEventListener('click', ()=>{
  const url = (UPD && UPD.r && (UPD.r.url || UPD.r.releasesUrl)) || '';
  if(!url) return;
  copyText(url, T('已复制下载链接：', 'Download link copied: '));
});

function showResult(d){
  const stats = Object.keys(d.stats).map(k=>T(k, STAT_EN[k]||k)+' '+d.stats[k]).join(' · ');
  const wrap = document.createElement('div');
  wrap.className = 'result';
  wrap.innerHTML = '<div class="card">'
    + '<div class="ok-ico"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    + 'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12.5l5 5L20 6.5"/></svg></div>'
    + '<h3>' + T('打码完成', 'Masking done') + '</h3>'
    + '<div style="color:var(--ink2);font-size:13px">' +
      T('共处理 ' + d.count + ' 处：', 'Masked ' + d.count + ' items: ') + esc(stats) + '</div>'
    + '<div style="color:var(--ink3);font-size:12px;margin-top:2px">' + T(
      '全文 ' + (d.pages||'-') + ' 页，其中 ' + (d.hitPages||'-') + ' 页有打码，其余页面原样保留',
      (d.pages||'-') + ' pages in total, ' + (d.hitPages||'-') + ' of them masked, the rest untouched') + '</div>'
    + '<div class="path">' + esc(d.path) + '</div>'
    + '<div class="res-actions">'
    + '<button class="btn primary" id="rOpen">' + T('打开 PDF', 'Open PDF') + '</button>'
    + '<button class="btn" id="rFolder">' + T('打开所在文件夹', 'Open containing folder') + '</button>'
    + '<button class="btn" id="rDl">' + T('另存到别处…', 'Save a copy…') + '</button>'
    + '<button class="btn ghost" id="rClose">' + T('关闭', 'Close') + '</button>'
    + '</div></div>';
  document.body.appendChild(wrap);
  wrap.querySelector('#rClose').onclick = ()=>wrap.remove();
  wrap.querySelector('#rOpen').onclick = ()=>post('/api/openfile', {token:d.token});
  wrap.querySelector('#rFolder').onclick = ()=>post('/api/showfolder', {token:d.token});
  wrap.querySelector('#rDl').onclick = ()=>saveCopyAs(d.token, d.dir);
  async function post(p, body){
    try{ await api(p, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); }
    catch(e){ toast(e.message, true); }
  }
}

/* 启动：先按上次保存的语言刷新整页文案，再决定要不要打开命令行带来的文件 */
(async ()=>{
  try{
    await loadCfg();
    if(CFG && CFG.lang === 'en') LANG = 'en';
  }catch(e){}
  applyLang();
  if (BOOT) openPath(BOOT);
})();

setInterval(()=>{ fetch('/api/ping').catch(()=>{}); }, 60000);

const aboutMask = $('aboutMask');
if (aboutMask) {
  $('aboutBtn').onclick = ()=> aboutMask.hidden = false;
  $('aboutOk').onclick = ()=> aboutMask.hidden = true;
  // 保存赞赏码：浏览器里直接用 a[download] 落盘，不需要后端
  const thanksSave = $('thanksSave');
  if (thanksSave) thanksSave.onclick = ()=>{
    const qr = $('thanksQr');
    if (!qr) return;
    const a = document.createElement('a');
    a.href = qr.src;
    a.download = 'PDFPrivacyMasker-' + (CFG.lang === 'en' ? 'thanks-qr' : '赞赏码') + '.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  aboutMask.addEventListener('click', e=>{ if (e.target === aboutMask) aboutMask.hidden = true; });
}
/* 项目地址：点一下就复制，方便二次开发者把来源留在自己版本里 */
['aboutUrl', 'footUrl'].forEach(id=>{
  const el = $(id);
  if (el) el.addEventListener('click', ()=>{ copyProjectUrl(el); });
});

$('quitBtn').addEventListener('click', async ()=>{
  try{ await api('/api/quit', {method:'POST'}); }catch(e){}
  document.body.innerHTML = '<div style="height:100vh;display:grid;place-items:center;'
    + 'font:14px system-ui;color:#5b6472">' +
    T('已退出，可直接关闭此页面。', 'Closed. You can shut this tab now.') + '</div>';
});
</script>
</body>
</html>
"""


def _fatal(msg):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(msg), APP_NAME, 0x10)
    except Exception:
        pass


def main():
    global BOOT_PATH
    with SETTINGS_LOCK:
        SETTINGS.update(_load_settings())
    _cleanup_stale()
    for a in sys.argv[1:]:
        if a.lower().endswith(".pdf") and os.path.exists(a):
            BOOT_PATH = a
            break
    try:
        srv = QuietServer(("127.0.0.1", 0), Handler)
    except Exception as e:
        _fatal("启动本地服务失败：%s" % e)
        return
    port = srv.server_address[1]
    url = "http://127.0.0.1:%d/?t=%s" % (port, SERVE_TOKEN[:8])

    def _watchdog():
        # 页面关闭后 30 分钟无请求则自动退出，避免后台常驻
        while True:
            time.sleep(60)
            if time.time() - srv.last_seen > 1800:
                _hard_exit(0)

    threading.Thread(target=_watchdog, daemon=True).start()
    if os.environ.get("PDFMASK_NO_OPEN") != "1":
        threading.Timer(0.5, lambda: _open_browser(url)).start()
    print("%s v%s 运行于 %s" % (APP_NAME, VERSION, url))
    print("  " + CREDIT_LINE + " · " + PROJECT_URL)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        _fatal("程序异常：%s" % e)


def _open_browser(url):
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        try:
            os.startfile(url)
        except Exception:
            _fatal("请手动用浏览器打开：%s" % url)


def _browser_open(url):
    """打开默认浏览器。失败时抛异常，让界面展示「复制链接」这类兜底方案。"""
    try:
        import webbrowser
        if webbrowser.open(url):
            return True
    except Exception:
        pass
    try:
        os.startfile(url)  # noqa: S606  (Windows 本地打开链接)
        return True
    except Exception as e:
        raise RuntimeError(_L("打不开默认浏览器：%s", "Could not launch a browser: %s") % e)



def about_text():
    """命令行里的署名与来源信息（附加条款要求「关于」信息可被看到）"""
    return "\n".join([
        "%s v%s" % (APP_NAME, VERSION),
        "",
        CREDIT_LINE,
        "原项目地址：%s" % PROJECT_URL,
        "开源协议：%s（附 AGPL-3.0 第 7 条(b) 附加条款）" % LICENSE_NAME,
        "",
        "二次开发或商用必须保留作者署名，并在程序中标注上述原项目地址；",
        "改动过的版本须注明「本程序基于该地址修改，非原作者发布」。",
        "详见 ADDITIONAL-TERMS.md。",
    ])


def show_about():
    """打印署名；打包成窗口程序后没有控制台，改用系统弹窗显示"""
    txt = about_text()
    if getattr(sys, "frozen", False):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None, txt, "%s v%s" % (APP_NAME, VERSION), 0x40)
            return
        except Exception:
            pass
    print(txt)


if __name__ == "__main__":
    if sys.argv[1:2] in (["--about"], ["-about"], ["--version"], ["-v"]):
        show_about()
    elif len(sys.argv) >= 4 and sys.argv[1] == "--cli":
        cli(sys.argv[2], sys.argv[3])
    else:
        main()
