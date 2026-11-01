# -*- coding: utf-8 -*-
"""打包后的 exe：界面接口端到端冒烟测试（open -> render -> 回读）"""
import subprocess, os, re, json, http.client, time, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXE = os.path.join(ROOT, "dist", "PDF隐私打码工具.exe")
SRC = os.path.join(ROOT, "test", "h30", "纯段落_2026.pdf")


def log(*a):
    print(*a, flush=True)


p = subprocess.Popen([EXE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     env=dict(os.environ, PDFMASK_NO_OPEN="1"))
port = None
t0 = time.time()
while time.time() - t0 < 60:
    line = p.stdout.readline()
    if not line:
        break
    s = line.decode("utf-8", "replace")
    m = re.search(r"127\.0\.0\.1:(\d+)", s)
    if m:
        port = int(m.group(1))
        log("服务端口:", port, "|", s.strip())
        break
if not port:
    log("未取到端口，退出")
    p.terminate()
    sys.exit(1)

c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
c.request("GET", "/")
r = c.getresponse()
html = r.read().decode()
c.close()
tok = re.search(r'const TOKEN = "([a-f0-9]+)"', html).group(1)
log("界面 HTML 大小:", len(html))


def post(path, obj):
    cc = http.client.HTTPConnection("127.0.0.1", port, timeout=300)
    cc.request("POST", path, body=json.dumps(obj).encode(),
               headers={"X-Token": tok, "Content-Type": "application/json"})
    rr = cc.getresponse()
    d = rr.read()
    cc.close()
    return rr.status, (json.loads(d.decode()) if d else {})


st, d = post("/api/open", {"path": SRC})
log("open:", st, "| 命中", len(d.get("findings", [])), "项 |", d.get("stats"))
ids = [f["id"] for f in d.get("findings", [])]
st, r2 = post("/api/render", {"doc": d["docId"], "ids": ids})
log("render:", st, "| 打码", r2.get("count"), "| 输出", r2.get("path"))
outp = r2.get("path")
if outp and os.path.exists(outp):
    dd = pymupdf.open(outp)
    t = "".join(pg.get_text() for pg in dd).replace("\n", "").replace(" ", "")
    log("输出页数:", dd.page_count, "| 剩余字数:", len(t))
    log("残留检查: 手机号片段 ->", "13889575552" in t, "| 身份证片段 ->",
        "320106199605166329" in t)
p.terminate()
