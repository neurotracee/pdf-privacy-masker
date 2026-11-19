"""把 README.md 渲染成一张长图，用来检查排版（不参与发版）。

GitHub 的 <picture> 会按系统深浅色切换，无头浏览器不方便模拟，
所以这里按 --theme 把 <picture> 直接展开成对应那一张 <img>。
"""
import os
import re
import subprocess
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

CSS = """
body{margin:0;padding:32px;background:%(bg)s;color:%(fg)s;
     font:16px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}
.markdown-body{max-width:900px;margin:0 auto;}
h3{font-size:1.35em;margin:1.6em 0 .5em;}
h2{font-size:1.6em;border-bottom:1px solid %(border)s;padding-bottom:.3em;margin-top:2em;}
h1{font-size:2em;}
img{max-width:100%%;box-sizing:border-box;background:%(bg)s;}
p{margin:.6em 0;}
blockquote{margin:1em 0;padding:.2em 1em;color:%(muted)s;border-left:.25em solid %(border)s;}
hr{height:1px;border:0;background:%(border)s;margin:2em 0;}
sub{color:%(muted)s;}
a{color:#2563EB;}
"""

THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", border="#d8dee4", muted="#59636e"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", border="#30363d", muted="#9198a1"),
}


def _abs(src):
    if not src or "://" in src:
        return src
    return "file:///" + os.path.join(ROOT, src).replace("\\", "/")


def flatten_pictures(html, theme):
    def repl(m):
        block = m.group(0)
        dark = re.search(r'srcset="([^"]+)"', block)
        light = re.search(r'<img src="([^"]+)"', block)
        alt = re.search(r'alt="([^"]*)"', block)
        src = (dark.group(1) if theme == "dark" and dark else
               (light.group(1) if light else ""))
        return '<img src="%s" alt="%s" width="100%%">' % (
            _abs(src), alt.group(1) if alt else "")
    html = re.sub(r"<picture>.*?</picture>", repl, html, flags=re.S)
    # 其余普通 <img> 的相对路径也要改成绝对路径，否则预览页面里全是裂图
    return re.sub(r'<img([^>]*?)src="(?!https?:|file:)([^"]+)"',
                  lambda m: '<img%s src="%s"' % (m.group(1), _abs(m.group(2))), html)


def main():
    theme = "light"
    if "--theme" in sys.argv:
        theme = sys.argv[sys.argv.index("--theme") + 1]
    h = 2600
    if "--height" in sys.argv:
        h = int(sys.argv[sys.argv.index("--height") + 1])
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        src = fh.read()
    body = markdown.markdown(src, extensions=["tables", "fenced_code", "nl2br"])
    body = flatten_pictures(body, theme)
    page = ("<!doctype html><meta charset='utf-8'><style>%s</style>"
            "<div class='markdown-body'>%s</div>"
            % (CSS % THEMES[theme], body))
    out = os.path.join(ROOT, "dev", "_ui", "readme-%s.html" % theme)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)

    png = os.path.join(ROOT, "dev", "_ui", "readme-%s-%d.png" % (theme, h))
    exe = next(e for e in EDGE if os.path.exists(e))
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--no-first-run", "--force-color-profile=srgb",
                    "--user-data-dir=" + os.path.join(os.environ.get("TEMP", "."), "edge-readme"),
                    "--virtual-time-budget=8000",
                    "--window-size=1000,%d" % h,
                    "--screenshot=" + png, "file:///" + out.replace("\\", "/")],
                   capture_output=True, timeout=180)
    print(png)


if __name__ == "__main__":
    main()
