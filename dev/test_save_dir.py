# -*- coding: utf-8 -*-
"""自测：保存位置相关接口（settings / render 指定目录 / 写入配置文件）。

把配置目录指到临时位置，避免污染真实用户设置。
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pdfmask  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(ROOT), "PDF隐私打码工具", "测试样例",
                      "样例_纯段落多人多页_未打码.pdf")

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  ✓ " if cond else "  ✗ ") + name + ("" if cond else "  <<< " + str(extra)))


def main():
    tmp = tempfile.mkdtemp(prefix="pdfmask_test_")
    cfgdir = os.path.join(tmp, "cfg")
    srcdir = os.path.join(tmp, "src")
    out1 = os.path.join(tmp, "out1")
    out2 = os.path.join(tmp, "out2")
    for d in (srcdir, out1):
        os.makedirs(d, exist_ok=True)

    # 隔离设置文件
    pdfmask.SETTINGS_DIR = cfgdir
    pdfmask.SETTINGS_PATH = os.path.join(cfgdir, "settings.json")
    pdfmask.SETTINGS.update(pdfmask.DEFAULT_SETTINGS)

    if not os.path.exists(SAMPLE):
        print("找不到样例 PDF：", SAMPLE)
        return 1
    src = os.path.join(srcdir, "测试文档.pdf")
    shutil.copy(SAMPLE, src)

    srv = pdfmask.QuietServer(("127.0.0.1", 0), pdfmask.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def call(path, payload=None):
        url = "http://127.0.0.1:%d%s" % (port, path)
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data,
                                     method="POST" if data is not None else "GET")
        req.add_header("X-Token", pdfmask.SERVE_TOKEN)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8")), None
        except urllib.error.HTTPError as e:
            return None, json.loads(e.read().decode("utf-8")).get("error", "http %d" % e.code)

    print("1) 初始设置")
    s, err = call("/api/settings")
    check("GET /api/settings 可用", s is not None, err)
    check("默认不弹窗开关为关（noAsk=False）", s and s["noAsk"] is False, s)
    check("默认目录已解析出来", s and os.path.isdir(s["defaultDir"]), s)
    check("未配置时不显示已配置", s and s["configured"] is False, s)

    print("2) 打开文档")
    d, err = call("/api/open", {"path": src})
    check("打开样例 PDF", d is not None, err)
    check("payload 带 outDir（源目录）", d and d.get("outDir") == srcdir, d and d.get("outDir"))
    ids = [f["id"] for f in d["findings"]][:5]
    check("识别出可打码条目", len(ids) >= 3, ids)

    print("3) 指定目录生成")
    r, err = call("/api/render", {"doc": d["docId"], "ids": ids,
                                  "dir": out1, "remember": True, "noAsk": False})
    ok = r is not None
    check("render 成功", ok, err)
    check("文件落在指定目录", ok and os.path.dirname(r["path"]) == out1, r and r["path"])
    check("文件真实存在", ok and os.path.isfile(r["path"]), r and r["path"])
    check("返回 dir 字段", ok and r.get("dir") == out1, r and r.get("dir"))

    print("4) 勾选「下次默认此路径」后写入设置")
    s2, _ = call("/api/settings?doc=" + d["docId"])
    check("saveDir 已记住", s2 and s2["saveDir"] == out1, s2)
    check("rememberDir=True", s2 and s2["rememberDir"] is True, s2)
    check("noAsk 仍为 False（没勾不再询问）", s2 and s2["noAsk"] is False, s2)
    check("配置文件已落盘", os.path.isfile(pdfmask.SETTINGS_PATH))

    print("5) 设置面板改路径 + 不再询问")
    s3, err = call("/api/settings", {"saveDir": out2, "noAsk": True})
    check("POST /api/settings 成功", s3 is not None, err)
    s4, _ = call("/api/settings")
    check("新路径生效", s4 and s4["saveDir"] == out2, s4)
    check("noAsk=True", s4 and s4["noAsk"] is True, s4)
    check("effectiveDir = 新路径", s4 and s4["effectiveDir"] == out2, s4)

    print("6) 目录不存在时自动创建")
    out3 = os.path.join(tmp, "自动创建", "深层目录")
    r2, err = call("/api/render", {"doc": d["docId"], "ids": ids, "dir": out3,
                                   "remember": True, "noAsk": True})
    check("自动建目录并保存", r2 is not None and os.path.isfile(r2["path"]), err)
    check("目录已创建", os.path.isdir(out3))

    print("7) 路径非法时报错")
    bad = os.path.join(srcdir, "测试文档.pdf")   # 指向一个文件
    r3, err = call("/api/render", {"doc": d["docId"], "ids": ids, "dir": bad})
    check("指向文件时拒绝", r3 is None and "文件" in (err or ""), err)
    r4, err = call("/api/render", {"doc": d["docId"], "ids": ids, "dir": ""})
    check("空目录时回落到源目录", r4 is not None and os.path.dirname(r4["path"]) == srcdir,
          (err, r4 and r4.get("path")))

    print("8) 设置持久化（重新读取）")
    reloaded = pdfmask._load_settings()
    check("重读配置一致", reloaded["saveDir"] == out3 and reloaded["noAsk"] is True, reloaded)

    print("9) 同名文件不覆盖")
    r5, _ = call("/api/render", {"doc": d["docId"], "ids": ids, "dir": out1})
    r6, _ = call("/api/render", {"doc": d["docId"], "ids": ids, "dir": out1})
    check("第二次自动改名", r5 and r6 and r5["path"] != r6["path"],
          (r5 and r5["name"], r6 and r6["name"]))

    print("10) 另存到别处")
    out4 = os.path.join(tmp, "另存目录")
    cp, cerr = call("/api/copyout", {"token": r6["token"], "dir": out4})
    check("另存成功", cp and os.path.isfile(cp.get("path", "")), cerr)
    check("另存到新目录", cp and os.path.dirname(cp["path"]) == out4, cp)
    cp2, cerr2 = call("/api/copyout", {"token": r6["token"], "dir": out4})
    check("重复另存不覆盖", cp2 and cp2["path"] != cp["path"], (cp, cerr2, cp2))
    _bad, bad = call("/api/copyout", {"token": "nope", "dir": out4})
    check("无效 token 被拒绝", isinstance(bad, str) and bool(bad), bad)

    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    print("\n通过 %d 项，失败 %d 项" % (len(PASS), len(FAIL)))
    if FAIL:
        print("失败：", FAIL)
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
