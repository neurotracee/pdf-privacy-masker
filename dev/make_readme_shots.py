# -*- coding: utf-8 -*-
"""生成 README / 文档用的「带壳截屏」：真实界面渲染 + 设备外框，中英双语两套。

为什么不用现成截图裁一下
------------------------
README 里原来放的是纯界面截图（Windows 1120×720、安卓 1080×2400），
贴到页面上显得寡淡，也分不出中英文两套。这里做两件事：

1. **出图**：Windows 端拿程序真正在浏览器里跑的那一页（pdfmask.HTML_UI），
   喂一份真实 PDF 的检测结果（真跑 pdfmask.detect，不是编的），用无头 Edge
   截成 2 倍图；安卓端直接用 Robolectric 的界面截图（app/build/ui-shots）。
2. **套壳**：Windows 窗口（标题栏 + 最小化/最大化/关闭）、手机（圆角边框 +
   挖孔 + 侧键）都用 PIL 画出来，配柔和渐变底和投影，仿 DSH Go 的 README。

产物（docs/img/shot/）
    win-work-{zh,en}.webp        单个 Windows 窗口
    win-settings-{zh,en}.webp
    phone-home-{zh,en}.webp      单个手机
    phone-work-{zh,en}.webp
    phone-settings-{zh,en}.webp
    win-feature-{zh,en}.webp     2400×1500 两窗口并排
    phone-feature-{zh,en}.webp   2400×1500 三台手机并排
    hero-{zh,en}.webp            2560×1280 首页横幅

用法：
    python dev/make_readme_shots.py            # 全部生成
    python dev/make_readme_shots.py --win      # 只重出 Windows 截图
    python dev/make_readme_shots.py --frames   # 只重新套壳（复用已有截图）
"""
import base64
import glob
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img", "shot")
TMP = os.path.join(HERE, "_ui", "win")
ANDROID_SHOTS = os.path.join(ROOT, "android", "app", "build", "ui-shots")

EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

SAMPLE_PDF = os.path.join(ROOT, "test", "测试文档_含隐私.pdf")
# 英文版截图用英文文档，否则英文 README 里那张「主界面」的正文还是中文
EN_SAMPLE = os.path.join(ROOT, "dev", "fixtures", "en_sample.pdf")

# 视觉基调：仿 DSH Go 那种「极浅冷紫 → 极浅暖白」的斜向渐变
BG_TOP = (245, 246, 251)
BG_BOTTOM = (232, 235, 245)
BEZEL = (24, 26, 32)

# README 同时出明暗两套，页面里用 <picture> + prefers-color-scheme 切换；
# 深色主题下如果还贴浅色画布，整块图会亮得刺眼。
THEMES = {
    "light": dict(
        bg=(245, 246, 251), bg2=(232, 235, 245),
        glow1=((255, 255, 255), 110), glow2=((222, 230, 248), 90),
        shadow=(15, 23, 42), shadow_k=1.0,
        chrome=(246, 247, 250), titlebar=(245, 246, 249),
        edge=(214, 218, 228), win_text=(40, 44, 54), win_btn=(72, 78, 92),
        title=(22, 26, 36), sub=(96, 102, 118), brand=(90, 96, 112),
        pill=(255, 255, 255, 210), pill_edge=(214, 220, 232, 255),
        pill_text=(60, 66, 82), fine=(148, 154, 168),
    ),
    "dark": dict(
        bg=(20, 23, 30), bg2=(9, 11, 16),
        glow1=((56, 74, 110), 120), glow2=((26, 36, 58), 120),
        shadow=(0, 0, 0), shadow_k=1.9,
        chrome=(34, 38, 47), titlebar=(38, 42, 52),
        edge=(58, 63, 76), win_text=(224, 228, 237), win_btn=(196, 202, 216),
        title=(238, 241, 248), sub=(148, 156, 174), brand=(138, 146, 164),
        pill=(30, 34, 44, 220), pill_edge=(58, 64, 80, 255),
        pill_text=(202, 210, 226), fine=(118, 126, 144),
    ),
}
TH = THEMES["light"]


def set_theme(name):
    global TH
    TH = THEMES[name]


# ----------------------------------------------------------------- 字体 / 图标
def font(size, bold=False, en=False):
    cands = []
    if en:
        cands = [r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"]
    cands += [r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"]
    for c in cands:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def app_icon(px):
    ico = os.path.join(ROOT, "app.ico")
    try:
        im = Image.open(ico)
        im.size = (256, 256)
        im = im.convert("RGBA")
        return im.resize((px, px), Image.LANCZOS)
    except Exception:
        return Image.new("RGBA", (px, px), (37, 99, 235, 255))


# ------------------------------------------------------------ Windows 出图
MOCK_DOC = """
  var DOC = __DOC__;
  var CFG = __CFG__;
"""


def _doc_payload(lang):
    """真跑一遍检测，同时返回前端 DOC 与预览渲染要用的 state。"""
    import pdfengine
    import pdfmask

    src = SAMPLE_PDF if lang == "zh" else EN_SAMPLE
    doc = pdfengine.open_doc(src)
    findings = pdfmask.detect(doc, use_ocr=False)
    pages = []
    for i in range(len(doc)):
        r = doc[i].rect
        pages.append({"w": int(r.width), "h": int(r.height),
                      "hasText": True, "rot": 0})
    items = []
    stats = {}
    for i, f in enumerate(findings):
        label = pdfmask.TYPE_NAME.get(f["type"], f["type"])
        mask = pdfmask._mask_text(f["type"], f["text"])
        r = f["rect"]
        items.append({"id": "f%d" % i, "type": f["type"], "label": label,
                      "mask": mask, "page": f["page"],
                      "rect": [float(r.x0), float(r.y0), float(r.x1), float(r.y1)],
                      "note": f.get("note") or "", "suspect": False})
        stats[label] = stats.get(label, 0) + 1
    name = "员工信息登记表.pdf" if lang == "zh" else "employee-records.pdf"
    docj = {"docId": "t1", "name": name, "size": os.path.getsize(src),
            "pages": pages, "findings": items, "scanned": [],
            "outDir": "D:\\\\HugoMoveData\\\\User\\\\YB\\\\Downloads",
            "stats": stats}
    cfg = {"saveDir": "", "rememberDir": True, "noAsk": False,
           "defaultDir": "D:\\\\HugoMoveData\\\\User\\\\YB\\\\Downloads",
           "effectiveDir": "D:\\\\HugoMoveData\\\\User\\\\YB\\\\Downloads",
           "configured": False, "lang": lang,
           "settingsPath": "C:\\\\Users\\\\YB\\\\AppData\\\\Roaming\\\\PDF隐私打码工具\\\\settings.json"}

    class _State(object):
        pass

    st = _State()
    st.doc = doc
    st.findings = findings
    return docj, cfg, st


def build_win_html(lang, scene):
    import make_ui_preview as P
    import pdfmask

    docj, cfg, state = _doc_payload(lang)
    mock = P.MOCK.replace("__DIGEST__", "{}")
    # 用真数据替掉脚本里写死的那份 DOC / CFG
    mock = re.sub(r"  var DOC = \{.*?\n  \};", "  var DOC = %s;" %
                  json.dumps(docj, ensure_ascii=False), mock, count=1, flags=re.S)
    mock = re.sub(r"  var CFG = \{.*?\n             settingsPath:'[^']*'\};",
                  "  var CFG = %s;" % json.dumps(cfg, ensure_ascii=False), mock,
                  count=1, flags=re.S)

    base = pdfmask.HTML_UI
    base = (base.replace("__TOKEN__", "testtoken")
                .replace("__BOOT__", '""')
                .replace("__VERSION__", pdfmask.VERSION)
                .replace("__AUTHOR__", pdfmask.AUTHOR)
                .replace("__DEVELOPER__", pdfmask.DEVELOPER)
                .replace("__LICENSE__", pdfmask.LICENSE_NAME)
                .replace("__CREDIT__", pdfmask.CREDIT_LINE)
                .replace("__URLSHORT__", pdfmask.URL_SHORT)
                .replace("__URL__", pdfmask.PROJECT_URL)
                .replace("__THANKS__", pdfmask.QR_PNG_B64))
    # 界面语言：初始化时有些按钮不会跟着 CFG.lang 走，点一次语言切换才会全量重译
    # （和 dev/make_ui_preview.py 的 ui_12_work_en 是同一套做法）。
    boot = ("<script>try{S.zoom=1.0;}catch(e){};"
            "window.__ready(function(){"
            "try{document.querySelector('.seg-btn[data-lang=%s]').click();}catch(e){}"
            % lang
            + ("setTimeout(function(){document.getElementById('setBtn').click();},60);"
               if scene == "settings" else "")
            + "});</script>")
    html = base.replace("<body>", "<body>" + mock, 1).replace("</body>", boot + "</body>", 1)
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, "win-%s-%s.html" % (scene, lang))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path, state


def shot_win(html_path, state, png_path, w=1120, h=720, scale=2):
    """起一个只服务「页面 + /api/preview」的小服务，再用无头 Edge 截图。

    直接把 file:// 页面打开的话，/api/preview 是相对路径、拿不到图，右侧预览会
    变成裂图；起服务后可以直接调程序自己的 _preview_png 出图，框选高亮、马赛克
    都是真实渲染结果，不靠另外画一遍。
    """
    import threading
    import urllib.parse
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import pdfmask

    with open(html_path, "rb") as fh:
        html_bytes = fh.read()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api/preview"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    body = pdfmask._preview_png(
                        state,
                        int(q.get("page", ["0"])[0]),
                        float(q.get("zoom", ["1.0"])[0]),
                        set(x for x in (q.get("sel", [""])[0]).split(",") if x),
                        q.get("mask", ["1"])[0] == "1",
                        q.get("hi", [""])[0])
                    ctype = "image/png"
                except Exception as e:  # 预览出错就回一张白图，别让整页裂掉
                    body = b""
                    ctype = "image/png"
                    print("    preview 失败：%s" % e)
            else:
                body, ctype = html_bytes, "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        exe = next((e for e in EDGE if os.path.exists(e)), None)
        if not exe:
            raise SystemExit("找不到 Edge / Chrome，无法截图")
        args = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--no-first-run", "--force-color-profile=srgb",
                "--user-data-dir=" + os.path.join(os.environ.get("TEMP", "."),
                                                  "edge-readme-shot"),
                "--virtual-time-budget=8000",
                "--screenshot=" + os.path.abspath(png_path),
                "--window-size=%d,%d" % (w, h),
                "--force-device-scale-factor=%d" % scale,
                "http://127.0.0.1:%d/" % port]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180)
    finally:
        srv.shutdown()
        srv.server_close()
    if not os.path.exists(png_path) or os.path.getsize(png_path) < 10000:
        raise SystemExit("截图失败：%s\n%s" % (html_path, (r.stderr or "")[-500:]))
    return png_path


def make_win_shots():
    out = {}
    for lang in ("zh", "en"):
        for scene in ("work", "settings"):
            html, state = build_win_html(lang, scene)
            png = os.path.join(TMP, "win-%s-%s.png" % (scene, lang))
            shot_win(html, state, png)
            out[(scene, lang)] = png
            print("  Windows 截图 %-9s %s" % (lang, os.path.basename(png)))
    return out


# --------------------------------------------------------------- 套壳：窗口
def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def shadow(canvas, box, radius, blur, alpha, offset=(0, 18)):
    """在 canvas 上给 box 画一层柔和投影。"""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    b = [box[0] + offset[0], box[1] + offset[1], box[2] + offset[0], box[3] + offset[1]]
    col = TH["shadow"] + (min(255, int(alpha * TH["shadow_k"])),)
    d.rounded_rectangle(b, radius=radius, fill=col)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(layer)


def frame_window(shot_path, title, scale_title=1.0):
    """把网页截图放进 Windows 11 风格的窗口里（含标题栏与窗口按钮）。"""
    src = Image.open(shot_path).convert("RGB")
    s = 2  # 截图是 2 倍图
    bar_h = 38 * s
    radius = 12 * s
    W, H = src.size
    win = Image.new("RGBA", (W, H + bar_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(win)
    chrome = TH["chrome"] + (255,)
    titlebar = TH["titlebar"] + (255,)
    d.rounded_rectangle([0, 0, W - 1, win.height - 1], radius=radius, fill=chrome)
    # 标题栏
    d.rounded_rectangle([0, 0, W - 1, bar_h + radius], radius=radius, fill=titlebar)
    d.rectangle([0, bar_h - radius, W - 1, bar_h], fill=titlebar)
    d.line([0, bar_h, W - 1, bar_h], fill=TH["edge"] + (255,), width=max(1, s // 2))
    # 图标 + 标题
    ic = app_icon(int(18 * s * scale_title))
    win.alpha_composite(ic, (14 * s, (bar_h - ic.height) // 2))
    f = font(int(13 * s * scale_title), en=False)
    d.text((14 * s + ic.width + 10 * s, (bar_h - int(13 * s * 1.35)) // 2),
           title, font=f, fill=TH["win_text"] + (255,))
    # 窗口按钮：最小化 / 最大化 / 关闭
    bx = W - 20 * s
    cy = bar_h // 2
    lw = max(1, int(1.2 * s))
    col = TH["win_btn"] + (255,)
    d.line([bx - 34 * s, cy, bx - 24 * s, cy], fill=col, width=lw)          # —
    d.rectangle([bx - 16 * s, cy - 5 * s, bx - 6 * s, cy + 5 * s],
                outline=col, width=lw)                                       # □
    d.line([bx + 4 * s, cy - 5 * s, bx + 14 * s, cy + 5 * s], fill=col, width=lw)   # ✕
    d.line([bx + 4 * s, cy + 5 * s, bx + 14 * s, cy - 5 * s], fill=col, width=lw)
    # 页面内容
    win.paste(src, (0, bar_h))
    # 圆角裁切
    win.putalpha(rounded_mask(win.size, radius))
    return win


# --------------------------------------------------------------- 套壳：手机
def frame_phone(shot_path, radius_scale=1.0):
    """把 1080×2400 的安卓截图放进手机外框：黑边 + 挖孔 + 侧键。"""
    src = Image.open(shot_path).convert("RGB")
    W, H = src.size
    bez = int(W * 0.016)
    outer_r = int(W * 0.115)
    inner_r = int(outer_r - bez * 0.9)
    ow, oh = W + bez * 2, H + bez * 2
    canvas = Image.new("RGBA", (ow + 16, oh + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    # 侧键（先画，压在机身下面）
    bw, bh = int(bez * 0.55), int(H * 0.075)
    d.rounded_rectangle([8, int(oh * 0.20), 8 + bw, int(oh * 0.20) + bh],
                        radius=bw // 2, fill=(58, 62, 74, 255))
    d.rounded_rectangle([8, int(oh * 0.32), 8 + bw, int(oh * 0.32) + int(bh * 1.4)],
                        radius=bw // 2, fill=(58, 62, 74, 255))
    d.rounded_rectangle([ow + 8 - bw, int(oh * 0.28), ow + 8,
                         int(oh * 0.28) + int(bh * 1.6)], radius=bw // 2,
                        fill=(58, 62, 74, 255))
    # 机身
    d.rounded_rectangle([8, 8, ow + 7, oh + 7], radius=outer_r, fill=BEZEL + (255,))
    # 深色画布上机身会融进背景，描一圈浅边把轮廓拉出来
    d.rounded_rectangle([8, 8, ow + 7, oh + 7], radius=outer_r,
                        outline=(96, 102, 118, 90), width=2)
    # 屏幕
    screen = Image.new("RGBA", (W, H))
    screen.paste(src, (0, 0))
    m = rounded_mask((W, H), inner_r)
    canvas.paste(screen, (8 + bez, 8 + bez), m)
    # 挖孔摄像头
    cr = int(W * 0.018)
    cx, cy = ow // 2 + 8, 8 + bez + int(H * 0.012) + cr
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(10, 11, 14, 255))
    # 底部手势条
    gb = int(W * 0.22)
    d.rounded_rectangle([ow // 2 + 8 - gb // 2, oh + 8 - bez - int(H * 0.012),
                         ow // 2 + 8 + gb // 2, oh + 8 - bez - int(H * 0.012) + int(W * 0.006)],
                        radius=int(W * 0.004), fill=(180, 182, 190, 255))
    return canvas


# ------------------------------------------------------------------- 画布
def gradient_bg(size, top=BG_TOP, bottom=BG_BOTTOM):
    W, H = size
    base = Image.new("RGB", (2, 2))
    base.putpixel((0, 0), top)
    base.putpixel((1, 1), bottom)
    base.putpixel((1, 0), tuple((a + b) // 2 for a, b in zip(top, bottom)))
    base.putpixel((0, 1), tuple((a + b) // 2 for a, b in zip(top, bottom)))
    return base.resize(size, Image.BICUBIC).convert("RGBA")


def glow(canvas, center, radius, color=(255, 255, 255), alpha=120):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([center[0] - radius, center[1] - radius,
               center[0] + radius, center[1] + radius], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius // 3))
    canvas.alpha_composite(layer)


def placeholder_win(lang, scene, size=(2240, 1516)):
    """没有截图时的替代：浅色底 + 一行字，保证套壳流程可单测。"""
    im = gradient_bg((size[0], size[1] - 76), (250, 250, 252), (244, 246, 250))
    d = ImageDraw.Draw(im)
    d.text((40, 40), "win %s %s" % (scene, lang), font=font(40), fill=(120, 126, 140))
    return im


# --------------------------------------------------------------- 排版：画布
def canvas(size):
    c = gradient_bg(size, TH["bg"], TH["bg2"])
    glow(c, (int(size[0] * 0.78), int(size[1] * 0.12)), int(size[0] * 0.34),
         TH["glow1"][0], TH["glow1"][1])
    glow(c, (int(size[0] * 0.12), int(size[1] * 0.95)), int(size[0] * 0.40),
         TH["glow2"][0], TH["glow2"][1])
    return c


def drop_in(base, img, pos, radius=36, blur=42, alpha=70, offset=(0, 26)):
    """把 img 贴到 base 的 pos，并先画一层投影。"""
    box = [pos[0], pos[1], pos[0] + img.width, pos[1] + img.height]
    shadow(base, box, radius, blur, alpha, offset)
    base.alpha_composite(img, pos)


def fit(img, max_w=None, max_h=None):
    w, h = img.size
    s = 1.0
    if max_w:
        s = min(s, max_w / float(w))
    if max_h:
        s = min(s, max_h / float(h))
    if s < 1.0:
        img = img.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    return img


def save(img, name, width=2400, quality=90):
    os.makedirs(OUT, exist_ok=True)
    if img.width > width:
        ratio = width / float(img.width)
        img = img.resize((width, int(img.height * ratio)), Image.LANCZOS)
    path = os.path.join(OUT, name)
    img.convert("RGB").save(path, "WEBP", quality=quality, method=6)
    print("  -> docs/img/shot/%s  (%d×%d, %.0f KB)" %
          (name, img.width, img.height, os.path.getsize(path) / 1024))
    return path


# ------------------------------------------------------------- 单张带壳图
def shot_window_png(lang, scene):
    return os.path.join(TMP, "win-%s-%s.png" % (scene, lang))


WIN_TITLE = {"zh": "PDF 隐私打码工具", "en": "PDF Privacy Masker"}


def single_window(lang, scene):
    src = Image.open(shot_window_png(lang, scene)).convert("RGB")
    win = frame_window(shot_window_png(lang, scene), WIN_TITLE[lang])
    win = fit(win, max_w=1960)
    pad = 96
    cv = canvas((win.width + pad * 2, win.height + pad * 2 + 20))
    drop_in(cv, win, (pad, pad), radius=24, blur=48, alpha=64)
    return cv


def single_phone(lang, scene):
    src = PHONE_SRC[(scene, lang)]
    ph = frame_phone(src)
    ph = fit(ph, max_h=1900)
    pad = 120
    cv = canvas((ph.width + pad * 2, ph.height + pad * 2))
    drop_in(cv, ph, (pad, pad), radius=int(ph.width * 0.12), blur=50, alpha=70)
    return cv


# --------------------------------------------------------- 横向功能图（2400）
def win_feature(lang):
    a = frame_window(shot_window_png(lang, "work"), WIN_TITLE[lang])
    b = frame_window(shot_window_png(lang, "settings"), WIN_TITLE[lang])
    W, H = 2400, 1500
    a = fit(a, max_h=1040)
    b = fit(b, max_h=900)
    cv = canvas((W, H))
    # 一前一后：工作区在后，设置在前，右下压住一点，像桌面上摊开的两扇窗
    ax = 70
    ay = (H - a.height) // 2 - 40
    bx = W - b.width - 60
    by = (H - b.height) // 2 + 160
    drop_in(cv, a, (ax, ay), radius=26, blur=56, alpha=62)
    drop_in(cv, b, (bx, by), radius=26, blur=56, alpha=76, offset=(0, 30))
    return cv


PHONE_LABELS = {"home": "01-home-phone-portrait.png", "work": "04-work-phone-portrait.png",
                "settings": "16-settings-zh.png"}
PHONE_LABELS_EN = {"home": "14-home-english.png", "work": "15-work-english.png",
                   "settings": "17-settings-en.png"}
PHONE_SRC = {}


def load_phone_src():
    for scene in ("home", "work", "settings"):
        for lang, table in (("zh", PHONE_LABELS), ("en", PHONE_LABELS_EN)):
            p = os.path.join(ANDROID_SHOTS, table[scene])
            if not os.path.exists(p):
                raise SystemExit("缺安卓截图：%s（先跑 UiShotTest）" % p)
            PHONE_SRC[(scene, lang)] = p


def phone_feature(lang):
    shots = [frame_phone(PHONE_SRC[(s, lang)]) for s in ("home", "work", "settings")]
    shots = [fit(p, max_h=1230) for p in shots]
    W, H = 2400, 1500
    cv = canvas((W, H))
    total = sum(p.width for p in shots) + 90 * (len(shots) - 1)
    x = (W - total) // 2
    for i, p in enumerate(shots):
        y = (H - p.height) // 2 - (18 if i == 1 else 0)
        drop_in(cv, p, (x, y), radius=int(p.width * 0.12), blur=52, alpha=72,
                offset=(0, 26))
        x += p.width + 90
    return cv


# ------------------------------------------------------------------- Hero
HERO = {
    "zh": dict(
        title=["PDF 隐私打码", "拖进去就好"],
        sub=["自动认出手机号、身份证号、银行卡、姓名等敏感信息，",
             "用不可还原的马赛克盖掉，全程在本机完成。"],
        pill="Windows  ·  Android  ·  不联网也能用",
        note="示意图为 AI 生成，仅供创意参考，具体以实际界面为准  ·  版式思路借鉴 DSH Go 项目",
        repo="详细见 GitHub：ccch1mneyyy/dsh-go"),
    "en": dict(
        title=["PDF Privacy", "Masker"],
        sub=["Detects phone numbers, ID numbers, bank cards,",
             "names and more — then covers them all with",
             "irreversible mosaic. Nothing leaves your device."],
        pill="Windows  ·  Android  ·  Works offline",
        note="AI-generated illustration, for reference only — the actual UI may differ  ·  layout inspired by DSH Go",
        repo="Details on GitHub: ccch1mneyyy/dsh-go"),
}


def hero(lang):
    # 左边留给文字（最宽约 1200），右侧整块放「窗口 + 两台手机」，
    # 两者之间留出空档，手机不压字。底部多留一条空白放右下角小字。
    W, H = 2900, 1480
    cv = canvas((W, H))
    win = frame_window(shot_window_png(lang, "work"), WIN_TITLE[lang])
    win = fit(win, max_w=1500)
    wx = W - win.width - 150          # 整块往左压一点，右边不留太空
    wy = 180
    drop_in(cv, win, (wx, wy), radius=26, blur=60, alpha=70, offset=(0, 34))

    # 两台手机必须等高、同一个 y：高度不同就会一高一低，看着像没摆正
    ph1 = fit(frame_phone(PHONE_SRC[("home", lang)]), max_h=700)
    ph2 = fit(frame_phone(PHONE_SRC[("work", lang)]), max_h=700)
    py = H - max(ph1.height, ph2.height) - 150
    drop_in(cv, ph1, (wx - 20, py),
            radius=int(ph1.width * 0.12), blur=50, alpha=80, offset=(0, 26))
    drop_in(cv, ph2, (wx + win.width - ph2.width - 60, py),
            radius=int(ph2.width * 0.12), blur=50, alpha=80, offset=(0, 26))

    d = ImageDraw.Draw(cv)
    ic = app_icon(96)
    cv.alpha_composite(ic, (140, 150))
    x = 140 + 96 + 28
    d.text((x, 162), "pdf-privacy-masker", font=font(40, en=True), fill=TH["brand"])

    y = 300
    for line in HERO[lang]["title"]:
        d.text((140, y), line, font=font(108, bold=True, en=(lang == "en")),
               fill=TH["title"])
        y += 128
    y += 20
    for line in HERO[lang]["sub"]:
        d.text((140, y), line, font=font(40, en=(lang == "en")), fill=TH["sub"])
        y += 60
    d.rounded_rectangle([140, y + 32, 140 + 700, y + 32 + 76], radius=38,
                        fill=TH["pill"], outline=TH["pill_edge"], width=2)
    d.text((140 + 34, y + 32 + 19), HERO[lang]["pill"],
           font=font(33, en=(lang == "en")), fill=TH["pill_text"])

    # 左下角两行小字：第一行说明这张图是合成示意、并注明版式借鉴来源，
    # 第二行只写仓库路径（不带 https，越短越好）。整块离底边留出约两厘米。
    fn = font(26, en=(lang == "en"))
    d.text((140, H - 150), HERO[lang]["note"], font=fn, fill=TH["fine"])
    d.text((140, H - 106), HERO[lang]["repo"], font=font(26, en=(lang == "en")), fill=TH["fine"])
    return cv


def lang_compare():
    """中英文同屏：左中文、右英文，说明「切换语言后界面整体变英文」。"""
    a = frame_window(shot_window_png("zh", "work"), WIN_TITLE["zh"])
    b = frame_window(shot_window_png("en", "work"), WIN_TITLE["en"])
    W, H = 2400, 1260
    a = fit(a, max_w=1120)
    b = fit(b, max_w=1120)
    cv = canvas((W, H))
    gap = 60
    total = a.width + b.width + gap
    x = (W - total) // 2
    drop_in(cv, a, (x, (H - a.height) // 2), radius=22, blur=48, alpha=58)
    drop_in(cv, b, (x + a.width + gap, (H - b.height) // 2), radius=22, blur=48, alpha=58)
    return cv


# ------------------------------------------------------------------- 入口
def main():
    args = set(sys.argv[1:])
    load_phone_src()
    if args & {"--win", "--all", ""} or not args:
        print("Windows 截图")
        for lang in ("zh", "en"):
            for scene in ("work", "settings"):
                h, state = build_win_html(lang, scene)
                shot_win(h, state, shot_window_png(lang, scene), w=1440, h=900)
                print("  %s / %s" % (lang, scene))
    if args and args <= {"--win"}:
        return
    for theme in ("light", "dark"):
        set_theme(theme)
        print("套壳出图 · %s" % theme)
        for lang in ("zh", "en"):
            suf = "%s-%s.webp" % (lang, theme)
            save(single_window(lang, "work"), "win-work-" + suf)
            save(single_window(lang, "settings"), "win-settings-" + suf)
            save(phone_feature(lang), "phone-feature-" + suf)
            save(hero(lang), "hero-" + suf)
            save(lang_compare(), "lang-" + suf)


if __name__ == "__main__":
    main()
