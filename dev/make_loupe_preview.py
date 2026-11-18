# -*- coding: utf-8 -*-
"""把「放大镜里的实时虚线框」单独渲染成图，用来肉眼核对。

做法和 make_job_panel_preview.py 一样：拿程序真正在浏览器里跑的那一页，
把占位符填掉，再在末尾追加一小段脚本伪造一次「正在拖框」的中途状态，
然后让 Edge/Chrome 截图。

    python dev/make_loupe_preview.py       # 生成手动框选 / 橡皮擦两张
"""
import base64
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pdfmask as M  # noqa: E402
from pdfmask_webui import HTML_UI  # noqa: E402

OUT = os.path.join(HERE, "_ui")
os.makedirs(OUT, exist_ok=True)

EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

LINES = ["姓名：张伟", "身份证号：110101199003071234", "手机号码：13800138000",
         "会议日期：2026年11月20日", "合同金额：人民币 128000 元"]


def sample_png():
    """画一张「页面」：白底 + 几行黑字，放大后才看得出细节。"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (560, 360), (255, 255, 255))
    d = ImageDraw.Draw(img)
    y = 34
    for line in LINES:
        d.text((40, y), line, fill=(20, 24, 32))
        y += 34
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_html(mode):
    html = (HTML_UI
            .replace("__TOKEN__", "preview")
            .replace("__BOOT__", "null")
            .replace("__VERSION__", M.VERSION)
            .replace("__AUTHOR__", M.AUTHOR)
            .replace("__DEVELOPER__", M.DEVELOPER)
            .replace("__DEVELOPER_NOTE__", M.DEVELOPER_NOTE)
            .replace("__LICENSE__", M.LICENSE_NAME)
            .replace("__URL__", M.PROJECT_URL)
            .replace("__URLGITEE__", M.GITEE_URL)
            .replace("__CREDIT__", M.CREDIT_LINE)
            .replace("__URLSHORT__", M.URL_SHORT)
            .replace("__URLSHORT_GITEE__", M.URL_SHORT_GITEE)
            .replace("__THANKS__", M.QR_PNG_B64))
    tail = """
<script>
(function(){
  var img = $('pageImg');
  if(!img) return;
  img.style.width = '560px';
  img.style.height = '360px';
  img.onload = function(){
    S.zoom = 1; S.drawing = true; S.mode = '%(mode)s';
    startPt = {x: 300, y: 210};
    band = document.createElement('div');
    band.className = 'band' + ('%(mode)s' === 'erase' ? ' erase' : '');
    document.body.appendChild(band);
    drawBand(startPt, {x: 372, y: 262});
    updateLoupe({clientX: 372, clientY: 262});
  };
  img.src = 'data:image/png;base64,%(png)s';
})();
</script>
""" % {"mode": mode, "png": sample_png()}
    return html.replace("</body>", tail + "</body>")


def shot(html, png, name):
    path = os.path.join(OUT, name + ".html")
    io.open(path, "w", encoding="utf-8").write(html)
    exe = next((p for p in EDGE if os.path.exists(p)), None)
    if not exe:
        print("找不到 Edge/Chrome，跳过截图")
        return None
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1.5",
           "--window-size=1120,760",
           "--virtual-time-budget=4000",
           "--screenshot=" + png,
           "file:///" + path.replace("\\", "/")]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=90)
    return png if os.path.exists(png) else None


if __name__ == "__main__":
    for mode, name in (("draw", "loupe_draw"), ("erase", "loupe_erase")):
        print(shot(build_html(mode), os.path.join(OUT, name + ".png"), name) or ("(%s 未生成)" % name))
