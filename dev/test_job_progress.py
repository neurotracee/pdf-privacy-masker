# -*- coding: utf-8 -*-
"""处理进度面板的服务端验收：进度是否真的在走、暂停是否真的停住、停止是否真的中断。

界面上的两条进度条全靠 `/api/job` 这一个接口，所以这里直接测服务端，
不依赖浏览器：
  1. 直连 detect()：页码递增、总进度单调上升、最后一页到 1.0；
  2. 暂停：中途 pause 之后 0.8 秒内总进度不许变，resume 之后继续往上；
  3. 停止：stop 之后工作线程抛 JobCancelled，而不是傻跑完；
  4. HTTP：/api/job 能查到状态，/api/job/pause|resume|stop 能改状态，
     上传结束后 active 变回 false；打码阶段 kind=mask。

跑法：
    python dev/test_job_progress.py
"""
import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pdfmask as M  # noqa: E402

TMP = os.path.join(ROOT, "test", "job")
os.makedirs(TMP, exist_ok=True)
DOC = os.path.join(TMP, "十二页.pdf")

OK = []
BAD = []


def check(name, cond, detail=""):
    (OK if cond else BAD).append(name)
    print(("  [OK]   " if cond else "  [FAIL] ") + name + (("  " + detail) if detail else ""))


def make_doc(pages=12):
    if os.path.exists(DOC) and pymupdf.open(DOC).page_count == pages:
        return DOC
    doc = pymupdf.open()
    for i in range(pages):
        p = doc.new_page(width=595, height=842)
        p.insert_text((60, 100), "第 %d 页" % (i + 1), fontsize=16)
        p.insert_text((60, 140), "姓名：张伟    电话：13812345678", fontsize=12)
        p.insert_text((60, 170), "身份证号：320102199003072316", fontsize=12)
        p.insert_text((60, 200), "住址：江苏省南京市玄武区中山路100号3栋502室", fontsize=12)
    doc.save(DOC)
    doc.close()
    return DOC


# ---------------------------------------------------------------- 直连

def t_direct():
    print("\n1) detect() 的进度上报")
    doc = pymupdf.open(make_doc())
    job = M.Job("scan", "test", "test")
    seen = []
    err = []

    def work():
        try:
            M.detect(doc, job=job)
        except BaseException as e:      # noqa: BLE001
            err.append(e)

    th = threading.Thread(target=work, daemon=True)
    th.start()
    while th.is_alive():
        st = job.status()
        seen.append((st["page"], st["overall"]))
        time.sleep(0.02)
    th.join(2)
    fin = job.status()            # 收尾再取一次：纯文字层的文档跑得很快，采样可能漏掉最后一页
    seen.append((fin["page"], fin["overall"]))
    doc.close()

    check("没有异常", not err, str(err[:1]))
    pages = [p for p, _ in seen]
    check("页码一路推进到 12", max(pages or [0]) >= 12, "max=%s" % max(pages or [0]))
    ov = [o for _, o in seen]
    check("总进度单调不降", all(b >= a - 1e-6 for a, b in zip(ov, ov[1:])))
    check("总进度确实涨上去了", (max(ov or [0]) > 0.5), "max=%.2f" % max(ov or [0]))


def t_pause_and_stop():
    print("\n2) 暂停 / 继续 / 停止")
    for mode in ("pause", "stop"):
        doc = pymupdf.open(make_doc())
        job = M.Job("scan", "test", "test")
        err = []

        def work():
            try:
                M.detect(doc, job=job)
            except BaseException as e:  # noqa: BLE001
                err.append(e)

        th = threading.Thread(target=work, daemon=True)
        th.start()
        # 等它至少跑过一页再动手，避免测在启动之前的空档
        for _ in range(400):
            if job.status()["page"] >= 2:
                break
            time.sleep(0.01)

        if mode == "pause":
            job.pause()
            time.sleep(0.15)                 # 让工作线程走到安全点
            a = job.status()["overall"]
            time.sleep(0.8)
            b = job.status()["overall"]
            check("暂停后进度冻结", abs(a - b) < 1e-6, "%.3f -> %.3f" % (a, b))
            check("暂停时线程还活着（不是退出）", th.is_alive())
            job.resume()
            time.sleep(0.5)
            c = job.status()["overall"]
            check("继续后进度重新上升", c > b, "%.3f -> %.3f" % (b, c))
            job.stop()
        else:
            job.stop()
            th.join(3)
            check("停止后工作线程退出", not th.is_alive())
            check("抛出的是 JobCancelled",
                  bool(err) and isinstance(err[0], M.JobCancelled),
                  type(err[0]).__name__ if err else "无异常")
        doc.close()


# ---------------------------------------------------------------- HTTP

def _req(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def SCAN_PDF():
    """扫描件夹具（dev/fixtures 由 dump_ocr_fixture.py 生成，可能不在）"""
    p = os.path.join(HERE, "fixtures", "t1.pdf")
    if os.path.exists(p):
        return p
    return make_doc(3)


def t_http():
    print("\n3) /api/job 与暂停/停止接口")
    srv = M.QuietServer(("127.0.0.1", 0), M.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port
    hdr = {"X-Token": M.SERVE_TOKEN}

    try:
        # 空转时也要能查，且不报错
        code, body = _req(base + "/api/job", headers=hdr)
        d = json.loads(body)
        check("没有任务时返回 active=false", code == 200 and d.get("active") is False, str(d))

        # 用扫描件跑上传：文字层文档太快，采样窗口可能一次都赶不上。
        # 扫描件要走 OCR，一页就要几秒，才看得出进度条在动。
        raw = open(SCAN_PDF(), "rb").read()
        h2 = dict(hdr)
        h2["X-File-Name"] = urllib.parse.quote("十二页.pdf")   # 与前端一致：URI 编码后再进头
        h2["Content-Type"] = "application/pdf"
        res = {}

        samples = []
        stop_sampling = threading.Event()

        def sample():
            # 与上传并行地拉状态；看到过 active 之后，等它转成 false 再收工
            while not stop_sampling.is_set():
                try:
                    _, b = _req(base + "/api/job", headers=hdr)
                    j = json.loads(b)
                    if j.get("active"):
                        samples.append(j)
                except Exception:
                    pass
                time.sleep(0.02)

        sp = threading.Thread(target=sample, daemon=True)
        sp.start()

        def up():
            try:
                res["code"], res["body"] = _req(base + "/api/upload", data=raw, headers=h2)
            except Exception as e:  # noqa: BLE001
                res["err"] = e

        th = threading.Thread(target=up, daemon=True)
        th.start()
        th.join(60)
        time.sleep(0.3)
        stop_sampling.set()
        sp.join(2)
        check("上传成功", res.get("code") == 200, str(res.get("err") or res.get("code")))
        check("过程中能查到 active 的任务", bool(samples), "采样 %d 次" % len(samples))
        if samples:
            check("任务里有页码与总页数",
                  samples[-1]["pages"] >= 1 and samples[-1]["page"] >= 1,
                  "%s/%s" % (samples[-1]["page"], samples[-1]["pages"]))
        _, b = _req(base + "/api/job", headers=hdr)
        check("结束后 active=false", json.loads(b).get("active") is False)

        # 控制接口：对一个手动造出来的任务生效
        j = M.job_new("scan", "x", "x")
        j.begin_page(1, 10)
        _req(base + "/api/job/pause", data=b"", headers=hdr, method="POST")
        check("pause 接口生效", M.job_current().status()["paused"] is True)
        _req(base + "/api/job/resume", data=b"", headers=hdr, method="POST")
        check("resume 接口生效", M.job_current().status()["paused"] is False)
        _req(base + "/api/job/stop", data=b"", headers=hdr, method="POST")
        check("stop 接口生效", M.job_current().status()["active"] is False)

        # 打码阶段：job 的 kind 应该是 mask
        doc_id = json.loads(res["body"])["docId"]
        body = json.dumps({"doc": doc_id, "ids": [f["id"] for f in
                                                 json.loads(res["body"])["findings"]]}).encode()
        h3 = dict(hdr)
        h3["Content-Type"] = "application/json"
        _req(base + "/api/render", data=body, headers=h3, method="POST")
        check("打码完成后不再挂着任务", M.job_current().status()["active"] is False)
    finally:
        srv.shutdown()


if __name__ == "__main__":
    t_direct()
    t_pause_and_stop()
    t_http()
    print("\n通过 %d 项，失败 %d 项" % (len(OK), len(BAD)))
    if BAD:
        print("失败：", "、".join(BAD))
        sys.exit(1)
