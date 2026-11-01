# -*- coding: utf-8 -*-
"""对打包后的 exe 走完整接口流程"""
import http.client
import json
import re
import sys

PORT = int(sys.argv[1])
c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
c.request("GET", "/")
r = c.getresponse()
html = r.read().decode("utf-8")
c.close()
tok = re.search(r'const TOKEN = "([a-f0-9]+)"', html).group(1)
print("页面 OK，token:", tok[:8], "大小:", len(html))
H = {"X-Token": tok, "Content-Type": "application/json"}


def post(p, obj):
    cc = http.client.HTTPConnection("127.0.0.1", PORT, timeout=180)
    cc.request("POST", p, body=json.dumps(obj).encode(), headers=H)
    rr = cc.getresponse()
    d = rr.read()
    cc.close()
    return rr.status, (json.loads(d.decode()) if d else {})


path = r"C:\Users\YB\WorkBuddy\2026-10-31-22-09-25\pdf-privacy-mask\test\测试文档_含隐私.pdf"
st, d = post("/api/open", {"path": path})
print("open:", st, "命中:", len(d.get("findings", [])), d.get("stats"))
ids = [f["id"] for f in d["findings"]]
st, r2 = post("/api/render", {"doc": d["docId"], "ids": ids})
print("render:", st, r2.get("count"), r2.get("path"))

import pymupdf
dd = pymupdf.open(r2["path"])
t = "".join(p.get_text() for p in dd)
print("输出页数:", dd.page_count, "| 手机号泄漏:", "13812346780" in t,
      "| 姓名泄漏:", "陈嘉豪" in t, "| 普通日期保留:", "2026年03月05日" in t.replace(" ", ""))
