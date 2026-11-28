#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 `.agent/STATE.md`：接手的人第一眼看的那张「事实快照」。

为什么要有它
------------
会话之间、平台之间，Agent 最容易翻车的不是不会写代码，而是**版本/分支/发版
状态记错了**——比如以为还没发版、以为改了版本号就生效了。这张表全部由仓库
自己算出来，不靠谁手写，所以永远不会「写着写着就过期」。

用法（三端通用，只用标准库，不联网）：
    python dev/agent_state.py            # 刷新 .agent/STATE.md
    python dev/agent_state.py --print     # 只打印到终端，不写文件

约定：这个文件是**生成物**，不要手改；要补信息写 `.agent/CONTEXT.md`
或 `.agent/HANDOVER.md`。
"""
import io
import os
import re
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, ".agent", "STATE.md")


def _read(path):
    try:
        with io.open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _git(*args):
    """跑一条 git 命令；没有 git（比如只有 PortableGit）就返回 None。"""
    try:
        r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _count_files(exts, subdir=""):
    base = os.path.join(ROOT, subdir) if subdir else ROOT
    n = 0
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "build", "dist", "__pycache__", "node_modules",
                                    ".gradle", "_ui", "release")]
        n += sum(1 for f in filenames if f.endswith(exts))
    return n


def collect():
    facts = {}

    py_ver = re.search(r'^VERSION\s*=\s*"([^"]+)"', _read("pdfmask.py"), re.M)
    facts["py"] = py_ver.group(1) if py_ver else "（没读到）"

    gr = re.search(r'appVersionName\s*=\s*"([^"]+)"', _read("android/app/build.gradle.kts"))
    facts["android"] = gr.group(1) if gr else "（没读到）"

    vi = _read("version_info.txt")
    fixed = re.search(r"filevers=\(([^)]*)\)", vi)
    string = re.search(r"'FileVersion',\s*'([^']+)'", vi)
    facts["vi_fixed"] = ("(" + fixed.group(1).replace(" ", "") + ")") if fixed else "（没读到）"
    facts["vi_string"] = string.group(1) if string else "（没读到）"

    # 三处一致才敢说「版本对齐」
    fixed_nums = re.findall(r"\d+", fixed.group(1)) if fixed else []
    aligned = (facts["py"] == facts["android"] == facts["vi_string"]
               and ".".join(fixed_nums + ["0"] * 4)[:len(facts["py"])] == facts["py"])
    facts["aligned"] = aligned

    facts["tag"] = _git("describe", "--tags", "--abbrev=0") or "（读不到 tag）"
    facts["commits"] = (_git("log", "-5", "--date=short",
                             "--pretty=format:%h  %ad  %s") or "").splitlines()
    status = _git("status", "--porcelain")
    facts["dirty"] = len([l for l in (status or "").splitlines() if l.strip()])
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    facts["branch"] = branch or "（未知）"

    wf_dir = os.path.join(ROOT, ".github", "workflows")
    facts["workflows"] = sorted(os.listdir(wf_dir)) if os.path.isdir(wf_dir) else []

    facts["py_files"] = _count_files((".py",))
    facts["kt_files"] = _count_files((".kt",), "android")
    facts["docs"] = len([f for f in os.listdir(os.path.join(ROOT, "docs"))
                         if f.endswith(".md")]) if os.path.isdir(os.path.join(ROOT, "docs")) else 0
    facts["now"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return facts


def render(f):
    ok = "✅ 一致" if f["aligned"] else "⚠️ 不一致（发版前必须改齐）"
    dirty = "干净" if f["dirty"] == 0 else "%d 个未提交改动" % f["dirty"]
    lines = [
        "# STATE.md — 当前事实快照",
        "",
        "> **自动生成，勿手改**：`python dev/agent_state.py`（%s）。" % f["now"],
        "> 想要长期有效的信息写 `.agent/CONTEXT.md`，一次性的经过写 `.agent/HANDOVER.md`。",
        "",
        "## 版本",
        "",
        "| 位置 | 值 |",
        "| --- | --- |",
        "| `pdfmask.py` VERSION | `%s` |" % f["py"],
        "| 安卓 `appVersionName` | `%s` |" % f["android"],
        "| `version_info.txt` FileVersion | `%s` |" % f["vi_string"],
        "| `version_info.txt` filevers | `%s` |" % f["vi_fixed"],
        "",
        "**三处是否对齐**：%s" % ok,
        "",
        "## 仓库",
        "",
        "- 分支：`%s`　工作区：%s" % (f["branch"], dirty),
        "- 最新 tag：`%s`" % f["tag"],
        "",
        "## 最近 5 次提交",
        "",
    ]
    if f["commits"]:
        lines += ["```"] + f["commits"] + ["```"]
    else:
        lines.append("（读不到 git 记录：本机可能只有 PortableGit，用完整路径调用）")
    lines += [
        "",
        "## CI",
        "",
    ]
    if f["workflows"]:
        lines += ["- `.github/workflows/%s`" % w for w in f["workflows"]]
    else:
        lines.append("- （没有工作流）")
    lines += [
        "",
        "## 规模",
        "",
        "- Python 文件 %d 个（Windows + Linux 同一套代码）" % f["py_files"],
        "- Kotlin 文件 %d 个（安卓原生实现）" % f["kt_files"],
        "- `docs/` 文档 %d 篇" % f["docs"],
        "",
        "---",
        "",
        "下一步该看什么：`.agent/HANDOVER.md` 最近 3 条 → `.agent/CONTEXT.md` → 命中文件。",
        "",
    ]
    return "\n".join(lines)


def main():
    text = render(collect())
    if "--print" in sys.argv[1:]:
        sys.stdout.write(text)
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("已刷新 %s" % os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
