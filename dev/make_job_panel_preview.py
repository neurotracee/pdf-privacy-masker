# -*- coding: utf-8 -*-
"""把「处理进度面板」单独渲染成一张图，用来肉眼核对版式。

做法：直接拿 pdfmask 里那份 HTML_UI（就是程序真正在浏览器里跑的那一页），
把服务端占位符填掉，再在末尾追加一小段脚本：先把面板打开，然后喂一组假数据。
不需要启动服务、也不需要真的识别一份 PDF。

    python dev/make_job_panel_preview.py            # 生成两张图（进行中 / 已暂停）
"""
import io
import json
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


def build_html(running=True):
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
    fake = {
        "active": True,
        "paused": not running,
        "kind": "scan",
        "title": "正在识别扫描页",
        "titleEn": "Reading scanned pages",
        "note": "扫描页",
        "page": 4,
        "pages": 12,
        "pageFrac": 0.62,
        "overall": 0.2833,
    }
    # 用真面板 + 假数据：jobShow 起个壳，paintJob 填数。
    # 轮询会失败（file:// 下没有服务端），正好停在那里不动。
    tail = """
<script>
  jobShow(T('正在识别敏感信息…','Scanning for sensitive data…'));
  clearTimeout(JOB_TIMER);
  paintJob(%s);
</script>
""" % json.dumps(fake, ensure_ascii=False)
    return html.replace("</body>", tail + "</body>")


def shot(html, png):
    path = os.path.join(OUT, "job_panel.html")
    io.open(path, "w", encoding="utf-8").write(html)
    exe = next((p for p in EDGE if os.path.exists(p)), None)
    if not exe:
        print("找不到 Edge/Chrome，跳过截图")
        return None
    cmd = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=1.5",
           "--window-size=1120,760",
           "--screenshot=" + png,
           "file:///" + path.replace("\\", "/")]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=90)
    return png if os.path.exists(png) else None


if __name__ == "__main__":
    a = shot(build_html(True), os.path.join(OUT, "job_running.png"))
    b = shot(build_html(False), os.path.join(OUT, "job_paused.png"))
    print(a or "(running 未生成)")
    print(b or "(paused 未生成)")
