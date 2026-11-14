# -*- coding: utf-8 -*-
"""对打包后的 exe 验证「保存位置」相关功能（含原生对话框）。

用法：python dev/test_exe_save.py <端口>
"""
import ctypes
import http.client
import json
import os
import re
import sys
import tempfile
import threading
import time

PORT = int(sys.argv[1])
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "test", "刁难文档30_纯段落.pdf")
with open(os.path.join(ROOT, "pdfmask.py"), encoding="utf-8") as _f:
    EXPECT_VER = re.search(r'^VERSION = "([^"]+)"', _f.read(), re.M).group(1)
user32 = ctypes.windll.user32
PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✓ " if cond else "  ✗ ") + name + ("" if cond else "  <<< " + str(extra)))


def get(path):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    c.request("GET", path, headers={"X-Token": TOK})
    r = c.getresponse()
    d = r.read()
    c.close()
    return json.loads(d.decode("utf-8"))


def post(path, obj, timeout=300):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    c.request("POST", path, body=json.dumps(obj).encode(),
              headers={"X-Token": TOK, "Content-Type": "application/json"})
    r = c.getresponse()
    d = r.read()
    c.close()
    return r.status, (json.loads(d.decode("utf-8")) if d else {})


c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
c.request("GET", "/")
html = c.getresponse().read().decode("utf-8")
c.close()
TOK = re.search(r'const TOKEN = "([a-f0-9]+)"', html).group(1)
print("页面加载 OK，token:", TOK[:8])
check("exe 页面可访问", len(html) > 10000, len(html))
check("界面版本与 pdfmask.VERSION 一致", EXPECT_VER in html,
      (EXPECT_VER, re.findall(r"版本 (\S+)", html)))
check("首页徽章标着「支持扫描件」",
      "支持扫描件" in html and "不支持扫描件" not in html)
check("界面含「设置」入口", 'id="setBtn"' in html)
check("界面含保存位置弹窗", 'id="saveMask"' in html)

tmp = tempfile.mkdtemp(prefix="exe_save_")
out = os.path.join(tmp, "指定输出")
os.makedirs(out, exist_ok=True)

st, d = post("/api/open", {"path": SAMPLE})
check("打开 PDF 成功", st == 200 and d.get("findings"), d.get("error"))
ids = [f["id"] for f in d.get("findings", [])][:20]

s = get("/api/settings?doc=" + d.get("docId", ""))
check("读取设置成功", "noAsk" in s, s)

st, r = post("/api/render", {"doc": d["docId"], "ids": ids, "dir": out,
                             "remember": True, "noAsk": False})
check("指定目录生成成功", st == 200 and os.path.isfile(r.get("path", "")), r.get("error"))
check("文件落在指定目录", os.path.dirname(r.get("path", "")) == out, r.get("path"))

s2 = get("/api/settings")
check("勾选「下次默认」后已记住路径", s2.get("saveDir") == out, s2.get("saveDir"))
check("noAsk 仍为 False", s2.get("noAsk") is False, s2)

st, s3 = post("/api/settings", {"saveDir": tmp, "noAsk": True})
check("设置面板保存成功", st == 200 and s3.get("settings", {}).get("noAsk") is True, s3)

# --- 原生「选择文件夹」对话框（打包后最容易出问题的地方）---
print("\n调用系统原生选择框（2 秒后自动关闭）…")
box = {"resp": None, "done": False}


def ask():
    try:
        box["resp"] = post("/api/pickdir", {"initial": tmp}, timeout=120)
    except Exception as e:      # noqa: BLE001
        box["resp"] = ("EXC", str(e))
    box["done"] = True


th = threading.Thread(target=ask, daemon=True)
th.start()

hwnd = None
for _ in range(40):
    time.sleep(0.25)
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(128)
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, cls, 64)
        user32.GetWindowTextW(h, buf, 128)
        if cls.value == "#32770" and user32.IsWindowVisible(h) and "保存位置" in buf.value:
            found.append(h)
        return True

    user32.EnumWindows(cb, None)
    if found:
        hwnd = found[0]
        break
    if box["done"]:
        break

check("打包后仍能弹出系统选择框", hwnd is not None, box["resp"])
if hwnd:
    time.sleep(0.4)
    user32.PostMessageW(ctypes.c_void_p(hwnd), 0x0010, 0, 0)   # WM_CLOSE
th.join(timeout=20)
check("关闭后接口正常返回", box["done"], box)
resp = box["resp"] or (None, {})
body = resp[1] if isinstance(resp, tuple) and isinstance(resp[1], dict) else {}
check("取消时返回 cancel", body.get("status") == "cancel", resp)

print("\n通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
if FAIL:
    print("失败：", FAIL)
sys.exit(0 if not FAIL else 1)
