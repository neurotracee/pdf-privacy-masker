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
# details. You should have received a copy of the license along with this
# program.  If not, see <https://www.gnu.org/licenses/>.

"""
本地离线 OCR —— 给「没有文字层」的 PDF（扫描件、拍照件、纯图片页）提供文字与坐标。

设计要点
--------
1. **只补坐标，不改规则。** 对外只暴露 `page_lines(page)`，返回结构与
   `pdfmask._visual_lines()` 完全一致：[(行文本, [(字, Rect) 或 (" ", None)])]。
   上层的名字/号码识别规则一行都不用动，因为打码本身只吃矩形。

2. **每字矩形来自识别模型的时间步。** 通用 OCR 只给「整行」一个框，拿不到
   「这行里的手机号是第几个字到第几个字」，规则引擎就无法定位。
   PP-OCR 的识别网络是 CTC 结构，输出 T 个时间步 × 6625 类；把相邻且同类的
   时间步合并，就能反推每个字在行内的横向区间（纵向统一取行框）。
   这样「一行里只有号码要打码」也能精确到字。

3. **零网络、零外部服务。** 模型文件随程序分发（assets/ocr/），只在本机 CPU
   上推理，不联网、不上传。

4. **不依赖 OpenCV。** 只用到 numpy + Pillow + onnxruntime：连通域用 numpy 的
   行游程 + 并查集自己算，发布包能少 40 MB，也不容易被 PyInstaller 卡住。

依赖说明
--------
onnxruntime 与 numpy 是**软依赖**：装不上或模型缺失时 `available()` 返回 False，
调用方应退回「仅手动框选」模式，程序其余功能不受影响。
"""

from __future__ import annotations

import os
import sys
import threading
import numpy as np

# ---------------------------------------------------------------------------
# 参数：都是「准确率 / 速度」的权衡点，集中放在这里便于调
# ---------------------------------------------------------------------------

DET_MODEL = "ch_PP-OCRv4_det_infer.onnx"
REC_MODEL = "ch_PP-OCRv4_rec_infer.onnx"
REC_DICT = "ppocr_keys_v1.txt"

RENDER_ZOOM = 2.5        # 页面渲染倍率下限（2.5 ≈ 180 dpi）；扫描件会按原图分辨率自动提高
RENDER_ZOOM_MAX = 4.2    # 上限（4.2 ≈ 300 dpi）：再高只是把已经模糊的像素放大，白花时间
DET_LIMIT = 1280         # 检测输入的长边上限，越大越准也越慢
DET_THRESH = 0.30        # 概率图二值化阈值
BOX_THRESH = 0.50        # 连通域平均分低于此值丢弃（滤掉噪点）
UNCLIP_RATIO = 1.6       # 外扩比例，把文字笔画框撑到「整行高度」
UNCLIP_MAX_RATIO_Y = 0.12   # 纵向外扩上限（按行高算）：大了会吞邻行
MIN_BOX_SIDE = 3         # 最小边长（检测图坐标系），小于此值当噪点

REC_HEIGHT = 48          # 识别输入高（PP-OCR 固定 48）
REC_MAX_W = 2560         # 单行裁剪的最大宽度；超过才压缩，别把正常行长压变形
REC_BATCH = 8            # 每批送进识别模型的行数
PAD_RATIO = 0.85         # 检测框外扩比例（按行高算）：0.45 时细笔画末位数字会被切掉
SKEW_MAX = 3.0           # 倾斜校正的搜索范围（度）
SKEW_MIN = 0.20          # 小于这个角度不动，免得白转一次、掉精度
# 检测框是整行外接框（含行距 / padding / 倾斜余量），实测约为真实字高的 2 倍。
# 单个字的打码矩形按这个比例从行框中心收窄，避免打码块侵入上下行。

# 低对比度页面的对比度归一化（见 normalize_contrast）
CONTRAST_MIN_RANGE = 120  # 灰度 p99-p1 低于此值才动手；正常扫描件远大于它
CONTRAST_LO_P = 5         # 黑场分位
CONTRAST_HI_P = 90        # 白场分位
CONTRAST_PAPER_MIN = 150  # 中位灰度低于此值当「照片」处理，不动它

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def normalize_contrast(rgb):
    """低对比度纸面页的对比度归一化。

    现实里被「故意刁难」的扫描件常常长这样：泛黄的纸底本身就是浅灰
    （中位灰度 225 左右），字又不是纯黑，最暗只到 154，整页灰度动态范围
    只有 60~80。PP-OCR 的检测头输出的是概率图，再过 DET_THRESH 二值化——
    对比度不足时整行根本激活不起来，于是出现「一页 15 行只认出 8 行」
    「整页 0 检出」这种断崖式漏检，而规则层再准也救不回来。

    做法是按页自适应做一次线性拉伸：取灰度 5% / 90% 分位当黑白端点，
    把 [lo, hi] 铺满 [0, 255]。三个保护条件：
      · 动态范围本来就够（>= CONTRAST_MIN_RANGE）→ 原样返回，正常文档一个
        像素都不动，不给现有样本引入副作用；
      · 中位灰度偏暗 → 当照片处理，原样返回，避免把暗背景拉爆；
      · hi-lo 几乎为 0（空白页）→ 原样返回。

    只影响检测与识别的输入，打码坐标仍然按原图算，所以不会错位。
    """
    g = rgb.astype(np.float32).mean(axis=2)
    sub = g[::4, ::4]
    lo, hi = np.percentile(sub, [CONTRAST_LO_P, CONTRAST_HI_P])
    med = float(np.percentile(sub, 50))
    if med < CONTRAST_PAPER_MIN or (hi - lo) >= CONTRAST_MIN_RANGE or (hi - lo) < 2:
        return rgb
    out = np.clip((g - lo) * (255.0 / float(hi - lo)), 0, 255).astype(np.uint8)
    return np.repeat(out[:, :, None], 3, axis=2)


_GRAD_CELL = 64           # 光照估计的网格边长（像素）
_GRAD_TRIGGER = 14.0      # 网格间纸底亮度差超过这个值，就当「有明显光照渐变」


def _paper_field(gray, cell=_GRAD_CELL):
    """按网格取 90% 分位，估计这一页的「纸底亮度分布」。

    用分位数而不是均值/高斯模糊：一格 64×64 里文字占比通常不到 10%，
    90% 分位基本落在纸底上，不会被笔画拉低；而均值会被文字污染，除完
    把笔画漂白、笔画断裂（试过，反而更差）。
    """
    h, w = gray.shape
    ny = max(1, h // cell)
    nx = max(1, w // cell)
    gh, gw = h // ny, w // nx
    blk = gray[:ny * gh, :nx * gw].reshape(ny, gh, nx, gw).transpose(0, 2, 1, 3)
    field = np.percentile(blk.reshape(ny, nx, gh * gw), 90, axis=2)
    from PIL import Image
    small = Image.fromarray(np.clip(field, 0, 255).astype(np.uint8))
    return np.asarray(small.resize((w, h), Image.BILINEAR), dtype=np.float32)


def has_gradient(rgb):
    """这一页是不是「一边亮一边暗」（拍照 / 扫描时台灯偏一侧）。

    第 8 页这类样本：中心亮、四角暗，全局拉伸会把暗区直接压成黑，
    行与行粘成一片，识别出来就是乱码。这种页面必须先除掉光照再谈对比度。
    """
    g = rgb.astype(np.float32).mean(axis=2)
    field = _paper_field(g)
    tiny = field[::32, ::32]
    return (float(tiny.max()) - float(tiny.min())) >= _GRAD_TRIGGER


def flatten_illumination(rgb):
    """用纸底亮度把页面「压平」：每个像素除以所在位置的纸底亮度。

    纸底变成均匀的 255，字还是相对更暗——渐变消失，后面再统一拉伸黑白场
    就稳定了。返回仍是 HxWx3 uint8，坐标不变。
    """
    g = rgb.astype(np.float32).mean(axis=2)
    field = _paper_field(g)
    out = np.clip(g / np.maximum(field, 1.0) * 255.0, 0, 255).astype(np.uint8)
    return np.repeat(out[:, :, None], 3, axis=2)


def fold_width(c):
    """把一个全角字符折成半角（1 换 1，不改变字数，矩形不会错位）

    中文文档里「１２３」「ｈｔｔｐ」「：」这类全角写法非常常见，
    而识别规则里的正则用的是半角字符类，不折就完全匹配不到。
    与 pdfmask.py 里的同名函数保持一致。
    """
    o = ord(c)
    if 0xFF01 <= o <= 0xFF5E:
        return chr(o - 0xFEE0)
    if o == 0x3000:
        return " "
    return c


# ---------------------------------------------------------------------------
# 模型定位
# ---------------------------------------------------------------------------

def model_dir() -> str:
    """找模型目录：环境变量 > PyInstaller 解包目录 > 源码同级 assets/ocr"""
    env = os.environ.get("PDFMASK_OCR_DIR")
    if env and os.path.isfile(os.path.join(env, DET_MODEL)):
        return env
    cands = []
    base = getattr(sys, "_MEIASS", None) or getattr(sys, "_MEIPASS", None)
    if base:
        cands.append(os.path.join(base, "assets", "ocr"))
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, "assets", "ocr"))
    cands.append(os.path.join(os.getcwd(), "assets", "ocr"))
    for c in cands:
        if os.path.isfile(os.path.join(c, DET_MODEL)):
            return c
    return ""


def available() -> bool:
    """OCR 能不能用：模型在、onnxruntime 与 numpy 都装得上"""
    if not model_dir():
        return False
    try:
        import onnxruntime  # noqa: F401
    except Exception:
        return False
    return True


def why_unavailable() -> str:
    if not model_dir():
        return "缺少 OCR 模型文件（assets/ocr/）"
    try:
        import onnxruntime  # noqa: F401
    except Exception:
        return "未安装 onnxruntime"
    return ""


# ---------------------------------------------------------------------------
# 图像小工具（不依赖 OpenCV）
# ---------------------------------------------------------------------------

def _resize_rgb(arr, w, h):
    """把 HxWx3 uint8 缩放到 (w, h)，用 Pillow（已经是项目依赖）"""
    from PIL import Image
    if arr.shape[1] == w and arr.shape[0] == h:
        return arr
    return np.asarray(Image.fromarray(arr).resize((max(1, w), max(1, h)), Image.BILINEAR))


def _skew_score(gray, angle):
    """把灰度图按 angle 转一下，看「行与行之间」的投影跳变有多锋利

    文字排得越正，水平投影的行间空隙越干净，相邻两行投影差的方差就越大。
    这就是最经典也最省算力的倾斜估计，不需要 OpenCV、不需要霍夫变换。
    """
    from PIL import Image
    b = np.asarray(Image.fromarray(gray).rotate(angle, resample=Image.BILINEAR,
                                               fillcolor=255)) < 165
    prof = b.sum(1).astype(np.float32)
    return float(np.var(np.diff(prof)))


def estimate_skew(gray, limit=SKEW_MAX):
    """估计页面倾斜角（度）。返回值直接拿去 `Image.rotate()` 就能摆正。

    先 0.25 度粗扫，再在最优值附近 0.05 度细扫——实测误差在 0.1 度以内，
    够用且总耗时只有十几毫秒（在缩到 600 px 的灰度图上算）。
    手机拍照、平板扫描仪的页面几乎都带 0.3~2 度的歪，歪着检测会整行整行地丢，
    所以这一步不是可选的优化，是准不准的前提。
    """
    from PIL import Image
    im = Image.fromarray(gray)
    w, h = im.size
    s = 600.0 / max(w, h)
    if s < 1.0:
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR)
        w, h = im.size
    a = np.asarray(im)
    best, best_v = 0.0, _skew_score(a, 0.0)
    t = -limit
    while t <= limit + 1e-9:
        v = _skew_score(a, t)
        if v > best_v:
            best, best_v = float(t), v
        t += 0.25
    t = best - 0.35
    while t <= best + 0.35 + 1e-9:
        v = _skew_score(a, t)
        if v > best_v:
            best, best_v = float(t), v
        t += 0.05
    return best


def _unrotate_box(x0, y0, x1, y1, cx, cy, deg):
    """把「摆正后图像」里的框，换算回「原图」坐标（四角取外接矩形）"""
    if not deg:
        return x0, y0, x1, y1
    import math
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    xs, ys = [], []
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        dx, dy = x - cx, y - cy
        xs.append(ca * dx - sa * dy + cx)
        ys.append(sa * dx + ca * dy + cy)
    return min(xs), min(ys), max(xs), max(ys)



def _pick_zoom(page, base=None):
    """按页面里图片的原始分辨率挑渲染倍率

    300 dpi 扫进来的扫描件，如果还按 180 dpi 渲染，等于先把扫描的分辨率扔掉一半，
    再做识别——首当其冲的就是「一长串相同数字」和号码末尾几位（实测 15900002222
    会被读成 1590002222）。所以这里按原图的实际像素密度往上抬，抬到 300 dpi 为止；
    本来就模糊的 150 dpi 图不会被无意义地放大，速度和以前一样。
    """
    lo = float(base or RENDER_ZOOM)
    dpi = 0.0
    try:
        for info in page.get_image_info():
            bbox = info.get("bbox")
            iw = float(info.get("width") or 0)
            ih = float(info.get("height") or 0)
            if not bbox or iw < 1 or ih < 1:
                continue
            w_pt = max(1e-6, bbox[2] - bbox[0])
            h_pt = max(1e-6, bbox[3] - bbox[1])
            dpi = max(dpi, iw * 72.0 / w_pt, ih * 72.0 / h_pt)
    except Exception:
        dpi = 0.0
    if dpi <= 0:
        return lo
    return max(lo, min(RENDER_ZOOM_MAX, round(dpi / 72.0, 2)))


def _components(mask):
    """二值图的 8 连通域标注，返回 [(x0, y0, x1, y1)]

    用「行游程 + 并查集」实现，避免引入 OpenCV：
    逐行取出连续为 True 的区间，和上一行有重叠（含斜接）的区间合并。
    """
    h, w = mask.shape
    parent = []

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    rows = []
    prev_runs = ()
    for y in range(h):
        row = mask[y]
        if not row.any():
            rows.append(())
            prev_runs = ()
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.flatnonzero(d == 1).tolist()
        ends = np.flatnonzero(d == -1).tolist()
        cur = []
        for s, e in zip(starts, ends):
            rid = len(parent)
            parent.append(rid)
            for ps, pe, pid in prev_runs:
                if ps <= e and s <= pe:
                    union(rid, pid)
            cur.append((s, e, rid))
        rows.append(tuple(cur))
        prev_runs = cur

    agg = {}
    for y, runs in enumerate(rows):
        for s, e, rid in runs:
            r = find(rid)
            box = agg.get(r)
            if box is None:
                agg[r] = [s, y, e, y + 1]
            else:
                if s < box[0]:
                    box[0] = s
                if e > box[2]:
                    box[2] = e
                box[3] = y + 1
    return [(v[0], v[1], v[2], v[3]) for v in agg.values()]


# ---------------------------------------------------------------------------
# 识别标签表
# ---------------------------------------------------------------------------

def _load_chars(path):
    """PP-OCR 的解码表：下标 0 是 blank，1..N 是字典字，最后一个是空格"""
    chars = [""]
    with open(path, encoding="utf-8") as f:
        for line in f:
            chars.append(line.rstrip("\n").rstrip("\r"))
    chars.append(" ")
    return chars


# ---------------------------------------------------------------------------
# 引擎
# ---------------------------------------------------------------------------

class OcrEngine(object):
    """一个进程内共用一个引擎（模型加载约 0.2–0.6 秒，别反复建）"""

    _singleton = None
    _lock = threading.Lock()

    def __init__(self, models: str = "", threads: int = 0):
        import onnxruntime as ort

        d = models or model_dir()
        if not d:
            raise RuntimeError(why_unavailable() or "OCR 模型不存在")

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads > 0:
            so.intra_op_num_threads = threads
        else:
            # 低配机器上别把核占满：留一个给界面线程
            cpu = os.cpu_count() or 2
            so.intra_op_num_threads = max(1, min(4, cpu - 1))
        so.log_severity_level = 3

        self.det = ort.InferenceSession(os.path.join(d, DET_MODEL),
                                        sess_options=so,
                                        providers=["CPUExecutionProvider"])
        self.rec = ort.InferenceSession(os.path.join(d, REC_MODEL),
                                        sess_options=so,
                                        providers=["CPUExecutionProvider"])
        self._det_in = self.det.get_inputs()[0].name
        self._rec_in = self.rec.get_inputs()[0].name
        self.chars = _load_chars(os.path.join(d, REC_DICT))

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._singleton is None:
                cls._singleton = OcrEngine()
            return cls._singleton

    # -- 检测 ---------------------------------------------------------------
    def _detect(self, img):
        """img: HxWx3 uint8（已经缩到 DET_LIMIT 以内，未补齐）

        返回检测图坐标系下的 [(x0, y0, x1, y1, score)]
        """
        h, w = img.shape[:2]
        ph = (32 - h % 32) % 32
        pw = (32 - w % 32) % 32
        if ph or pw:
            img = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="constant", constant_values=255)

        x = img.astype(np.float32) / 255.0
        x = (x - _MEAN) / _STD
        x = np.ascontiguousarray(x.transpose(2, 0, 1)[None], dtype=np.float32)

        prob = self.det.run(None, {self._det_in: x})[0][0, 0]
        # 概率图尺寸 = 补齐后的输入尺寸（PP-OCR det 输出与输入同尺寸）
        sx = w / float(prob.shape[1])
        sy = h / float(prob.shape[0])

        mask = prob > DET_THRESH
        if not mask.any():
            return []

        out = []
        for x0, y0, x1, y1 in _components(mask):
            bw = x1 - x0
            bh = y1 - y0
            if bw < MIN_BOX_SIDE or bh < MIN_BOX_SIDE:
                continue
            # 置信度只统计「框内真正被判为文字的那些像素」。
            # 以前算的是外接矩形内的平均概率，而一整行长句的矩形里大部分是
            # 字间空隙与行间空白，平均值被稀释到 0.25 上下，低于 BOX_THRESH
            # 0.50 就被整条丢掉了——表现就是「短片段能检出、整行长句全漏」。
            # 这也是长文本判决书大量漏检的主因（同一页可以从 8 个框变成 18 个）。
            sub_m = mask[y0:y1, x0:x1]
            if not sub_m.any():
                continue
            score = float(prob[y0:y1, x0:x1][sub_m].mean())
            if score < BOX_THRESH:
                continue
            # unclip：按「面积 / 周长」外扩，把笔画框撑成整行框。
            # 但外扩是各向同性的，而这两个方向的需求正好相反：
            #   · 水平：必须留够余量，否则行首行尾的字会被切掉半个
            #     （实测「出生日期」被读成「出生期」、「1994年3月8日」丢「日」）；
            #   · 垂直：绝不能大，长行按公式会扩到 0.8 倍行高，直接把上下
            #     相邻行吞进裁剪框，识别出来是「楼2单元…楼2执行人…」这种半截串。
            # 所以横向照公式扩，纵向压到 0.12 倍行高。
            d = bw * bh * UNCLIP_RATIO / (2.0 * (bw + bh) + 1e-6)
            dx = d
            # 纵向只对「细长行」收紧；短框（姓名、日期这类）仍然各向同性地扩，
            # 收紧它们会把字的上下沿切掉，OCR 会把「出生日期」读成「出生期」。
            dy = min(d, bh * UNCLIP_MAX_RATIO_Y) if bw >= 6 * bh else d
            # 第 6/7 个值：外扩**之前**的原始上下边。外扩是给识别留余量的，
            # 里面已经含了相邻行；字形高度只能取原始紧框，否则打码块会盖到上下行。
            out.append(((x0 - dx) * sx, (y0 - dy) * sy,
                        (x1 + dx) * sx, (y1 + dy) * sy, score,
                        y0 * sy, (y1 + 1) * sy))
        return out

    # -- 识别 ---------------------------------------------------------------
    def _rec_batch(self, crops):
        """crops: [HxWx3 uint8] → [(text, [(char, x0_frac, x1_frac, conf)])]"""
        if not crops:
            return []
        tensors, meta = [], []
        for crop in crops:
            h, w = crop.shape[:2]
            if h < 2 or w < 2:
                tensors.append(None)
                meta.append((0, 0))
                continue
            nw = max(8, int(round(w * REC_HEIGHT / float(h))))
            nw = min(nw, REC_MAX_W)
            nw += (4 - nw % 4) % 4
            img = _resize_rgb(crop, nw, REC_HEIGHT)
            t = img.astype(np.float32) / 255.0
            t = (t - 0.5) / 0.5
            tensors.append(np.ascontiguousarray(t.transpose(2, 0, 1), dtype=np.float32))
            meta.append((nw, w))

        idxs = [i for i, t in enumerate(tensors) if t is not None]
        if not idxs:
            return [("", [])] * len(crops)
        # 同一批里各行宽度不同，按批内最大宽度在归一化后补 0（与 PaddleOCR 一致）
        wide = max(tensors[i].shape[2] for i in idxs)
        padded = []
        for i in idxs:
            t = tensors[i]
            if t.shape[2] < wide:
                t = np.pad(t, ((0, 0), (0, 0), (0, wide - t.shape[2])), mode="constant")
            padded.append(t)
        batch = np.stack(padded, axis=0)
        preds = self.rec.run(None, {self._rec_in: batch})[0]

        results = [("", [])] * len(crops)
        for k, i in enumerate(idxs):
            pred = preds[k]                       # (T, 6625)
            idx = pred.argmax(1)
            conf = pred.max(1)
            nw, orig_w = meta[i]
            t_count = float(pred.shape[0])
            # 时间步铺满的是「补零后的宽度」，换算回本行实际宽度
            k_w = (wide / float(nw)) if nw else 1.0

            # CTC 去重：相邻同类合并成一个字，同时记下它的时间步区间
            groups = []
            prev = -1
            for t in range(pred.shape[0]):
                c = int(idx[t])
                if c == prev:
                    if groups and c != 0:
                        groups[-1][2] = t + 1
                        groups[-1][3].append(float(conf[t]))
                    continue
                prev = c
                if c != 0:
                    groups.append([c, t, t + 1, [float(conf[t])]])

            txt, chars = [], []
            for c, t0, t1, cs in groups:
                ch = self.chars[c] if c < len(self.chars) else ""
                if not ch:
                    continue
                ch = fold_width(ch)
                # 时间步区间 → 行内横向比例（缩放保持宽高比，可直接换算）
                f0 = min(1.0, (t0 / t_count) * k_w)
                f1 = min(1.0, (t1 / t_count) * k_w)
                if ch.strip() and f1 > f0:
                    chars.append((ch, f0, f1, sum(cs) / len(cs)))
                txt.append(ch)
            results[i] = ("".join(txt), chars)
        return results

    # -- 对外接口 -----------------------------------------------------------
    def page_lines(self, page, zoom: float = None, min_conf: float = 0.0):
        """把一页渲染出来做 OCR，返回 [(text, entries)]

        entries 与 `pdfmask._visual_lines()` 同构：(字, Rect) 或 (" ", None)，
        Rect 用**页面显示坐标**（与 redact 用的坐标系一致）。
        """
        import pymupdf

        z = float(zoom) if zoom else _pick_zoom(page)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False, colorspace=pymupdf.csRGB)
        full = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)

        # 先摆正再检测：扫描件 / 拍照件几乎都带零点几度的歪，
        # 歪着送进检测网络，整行会被漏掉（实测 0.9 度就能让 15 行只剩 5 行）。
        gray_small = full[::4, ::4].mean(axis=2).astype(np.uint8)
        rot = estimate_skew(gray_small)
        if abs(rot) >= SKEW_MIN:
            from PIL import Image
            full = np.ascontiguousarray(np.asarray(Image.fromarray(full).rotate(
                rot, resample=Image.BICUBIC, fillcolor=(255, 255, 255))))
        else:
            rot = 0.0
        rc_x, rc_y = full.shape[1] / 2.0, full.shape[0] / 2.0

        # 极低对比度的纸面页先拉一次黑白场再送进网络（灰字 + 泛黄底是
        # 扫描件漏检的头号原因）；有明显光照渐变的，先把光照除掉再拉伸，
        # 否则暗区会被压死、行与行粘成一片。正常页面这两步都不生效。
        if has_gradient(full):
            work = normalize_contrast(flatten_illumination(full))
        else:
            work = normalize_contrast(full)

        h, w = full.shape[:2]
        scale = min(1.0, DET_LIMIT / float(max(h, w)))
        small = (_resize_rgb(work, int(round(w * scale)), int(round(h * scale)))
                 if scale < 1.0 else work)
        boxes = self._detect(small)
        if not boxes:
            return []

        # 裁到全分辨率图上做识别：检测只要位置，识别要好像素
        inv = 1.0 / scale
        crops, rects = [], []
        for x0, y0, x1, y1, sc, raw_y0, raw_y1 in boxes:
            X0 = max(0, int(x0 * inv))
            Y0 = max(0, int(y0 * inv))
            X1 = min(w, int(x1 * inv) + 1)
            Y1 = min(h, int(y1 * inv) + 1)
            if X1 - X0 < 4 or Y1 - Y0 < 4:
                continue
            # 检测框常常比实际字形窄一点点（笔画细的末位数字尤其容易掉），
            # 按字高比例补边：既让识别看到完整字形，也让打码块盖住边缘不留白
            bh = Y1 - Y0
            pad_x = max(2, int(round(bh * PAD_RATIO)))
            pad_y = max(2, int(round(bh * 0.20)))
            crops.append((max(0, Y0 - pad_y), min(h, Y1 + pad_y),
                          max(0, X0 - pad_x), min(w, X1 + pad_x)))
            # 原始紧框的上下边（页面像素）：识别用外扩后的裁剪，定字高用这个
            ry0 = max(0, int(round(raw_y0 * inv)))
            ry1 = min(h, int(round(raw_y1 * inv)) + 1)
            rects.append((X0, Y0, X1, Y1, ry0, ry1))

        if not crops:
            return []

        patches = [work[a[0]:a[1], a[2]:a[3]] for a in crops]
        recs = []
        for i in range(0, len(patches), REC_BATCH):
            recs.extend(self._rec_batch(patches[i:i + REC_BATCH]))

        items = []
        for (X0, Y0, X1, Y1, ry0, ry1), (text, chars) in zip(rects, recs):
            if not text.strip():
                continue
            if min_conf > 0 and chars and (sum(c[3] for c in chars) / len(chars)) < min_conf:
                continue
            bh = Y1 - Y0
            pad_x = bh * PAD_RATIO
            # 外扩框只用来算「同一行」的聚类容差
            pbx0, pby0, pbx1, pby1 = _unrotate_box(X0 - pad_x, Y0 - bh * 0.20,
                                                   X1 + pad_x, Y1 + bh * 0.20,
                                                   rc_x, rc_y, rot)
            # 字形的上下边 = 检测概率图里**没外扩**的那一段（就是笔画本身）
            cy0, cy1 = ry0, ry1
            bx0, by0, bx1, by1 = _unrotate_box(X0 - pad_x, cy0,
                                               X1 + pad_x, cy1,
                                               rc_x, rc_y, rot)
            items.append({
                "text": text,
                "chars": chars,
                "x0": bx0 / z, "y0": by0 / z,
                "x1": bx1 / z, "y1": by1 / z,
                "tight": True,
                "tol": max(1.0, (pby1 - pby0) / z),
            })

        # 检测概率图的紧框仍会含一点出血（低对比度拍照件能到 1 个行距），
        # 直接用会把打码块蹭到上一行。按本页行距封顶：字高不超过行距的 0.68，
        # 居中位置不动——这样既不盖到邻行，也不会把字裁掉半个。
        if items:
            cys = sorted((it["y0"] + it["y1"]) / 2.0 for it in items)
            gaps = [b - a for a, b in zip(cys, cys[1:]) if b - a > 1.0]
            if gaps:
                gaps.sort()
                pitch = gaps[len(gaps) // 2]
                cap = pitch * 0.68
                for it in items:
                    h = it["y1"] - it["y0"]
                    if h > cap:
                        c = (it["y0"] + it["y1"]) / 2.0
                        it["y0"] = c - cap / 2.0
                        it["y1"] = c + cap / 2.0

        return _group_lines(items)


def _group_lines(items):
    """把检测框拼成「视觉行」，与 pdfmask._visual_lines 的分行口径保持一致

    返回的每个字都带 pymupdf.Rect —— 上层规则直接拿去做几何运算。
    """
    import pymupdf

    if not items:
        return []
    items.sort(key=lambda it: ((it["y0"] + it["y1"]) / 2.0, it["x0"]))

    groups = []
    for it in items:
        cy = (it["y0"] + it["y1"]) / 2.0
        # 用原检测框高度做聚类容差；字框收紧不影响「同一行」的判断
        hh = it.get("tol") or (it["y1"] - it["y0"])
        hit = None
        for g in groups:
            if abs(g["cy"] - cy) <= max(2.0, max(g["h"], hh) * 0.42):
                hit = g
                break
        if hit is None:
            groups.append({"cy": cy, "h": hh, "items": [it]})
        else:
            hit["items"].append(it)
            hit["h"] = max(hit["h"], hh)

    out = []
    for g in groups:
        seq = sorted(g["items"], key=lambda it: it["x0"])
        parts, entries = [], []
        prev_x1 = None
        prev_h = g["h"]
        for it in seq:
            if prev_x1 is not None and it["x0"] - prev_x1 > max(0.9, min(prev_h, it["y1"] - it["y0"]) * 0.42):
                parts.append(" ")
                entries.append((" ", None))
            hgt = it["y1"] - it["y0"]
            chars = it["chars"]
            # 同一个检测框内的字矩形首尾相接：CTC 反推的区间只是估计值，
            # 留缝会既切不准字、又让打码块之间露白（漏字就是漏隐私）
            spans = []
            for k in range(len(chars)):
                ch, f0, f1 = chars[k][0], chars[k][1], chars[k][2]
                b0 = ((chars[k - 1][2] + f0) / 2.0) if k else f0
                b1 = ((f1 + chars[k + 1][1]) / 2.0) if k + 1 < len(chars) else f1
                if b1 <= b0:
                    b0, b1 = f0, f1
                spans.append((ch, b0, b1))
            width = it["x1"] - it["x0"]
            box_h = it["y1"] - it["y0"]
            # 检测框是「整行外接框」，里面还含行距、检测器 padding 和轻微倾斜的余量，
            # 实测高度约为真实字高的 2 倍。以前直接拿它当每个字的矩形，
            # 打码块就向上/下各多盖半行：相邻两行的灰条连成一片，
            # 还会把上一行打码框下面那几个字一起糊掉。
            # 这里按行高估一个真实字高，居中收窄；宁可留一点点笔画边缘，
            # 也不能再牺牲正常文字——缩得不够就还是「连成一片」。
            # 纵向已经是「检测紧框 + 行距封顶」，不再二次收窄
            gy0, gy1 = it["y0"], it["y1"]
            glyph_h = gy1 - gy0
            # 单个字的 CTC 区间容易偏窄（模型把字挤在中间几步里），框会小得盖不住字形。
            # 给一个按字高算的下限：汉字宽约等于字高，宁可多盖一点，也不能露半个字。
            min_w = min(glyph_h * 0.9, width * 0.6)
            for ch, b0, b1 in spans:
                cx0 = it["x0"] + width * b0
                cx1 = it["x0"] + width * b1
                if cx1 - cx0 < min_w:
                    mid = (cx0 + cx1) / 2.0
                    cx0 = max(it["x0"], mid - min_w / 2.0)
                    cx1 = min(it["x1"], mid + min_w / 2.0)
                    if cx1 - cx0 < min_w:      # 贴到框边时允许向外溢出
                        cx0 = mid - min_w / 2.0
                        cx1 = mid + min_w / 2.0
                parts.append(ch)
                entries.append((ch, pymupdf.Rect(cx0, gy0, cx1, gy1)))
            prev_h = hgt
            prev_x1 = it["x1"]
        out.append(("".join(parts), entries))
    return out


# ---------------------------------------------------------------------------
# 页面路由：判断哪些页需要 OCR
# ---------------------------------------------------------------------------

def page_text_units(page):
    """统计这页可用文字：返回 (字符数, 图片数, 面积占比)"""
    chars = 0
    try:
        d = page.get_text("rawdict")
        for blk in d.get("blocks", []):
            if blk.get("type", 0) != 0:
                continue
            for line in blk.get("lines", []):
                for span in line.get("spans", []):
                    for ch in span.get("chars", []):
                        if ch.get("c", "").strip():
                            chars += 1
    except Exception:
        pass
    imgs = 0
    cover = 0.0
    try:
        prect = page.rect
        parea = max(1.0, prect.width * prect.height)
        infos = page.get_image_info()
        imgs = len(infos)
        for it in infos:
            r = it.get("bbox")
            if not r:
                continue
            x0, y0, x1, y1 = r
            w = max(0.0, min(x1, prect.x1) - max(x0, prect.x0))
            h = max(0.0, min(y1, prect.y1) - max(y0, prect.y0))
            cover += w * h
        cover = min(1.0, cover / parea)
    except Exception:
        pass
    return chars, imgs, cover


def needs_ocr(page, min_chars: int = 24) -> bool:
    """这页要不要走 OCR

    判据：
    - 几乎没字（扫描件、拍照件、纯图片页）→ 要
    - 有字但字很少、同时整页被图片盖住（截图型 PDF）→ 要
    """
    chars, imgs, cover = page_text_units(page)
    if chars < min_chars:
        return True
    if imgs and cover >= 0.55 and chars < min_chars * 6:
        return True
    return False


def warmup():
    """提前把模型读进内存，避免第一次点「识别」时卡两秒"""
    try:
        if available():
            OcrEngine.get()
            return True
    except Exception:
        pass
    return False
