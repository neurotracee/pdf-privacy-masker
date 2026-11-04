# -*- coding: utf-8 -*-
"""打包后的 exe：界面接口端到端冒烟测试（open -> render -> 回读）

注意：exe 是窗口版（console=False），运行时拿不到它的 stdout，
所以端口靠「启动前后对比本机新增的 LISTENING 端口」来找，别再指望 readline。
"""
import subprocess, os, re, json, http.client, time, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EXE = os.path.join(ROOT, "dist", "PDF隐私打码工具.exe")
SRC = os.path.join(ROOT, "test", "刁难文档30_纯段落.pdf")


def log(*a):
    print(*a, flush=True)


def listen_ports(host_ok=("127.0.0.1", "0.0.0.0")):
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                         text=True, errors="replace").stdout
    ports = set()
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        m = re.match(r"\s*TCP\s+(\S+):(\d+)\s", line)
        if m and m.group(1) in host_ok:
            ports.add(int(m.group(2)))
    return ports


if not os.path.exists(EXE):
    log("找不到 exe:", EXE)
    sys.exit(1)

before = listen_ports()
p = subprocess.Popen([EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     env=dict(os.environ, PDFMASK_NO_OPEN="1"))
port = None
for _ in range(40):
    time.sleep(1.0)
    if p.poll() is not None:
        log("exe 启动后立即退出，退出码:", p.returncode)
        sys.exit(1)
    new = listen_ports() - before
    if new:
        port = max(new)
        break
if not port:
    log("未取到端口，退出")
    p.terminate()
    sys.exit(1)
log("服务端口:", port)

c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
c.request("GET", "/")
r = c.getresponse()
html = r.read().decode()
c.close()
tok = re.search(r'const TOKEN = "([a-f0-9]+)"', html).group(1)
log("界面 HTML 大小:", len(html))
log("含『保存赞赏码』:", "保存赞赏码" in html)


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
