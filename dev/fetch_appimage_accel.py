#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 github.akams.cn 的加速节点把 GitHub Release 资产拉回本机（默认拉 AppImage）。

为什么要它：GitHub Release 的裸连下载在本机很慢甚至断流，而 akams 站聚合了
上百个国内可用的 ghproxy 节点。人肉做法是打开网页 → 点「节点测速」→ 挑最快的
→ 浏览器下载。这个脚本把同一件事做完：解析站点里的节点清单 → 自己按同样的
口径测速 → 多节点分段并行拉 → 用 Release 里的 SHA256SUMS 校验。

用法：
    python dev/fetch_appimage_accel.py --tag v1.4.10.0
    python dev/fetch_appimage_accel.py --tag v1.4.10.0 --upload   # 拉完直接传 Gitee
    python dev/fetch_appimage_accel.py --tag v1.4.10.0 --probe-only

设计取舍：
- **每次都重测**。这些是公益节点，随时会下架、限速、恢复：清单每次运行都重抓
  （缓存只在站点抓不到时兜底），速度也每次现测，两轮——先全量 1 MB 粗筛，
  再对前 12 名用 2 MB 复测，避免被握手开销和瞬时拥塞带偏。绝不复用上次结果。
- 不模拟浏览器点按钮。节点清单就写在前端 chunk 里，正则取出来即可；测速口径
  和站点一致（Range 取一小段算 MB/s），结果等价但可复现、可记录。
- 单连接普遍只有 0.1~0.9 MB/s，真正提速靠并发：文件切成 ~4 MB 小块，8 个线程
  抢占式取块，每块轮换节点、最多试 3 个，慢节点只拖累一小块。支持断点续传：
  中断后重跑只补没下完的块。
- 校验是硬门槛：字节数必须等于 GitHub API 报的大小，SHA256 必须等于 Release
  里 SHA256SUMS-linux.txt 的值，任何一个不符就整批作废重下，绝不把坏包传给 Gitee。
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GH_OWNER, GH_REPO = "neurotracee", "pdf-privacy-masker"
AKAMS = "https://github.akams.cn"
CHUNK_URL = AKAMS + "/_next/static/chunks/b76f8fb6e6127b5e.js"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) pdfmask-fetch/1.0"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "dev", ".akams_nodes.json")
SPEED_BYTES = 1024 * 1024  # 测速采样 1 MB（复测用 2 MB）
SPEED_TIMEOUT = 12
CHUNK_BYTES = 4 * 1024 * 1024  # 下载分块大小
MIN_PARTS = 8  # 小文件也至少切 8 块，保证并发
MAX_PARTS = 40  # 上限，避免块太多把请求开销放大
WORKERS = 8  # 同时下载的块数


def log(msg):
    print(msg, flush=True)


def http(url, headers=None, timeout=30, retries=2):
    h = dict(UA)
    if headers:
        h.update(headers)
    last = None
    for i in range(retries + 1):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries:
                time.sleep(1.5 * (i + 1))
    raise last


def gh_token():
    for p in (os.path.expanduser("~/.github_token"),):
        if os.path.exists(p):
            return io.open(p, encoding="utf-8").read().strip()
    return os.environ.get("GITHUB_TOKEN", "").strip()


# ---------- 1. 节点清单 ----------

def load_nodes(use_cache=False):
    """节点清单默认**每次都重抓**。

    这些是公益节点，随时会下架、限速、恢复，昨天的清单今天就可能一半不通；
    缓存只用于「站点抓不到时兜底」，不参与正常路径。
    """
    cached, cached_day = None, "?"
    if os.path.exists(CACHE):
        try:
            d = json.load(io.open(CACHE, encoding="utf-8"))
            cached, cached_day = d.get("nodes") or None, d.get("day", "?")
        except Exception:  # noqa: BLE001
            pass
    if use_cache and cached:
        log("节点清单：按参数使用缓存 %d 个（%s 抓的）" % (len(cached), cached_day))
        return cached
    try:
        log("节点清单：从 %s 重抓（每次运行都重新拉，不用旧清单）" % AKAMS)
        js = http(CHUNK_URL, timeout=40).read().decode("utf-8", "replace")
        seen, nodes = set(), []
        for m in re.finditer(r'value:"([a-z0-9][a-z0-9.\-]{3,60})"', js, re.I):
            d = m.group(1)
            if d in seen or "." not in d or d.endswith(".js") or "akams" in d:
                continue
            seen.add(d)
            nodes.append(d)
        if len(nodes) < 10:
            raise SystemExit("节点清单只解析到 %d 个，站点结构可能变了" % len(nodes))
        json.dump({"ts": time.time(), "day": time.strftime("%Y-%m-%d"), "nodes": nodes},
                  io.open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
        log("节点清单：%d 个" % len(nodes))
        return nodes
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        if cached:
            log("清单抓取失败（%s），回退上次缓存 %d 个（%s 抓的）" % (e, len(cached), cached_day))
            return cached
        raise SystemExit("节点清单抓不到，也没有缓存可用：%s" % e)


def node_url(node, gh_url):
    return "https://%s/%s" % (node, gh_url)


# ---------- 2. 测速 ----------

def probe(node, test_url, sample=SPEED_BYTES):
    """Range 取一段，返回 (node, MB/s, 状态)。口径同站点：bytes / 秒。"""
    path = test_url.split("://", 1)[1]
    t0 = time.time()
    try:
        r = http(node_url(node, path), headers={"Range": "bytes=0-%d" % (sample - 1)},
                 timeout=SPEED_TIMEOUT, retries=0)
        data = r.read(sample)
    except Exception as e:  # noqa: BLE001
        return node, 0.0, type(e).__name__
    dt = max(time.time() - t0, 0.001)
    if len(data) < 4096:
        return node, 0.0, "short"
    return node, len(data) / dt / 1048576.0, "ok"


def run_probe(nodes, test_url, sample, workers):
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(probe, n, test_url, sample) for n in nodes]
        for f in as_completed(futs):
            out.append(f.result())
    return out


def pick_nodes(nodes, test_url, top):
    """两轮测速：先全量粗筛，再对前 12 名加长采样复测。

    公益节点的速度抖动很大，1 MB 采样容易被握手指令和瞬时拥塞带偏；复测一遍
    能把这批节点里真正稳定快的挑出来。两轮都是**本次运行现测**，不复用历史值。
    """
    log("测速第 1 轮：%d 个节点各拉 %d KB …" % (len(nodes), SPEED_BYTES // 1024))
    first = run_probe(nodes, test_url, SPEED_BYTES, 24)
    ok1 = sorted([r for r in first if r[2] == "ok"], key=lambda x: -x[1])
    log("  可用 %d / %d" % (len(ok1), len(first)))
    if not ok1:
        raise SystemExit("所有节点都不通（公益节点可能全挂了，稍后重试或看站点）")

    finalists = [n for n, _, _ in ok1[:12]]
    if len(finalists) > top:
        log("测速第 2 轮：前 %d 名各拉 %d KB 复测 …" % (len(finalists), SPEED_BYTES * 2 // 1024))
        second = run_probe(finalists, test_url, SPEED_BYTES * 2, 12)
        ok = sorted([r for r in second if r[2] == "ok"], key=lambda x: -x[1])
        if len(ok) < top:  # 复测时挂了几个，用第一轮补齐
            have = {n for n, _, _ in ok}
            ok += [r for r in ok1 if r[0] not in have][:top - len(ok)]
            ok.sort(key=lambda x: -x[1])
    else:
        ok = ok1

    for n, s, _ in ok[:10]:
        log("  %7.2f MB/s  %s" % (s, n))
    return [n for n, _, _ in ok[:top]], ok


# ---------- 3. 资产与校验 ----------

def api_bases():
    return ["https://api.github.com"]


def gh_api(path):
    tok = gh_token()
    h = {"Accept": "application/vnd.github+json"}
    if tok:
        h["Authorization"] = "token " + tok
    errors = []
    for base in api_bases():
        try:
            return json.load(http(base + path, headers=h, timeout=40))
        except Exception as e:  # noqa: BLE001
            errors.append("%s: %s" % (base, e))
    raise SystemExit("GitHub API 取不到数据：\n  " + "\n  ".join(errors))


def release_assets(tag):
    d = gh_api("/repos/%s/%s/releases/tags/%s" % (GH_OWNER, GH_REPO, tag))
    return {a["name"]: {"size": a["size"], "url": a["browser_download_url"]}
            for a in d.get("assets", [])}


def fetch_small(nodes, gh_url, limit=2 * 1024 * 1024):
    """小文件（校验和）直接用最快的可用节点拿。"""
    path = gh_url.split("://", 1)[1]
    for n in nodes:
        try:
            data = http(node_url(n, path), timeout=30, retries=0).read(limit)
            if data:
                return data
        except Exception:  # noqa: BLE001
            continue
    raise SystemExit("SHA256SUMS 取不到")


# ---------- 4. 分段并行下载 ----------

def plan_parts(size):
    """切成 ~4 MB 的小段：段越小，慢节点只拖累一小块，整体越抗震。"""
    n = max(MIN_PARTS, min(MAX_PARTS, (size + CHUNK_BYTES - 1) // CHUNK_BYTES))
    step = size // n
    out = []
    for i in range(n):
        a = i * step
        b = size - 1 if i == n - 1 else (i + 1) * step - 1
        out.append((a, b))
    return out


def download_part(node, path, a, b, dest, retries=1):
    need = b - a + 1
    if os.path.exists(dest) and os.path.getsize(dest) == need:
        return "cached"
    got = 0
    for i in range(retries + 1):
        got = 0
        try:
            r = http(node_url(node, path), headers={"Range": "bytes=%d-%d" % (a, b)},
                     timeout=60, retries=0)
            with io.open(dest, "wb") as f:
                while True:
                    chunk = r.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
            if got == need:
                return "ok"
        except Exception:  # noqa: BLE001
            pass
        if i < retries:
            try:
                os.remove(dest)
            except OSError:
                pass
            time.sleep(0.8)
    return "fail(%s)" % got


def download(nodes, gh_url, size, out_path):
    """抢占式分块：谁空谁接下一块，每块换一个节点，失败自动降级到下一个。

    固定「一块绑一个节点」的写法会被一两个抽风的节点拖死；这里把块做小、
    动态派发，再给每块最多 3 个候选节点，慢的拖不动整体。
    """
    path = gh_url.split("://", 1)[1]
    parts = plan_parts(size)
    tmpdir = out_path + ".parts"
    os.makedirs(tmpdir, exist_ok=True)
    log("下载 %s：%.1f MB，%d 块 × %d 节点（每块最多试 3 个节点）" %
        (os.path.basename(out_path), size / 1048576.0, len(parts), len(nodes)))
    t0 = time.time()
    todo = list(range(len(parts)))
    lock = threading.Lock()
    state = {"ok": 0, "bad": [], "next_report": 1}

    def take():
        with lock:
            return todo.pop(0) if todo else None

    def worker(slot):
        turn = slot
        while True:
            i = take()
            if i is None:
                return
            a, b = parts[i]
            dest = os.path.join(tmpdir, "p%03d" % i)
            good = False
            for attempt in range(min(3, len(nodes))):
                node = nodes[(turn + attempt) % len(nodes)]
                st = download_part(node, path, a, b, dest)
                if not st.startswith("fail"):
                    good = True
                    break
            turn += 1
            with lock:
                if good:
                    state["ok"] += 1
                    done, bad = state["ok"], len(state["bad"])
                else:
                    state["bad"].append(i)
                    done, bad = state["ok"], len(state["bad"])
                pct = done * 100 // len(parts)
                show = pct >= state["next_report"] * 10
                if show:
                    state["next_report"] = pct // 10 + 1
            if show:
                el = max(time.time() - t0, 0.01)
                log("  进度 %d/%d 块（%d%%）  失败 %d  平均 %.2f MB/s" %
                    (done, len(parts), pct, bad, size * (done / len(parts)) / el / 1048576.0))

    threads = [threading.Thread(target=worker, args=(s,), daemon=True) for s in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 还有失败的块：逐个用所有节点再试一遍
    if state["bad"]:
        log("补下 %d 个失败块 …" % len(state["bad"]))
        for i in state["bad"]:
            a, b = parts[i]
            dest = os.path.join(tmpdir, "p%03d" % i)
            for node in nodes:
                st = download_part(node, path, a, b, dest)
                if not st.startswith("fail"):
                    break

    buf = io.BytesIO()
    for i in range(len(parts)):
        p = os.path.join(tmpdir, "p%03d" % i)
        if not os.path.exists(p):
            raise SystemExit("第 %d 块缺失，重跑本脚本会续传" % i)
        buf.write(io.open(p, "rb").read())
    data = buf.getvalue()
    if len(data) != size:
        raise SystemExit("合并后大小不符：%d != %d（重跑会重新校验）" % (len(data), size))
    with io.open(out_path, "wb") as f:
        f.write(data)
    for i in range(len(parts)):
        try:
            os.remove(os.path.join(tmpdir, "p%03d" % i))
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass
    dt = time.time() - t0
    log("完成：%.1f MB / %.1f 秒 = %.2f MB/s" %
        (size / 1048576.0, dt, size / 1048576.0 / max(dt, 0.001)))
    return out_path


def sha256_of(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--asset", default=None, help="只拉某个文件名（默认 .AppImage）")
    ap.add_argument("--nodes", type=int, default=4, help="测速后取前几个节点参与分段")
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--use-cache", action="store_true",
                    help="直接用上次缓存的节点清单（默认每次都重抓）")
    ap.add_argument("--wait-ci", type=int, default=0,
                    help="等 CI 把 AppImage 挂到该 Release 的最长分钟数（0 = 不等）")
    ap.add_argument("--upload", action="store_true", help="拉完直接传 Gitee（复用 push_appimage_gitee.py）")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "appimage"))
    a = ap.parse_args()

    if a.wait_ci:
        deadline = time.time() + a.wait_ci * 60
        while True:
            if any(n.lower().endswith(".appimage") for n in release_assets(a.tag)):
                break
            if time.time() >= deadline:
                raise SystemExit("等了 %d 分钟，%s 的 Release 里仍没有 AppImage（去 Actions 看那次构建）"
                                 % (a.wait_ci, a.tag))
            log("等 CI 构建并挂上 AppImage …（还剩 %d 分钟）" %
                max(0, int((deadline - time.time()) / 60)))
            time.sleep(20)

    assets = release_assets(a.tag)
    want = a.asset or next((n for n in assets if n.lower().endswith(".appimage")), None)
    if not want or want not in assets:
        raise SystemExit("这个 tag 没有 %s，现有：%s" % (a.asset or ".AppImage", ", ".join(assets)))
    info = assets[want]
    log("目标：%s  %d 字节" % (want, info["size"]))

    nodes = load_nodes(a.use_cache)
    test_url = info["url"]
    best, ranked = pick_nodes(nodes, test_url, a.nodes)
    if a.probe_only:
        return 0

    os.makedirs(a.out, exist_ok=True)
    out_path = os.path.join(a.out, want)

    # 先用最快节点取校验和，确定期望 SHA（优先 linux 那份，里面有 AppImage 的行）
    expect_sha = None
    sums_name = (next((n for n in assets if n.lower().startswith("sha256sums-linux")), None)
                 or next((n for n in assets if n.lower().startswith("sha256sums")), None))
    body = None
    if sums_name:
        try:
            body = fetch_small(best, assets[sums_name]["url"]).decode("utf-8", "replace")
            for line in body.splitlines():
                bits = line.split()
                if len(bits) >= 2 and os.path.basename(bits[-1].lstrip("*")) == want:
                    expect_sha = bits[0].lower()
                    break
            if not expect_sha:
                log("提示：%s 里没有 %s 的行" % (sums_name, want))
        except SystemExit:
            log("提示：取不到 %s，本次只按字节数校验" % sums_name)
    log("期望 SHA256：%s" % (expect_sha or "（Release 未提供，只校验字节数）"))

    def verified(path):
        if os.path.getsize(path) != info["size"]:
            return False
        if not expect_sha:
            return True
        return sha256_of(path) == expect_sha

    if os.path.exists(out_path) and verified(out_path):
        log("本地已有同尺寸文件且校验通过，跳过下载：%s" % out_path)
    elif os.path.exists(out_path):
        log("本地文件校验不符，重新下载")
        try:
            os.remove(out_path)
        except OSError:
            pass

    if not os.path.exists(out_path):
        download(best, info["url"], info["size"], out_path)
        got = sha256_of(out_path)
        if expect_sha:
            if got != expect_sha:
                log("SHA256 不符！got=%s want=%s" % (got, expect_sha))
                try:
                    os.remove(out_path)
                except OSError:
                    pass
                raise SystemExit("校验失败：下载的包与 Release 的校验和不一致，已删除，请重跑")
            log("SHA256 校验通过：%s" % got)
        else:
            log("字节数校验通过：%d 与 GitHub 一致（Release 未提供 SHA，未做内容比对）" % info["size"])

    log("产物：%s" % out_path)

    if a.upload:
        tok = os.path.join(os.path.expanduser("~"), ".gitee_token")
        if not os.path.exists(tok):
            raise SystemExit("没有 ~/.gitee_token，无法上传")
        os.environ["GITEE_TOKEN"] = io.open(tok, encoding="utf-8").read().strip()
        files = [out_path]
        if body and sums_name:
            sp = os.path.join(a.out, sums_name)
            io.open(sp, "w", encoding="utf-8", newline="\n").write(body)
            files.append(sp)
        cmd = [sys.executable, os.path.join(ROOT, "dev", "push_appimage_gitee.py"), a.tag] + files
        log("上传 Gitee：%s" % ", ".join(os.path.basename(c) for c in files))
        import subprocess
        return subprocess.call(cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
