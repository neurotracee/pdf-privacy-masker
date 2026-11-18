# -*- coding: utf-8 -*-
"""PDF 引擎适配层 —— 一个「转接头」。

全项目只有这一个文件认识 PyMuPDF。业务代码只说三件事：几何（Rect）、
位图（Pixmap）、文档（Doc / Page）。哪天要换内核（pypdfium2、pikepdf、
商业库 Artifex / 其它），只需要在本文件里再实现一份后端、把 ``_BACKEND``
换掉，`pdfmask.py` / `pdfmask_ocr.py` 一行都不用动。

为什么值得这么做：PyMuPDF 的 ``Rect`` 既当几何类型用、又自带 ``| & + - *``
运算符，项目里有上百处几何运算挂在它身上；如果把这种类型直接铺在业务代码里，
换库就不再是「换一个 import」，而是要重写所有几何表达式。

这里的 ``Rect`` 是纯 Python 实现，语义与 PyMuPDF 对齐（并集 / 交集 / 平移 /
缩放 / 取整 / 空判断），只在进出后端的边界上转换成底层对象。

约定：本文件对外只暴露下面这些名字，其它一律视为内部实现。
"""
from __future__ import annotations

import io

# ---------------------------------------------------------------------------
# 唯一一处底层依赖。想换内核，改这一行 + 文件末尾的 _BACKEND 即可。
# ---------------------------------------------------------------------------
import pymupdf as _m

# 常量直接转发（apply_redactions 之类要的是底层枚举值，用整数即可）
PDF_REDACT_IMAGE_NONE = _m.PDF_REDACT_IMAGE_NONE
PDF_REDACT_LINE_ART_NONE = _m.PDF_REDACT_LINE_ART_NONE
PDF_REDACT_TEXT_REMOVE = _m.PDF_REDACT_TEXT_REMOVE
CS_RGB = _m.csRGB

__all__ = [
    "Rect", "Point", "Matrix", "Pixmap", "Page", "Doc",
    "open_doc", "new_doc",
    "PDF_REDACT_IMAGE_NONE", "PDF_REDACT_LINE_ART_NONE",
    "PDF_REDACT_TEXT_REMOVE", "CS_RGB",
]


# ---------------------------------------------------------------------------
# 几何
# ---------------------------------------------------------------------------
class Point:
    """一个点。只用来给 Rect 做参数，不参与运算。"""

    __slots__ = ("x", "y")

    def __init__(self, x=0.0, y=0.0):
        if isinstance(x, Point):
            self.x, self.y = x.x, x.y
        elif isinstance(x, (tuple, list)):
            self.x, self.y = float(x[0]), float(x[1])
        else:
            self.x, self.y = float(x), float(y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, i):
        return (self.x, self.y)[i]

    def __add__(self, o):
        return Point(self.x + o[0], self.y + o[1])

    def __sub__(self, o):
        return Point(self.x - o[0], self.y - o[1])

    def __eq__(self, o):
        return isinstance(o, Point) and (self.x, self.y) == (o.x, o.y)

    def __repr__(self):
        return "Point(%g, %g)" % (self.x, self.y)


class Rect:
    """矩形。语义与 ``pymupdf.Rect`` 对齐：

    * ``Rect()`` 空矩形；``Rect(r)`` 拷贝；``Rect(seq)`` 四元组；
      ``Rect(x0, y0, x1, y1)``；``Rect(p0, p1)`` 两个点。
    * ``a & b`` 交集（无交集时为空矩形），``a | b`` 并集。
    * ``r + n`` / ``r - n`` 平移，``r * n`` / ``r / n`` 缩放，
      n 可以是标量或 2/4 元组。
    * ``.is_empty`` 判空，``.width/.height``、``.tl/.br`` 等是属性。
    """

    __slots__ = ("x0", "y0", "x1", "y1")

    def __init__(self, *args):
        n = len(args)
        if n == 0:
            self.x0 = self.y0 = self.x1 = self.y1 = 0.0
            return
        if n == 1:
            a = args[0]
            if isinstance(a, Rect) or hasattr(a, "x0"):
                self.x0, self.y0 = float(a.x0), float(a.y0)
                self.x1, self.y1 = float(a.x1), float(a.y1)
            elif isinstance(a, Point):
                self.x0, self.y0 = a.x, a.y
                self.x1, self.y1 = a.x, a.y
            else:
                v = list(a)
                if len(v) != 4:
                    raise ValueError("Rect 需要 4 个坐标，收到 %r" % (a,))
                self.x0, self.y0, self.x1, self.y1 = map(float, v)
            return
        if n == 2:
            p, q = args
            self.x0, self.y0 = float(p[0]), float(p[1])
            self.x1, self.y1 = float(q[0]), float(q[1])
            return
        if n == 4:
            self.x0, self.y0, self.x1, self.y1 = map(float, args)
            return
        raise ValueError("Rect 参数个数不对：%d" % n)

    # -- 基本协议 ----------------------------------------------------------
    def __iter__(self):
        yield self.x0
        yield self.y0
        yield self.x1
        yield self.y1

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self.x0, self.y0, self.x1, self.y1)[i]

    def __setitem__(self, i, v):
        v = float(v)
        if i == 0:
            self.x0 = v
        elif i == 1:
            self.y0 = v
        elif i == 2:
            self.x1 = v
        elif i == 3:
            self.y1 = v
        else:
            raise IndexError(i)

    def __eq__(self, o):
        try:
            return (self.x0, self.y0, self.x1, self.y1) == (
                float(o[0]), float(o[1]), float(o[2]), float(o[3]))
        except Exception:
            return NotImplemented

    def __hash__(self):
        return hash((self.x0, self.y0, self.x1, self.y1))

    def __repr__(self):
        return "Rect(%g, %g, %g, %g)" % (self.x0, self.y0, self.x1, self.y1)

    # -- 属性 --------------------------------------------------------------
    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0

    @property
    def is_empty(self):
        return self.x0 >= self.x1 or self.y0 >= self.y1

    @property
    def is_valid(self):
        return self.x0 <= self.x1 and self.y0 <= self.y1

    @property
    def tl(self):
        return Point(self.x0, self.y0)

    @property
    def tr(self):
        return Point(self.x1, self.y0)

    @property
    def bl(self):
        return Point(self.x0, self.y1)

    @property
    def br(self):
        return Point(self.x1, self.y1)

    @property
    def is_infinite(self):
        return abs(self.x0) > 2 ** 31 or abs(self.y0) > 2 ** 31

    # -- 运算符 ------------------------------------------------------------
    def __and__(self, other):
        r = Rect(other)
        if self.is_empty or r.is_empty:
            return Rect()
        return Rect(max(self.x0, r.x0), max(self.y0, r.y0),
                    min(self.x1, r.x1), min(self.y1, r.y1))

    def __or__(self, other):
        r = Rect(other)
        if self.is_empty:
            return Rect(r)
        if r.is_empty:
            return Rect(self)
        return Rect(min(self.x0, r.x0), min(self.y0, r.y0),
                    max(self.x1, r.x1), max(self.y1, r.y1))

    def _shift(self, other, sign):
        o = _as_sequence(other)
        if len(o) == 4:
            return Rect(self.x0 + sign * o[0], self.y0 + sign * o[1],
                        self.x1 + sign * o[2], self.y1 + sign * o[3])
        return Rect(self.x0 + sign * o[0], self.y0 + sign * o[1],
                    self.x1 + sign * o[0], self.y1 + sign * o[1])

    def __add__(self, other):
        return self._shift(other, 1)

    def __sub__(self, other):
        return self._shift(other, -1)

    def _scale(self, other):
        o = _as_sequence(other)
        if len(o) == 4:
            return Rect(self.x0 * o[0], self.y0 * o[1],
                        self.x1 * o[2], self.y1 * o[3])
        return Rect(self.x0 * o[0], self.y0 * o[1],
                    self.x1 * o[0], self.y1 * o[1])

    def __mul__(self, other):
        return self._scale(other)

    __rmul__ = __mul__

    def __truediv__(self, other):
        o = _as_sequence(other)
        if len(o) == 4:
            return Rect(self.x0 / o[0], self.y0 / o[1],
                        self.x1 / o[2], self.y1 / o[3])
        return Rect(self.x0 / o[0], self.y0 / o[1],
                    self.x1 / o[0], self.y1 / o[1])

    # -- 方法 --------------------------------------------------------------
    def round(self):
        return Rect(round(self.x0), round(self.y0),
                    round(self.x1), round(self.y1))

    @property
    def irect(self):
        return self.round()

    def normalize(self):
        return Rect(min(self.x0, self.x1), min(self.y0, self.y1),
                    max(self.x0, self.x1), max(self.y0, self.y1))

    def intersects(self, other):
        return not (self & other).is_empty

    def contains(self, x):
        if isinstance(x, Rect) or hasattr(x, "x0"):
            r = Rect(x)
            return (self.x0 <= r.x0 and self.y0 <= r.y0
                    and self.x1 >= r.x1 and self.y1 >= r.y1)
        p = Point(x)
        return self.x0 <= p.x <= self.x1 and self.y0 <= p.y <= self.y1

    def include_point(self, p):
        p = Point(p)
        self.x0, self.y0 = min(self.x0, p.x), min(self.y0, p.y)
        self.x1, self.y1 = max(self.x1, p.x), max(self.y1, p.y)
        return self

    def include_rect(self, r):
        merged = self | r
        self.x0, self.y0, self.x1, self.y1 = merged.x0, merged.y0, merged.x1, merged.y1
        return self

    def get_area(self):
        return max(0.0, self.width) * max(0.0, self.height)


def _as_sequence(v):
    if isinstance(v, (int, float)):
        return (v, v)
    if isinstance(v, Rect) or hasattr(v, "x0"):
        return (v.x0, v.y0, v.x1, v.y1)
    s = list(v)
    if len(s) == 2:
        return (float(s[0]), float(s[1]))
    if len(s) == 4:
        return tuple(map(float, s))
    raise ValueError("期望标量 / 2 元组 / 4 元组，收到 %r" % (v,))


class Matrix:
    """渲染矩阵。只用到缩放（``Matrix(z, z)``）和恒等。"""

    __slots__ = ("a", "b", "c", "d", "e", "f")

    def __init__(self, *args):
        if not args:
            self.a, self.b, self.c, self.d, self.e, self.f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
        elif len(args) == 2:
            zx, zy = float(args[0]), float(args[1])
            self.a, self.b, self.c, self.d, self.e, self.f = zx, 0.0, 0.0, zy, 0.0, 0.0
        elif len(args) == 6:
            self.a, self.b, self.c, self.d, self.e, self.f = map(float, args)
        else:
            raise ValueError("Matrix 只支持 (), (sx, sy), (a,b,c,d,e,f)")

    def __iter__(self):
        yield from (self.a, self.b, self.c, self.d, self.e, self.f)

    def __repr__(self):
        return "Matrix(%g, %g, %g, %g, %g, %g)" % tuple(self)


# ---------------------------------------------------------------------------
# 与底层之间的转换（只在本文件内使用）
# ---------------------------------------------------------------------------
def _to_raw_rect(r):
    """自有 Rect / 元组 -> 底层 Rect。已经是底层类型就原样返回。"""
    if isinstance(r, _m.Rect):
        return r
    if isinstance(r, Rect):
        return _m.Rect(r.x0, r.y0, r.x1, r.y1)
    if isinstance(r, _m.IRect):
        return _m.Rect(r)
    return _m.Rect(*list(r)[:4]) if len(list(r)) == 4 else _m.Rect(r)


def _to_raw_matrix(mat):
    if mat is None or isinstance(mat, _m.Matrix):
        return mat
    return _m.Matrix(mat.a, mat.b, mat.c, mat.d, mat.e, mat.f)


def _unwrap(x):
    """代理对象解包成底层对象；别的原样返回。"""
    return getattr(x, "_raw", x)


# ---------------------------------------------------------------------------
# 位图
# ---------------------------------------------------------------------------
class Pixmap:
    """底层位图的薄代理。

    只做两件事：把 ``samples / width / height / tobytes`` 透出去，
    以及在需要回传给后端时能拿回原始对象。不复制任何像素。
    """

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    @classmethod
    def from_bytes(cls, data):
        return cls(_m.Pixmap(data))

    @property
    def width(self):
        return self._raw.width

    @property
    def height(self):
        return self._raw.height

    @property
    def samples(self):
        return self._raw.samples

    def tobytes(self, fmt="png"):
        return self._raw.tobytes(fmt)

    def save(self, path):
        return self._raw.save(path)

    def __getattr__(self, name):
        return getattr(self._raw, name)


# ---------------------------------------------------------------------------
# 文档 / 页面
# ---------------------------------------------------------------------------
class Page:
    """一页。坐标一律以自有 ``Rect`` 出入，业务代码看不到底层类型。"""

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    @property
    def rect(self):
        return Rect(self._raw.rect)

    @property
    def rotation(self):
        return self._raw.rotation

    # -- 渲染 --------------------------------------------------------------
    def get_pixmap(self, clip=None, matrix=None, **kw):
        if clip is not None:
            kw["clip"] = _to_raw_rect(clip)
        if matrix is not None:
            kw["matrix"] = _to_raw_matrix(matrix)
        return Pixmap(self._raw.get_pixmap(**kw))

    # -- 文字层 ------------------------------------------------------------
    def get_text(self, *a, **k):
        return self._raw.get_text(*a, **k)

    # -- 抹除 --------------------------------------------------------------
    def add_redact_annot(self, rect, *a, **k):
        return self._raw.add_redact_annot(_to_raw_rect(rect), *a, **k)

    def apply_redactions(self, **k):
        return self._raw.apply_redactions(**k)

    # -- 贴图 --------------------------------------------------------------
    def insert_image(self, rect, *a, **k):
        if "pixmap" in k:
            k["pixmap"] = _unwrap(k["pixmap"])
        return self._raw.insert_image(_to_raw_rect(rect), *a, **k)

    # -- 表单域 / 注释 / 图片信息 ------------------------------------------
    def widgets(self):
        return self._raw.widgets()

    def annots(self):
        return self._raw.annots()

    def delete_widget(self, w):
        return self._raw.delete_widget(_unwrap(w))

    def delete_annot(self, a):
        return self._raw.delete_annot(_unwrap(a))

    def get_image_info(self, **k):
        return self._raw.get_image_info(**k)

    def show_pdf_page(self, rect, src, pno, **k):
        return self._raw.show_pdf_page(_to_raw_rect(rect), _unwrap(src), pno, **k)

    def __getattr__(self, name):
        # 兜底：还没被接口收编的属性直接透传，保证行为不变。
        return getattr(self._raw, name)


class Doc:
    """一份文档。``len(doc)`` / ``doc[i]`` / 迭代都给代理 Page。"""

    __slots__ = ("_raw",)

    def __init__(self, raw):
        self._raw = raw

    @property
    def page_count(self):
        return self._raw.page_count

    def __len__(self):
        return self._raw.page_count

    def __getitem__(self, i):
        return Page(self._raw[i])

    def __iter__(self):
        for i in range(self._raw.page_count):
            yield Page(self._raw[i])

    def close(self):
        return self._raw.close()

    def save(self, *a, **k):
        return self._raw.save(*a, **k)

    def set_toc(self, *a, **k):
        return self._raw.set_toc(*a, **k)

    def get_toc(self, *a, **k):
        return self._raw.get_toc(*a, **k)

    def set_metadata(self, *a, **k):
        return self._raw.set_metadata(*a, **k)

    def insert_pdf(self, src, *a, **k):
        return self._raw.insert_pdf(_unwrap(src), *a, **k)

    def new_page(self, **k):
        return Page(self._raw.new_page(**k))

    @property
    def needs_pass(self):
        return self._raw.needs_pass

    def __getattr__(self, name):
        return getattr(self._raw, name)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def open_doc(source=None, **kw):
    """打开文档。``source`` 可以是路径、bytes 或空（新建）。

    与 ``pymupdf.open`` 保持同一套调用方式，只是返回代理对象。
    """
    if source is None:
        return Doc(_m.open(**kw))
    if isinstance(source, (bytes, bytearray, memoryview)):
        return Doc(_m.open(stream=bytes(source), filetype=kw.pop("filetype", "pdf"), **kw))
    return Doc(_m.open(source, **kw))


def new_doc():
    return Doc(_m.open())


def as_doc(x):
    """把任意「文档样」的东西统一成代理 Doc。

    业务函数对外收文档时先过一道这个：调用方传路径、传底层 Document、
    传已经是代理的 Doc，都能收敛到同一种对象，后面的几何运算才不会
    在「自有 Rect」和「底层 Rect」之间打架。
    """
    if isinstance(x, Doc):
        return x
    if isinstance(x, str):
        return open_doc(x)
    return Doc(x)


def document_from_bytes(data):
    return Doc(_m.open(stream=data, filetype="pdf"))


def render_page(page, zoom=1.0, clip=None, alpha=False, colorspace=None):
    """把一页渲染成位图。

    这是给「手里可能是一个底层 Page、也可能是一个代理 Page」的地方用的：
    OCR 模块会拿到外部传进来的页对象，不能假设它一定是代理，也不能把自有
    Matrix 直接塞给底层接口（底层会静默忽略、退回 1 倍，图糊了但没人报错）。
    """
    raw = page._raw if isinstance(page, Page) else page
    kw = {"matrix": _m.Matrix(zoom, zoom), "alpha": alpha}
    if colorspace is not None:
        kw["colorspace"] = colorspace
    if clip is not None:
        kw["clip"] = _to_raw_rect(clip)
    return Pixmap(raw.get_pixmap(**kw))


def raw_rect(r):
    """自有 Rect / 元组 -> 底层 Rect。

    对外暴露它是为了让**测试脚本**也能安全地把矩形交给底层接口：
    PyMuPDF 的 ``clip=`` / ``rect=`` 参数只认自己的 Rect 和 tuple/list，
    收到别的东西不会报错，而是**静默忽略**（`get_pixmap(clip=...)` 直接
    渲染整页）。这类降级不抛异常，很容易把验证结论测偏。
    """
    return _to_raw_rect(r)
