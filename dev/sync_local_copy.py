# -*- coding: utf-8 -*-
"""把刚打好的 exe 同步到「本机日常在用的那一份」。

开源项目有个容易漏的环节：Release 上传得很及时，但开发者自己桌面上那份
还是两周前编译的，日常测的都是旧代码。这个脚本把最后一步补上——
打包完成后自动把 dist 里的 exe 覆盖到日常运行的位置，旧版按版本号存进
旁边的 _old/ 目录，需要回退时直接拿。

目标路径不写进仓库（每个人的机器不一样），从这两个地方读，先到先用：

    1. 命令行 --target "D:\\某处\\PDF隐私打码工具.exe"
    2. dev/.local_copy_target 文件（已在 .gitignore 里，内容是完整目标路径）
    3. 环境变量 PDFMASK_LOCAL_EXE

都没有就安静退出（返回码 0），不影响别人打包。

用法：
    python dev/sync_local_copy.py               # 打包.bat 里自动调用
    python dev/sync_local_copy.py --check       # 只比较，不复制
    python dev/sync_local_copy.py --target ...  # 临时指定别处
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "dist", "PDF隐私打码工具.exe")
TARGET_FILE = os.path.join(ROOT, "dev", ".local_copy_target")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_target(cli_target):
    if cli_target:
        return cli_target
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, encoding="utf-8") as f:
            line = f.read().strip()
        if line:
            return line
    return os.environ.get("PDFMASK_LOCAL_EXE", "").strip()


def _iter_processes():
    """逐个列出 (pid, exe 完整路径)。

    直接用 Win32 API 枚举，不依赖 tasklist / PowerShell：中文进程名经过
    命令行参数和代码页转手后经常匹配不上，这里按完整路径比较最稳。
    """
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.QueryFullProcessImageNameW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, ctypes.c_wchar_p,
        ctypes.POINTER(wintypes.DWORD)]

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == ctypes.c_void_p(-1).value:
        return
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pid = entry.th32ProcessID
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h:
                try:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(1024)
                    if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                        yield pid, buf.value
                finally:
                    k32.CloseHandle(h)
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)


def running_pids(path):
    """找出占着这个 exe 的进程。"""
    if os.name != "nt":
        return []
    want = os.path.normcase(os.path.abspath(path))
    out = []
    try:
        for pid, exe in _iter_processes():
            if os.path.normcase(exe) == want:
                out.append(str(pid))
    except Exception:
        return []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="", help="目标 exe 完整路径（覆盖配置文件）")
    ap.add_argument("--check", action="store_true", help="只报告是否一致，不复制")
    ap.add_argument("--close", action="store_true", help="目标正在运行时先关掉它再复制")
    a = ap.parse_args()

    target = resolve_target(a.target)
    if not target:
        print("未配置本地副本路径，跳过（见 dev/.local_copy_target）")
        return 0
    if not os.path.exists(SRC):
        print("找不到构建产物：%s" % SRC)
        return 1
    if not os.path.exists(target):
        folder = os.path.dirname(target)
        print("目标不存在，视为新安装：%s" % target)
        os.makedirs(folder, exist_ok=True)

    src_hash = sha256(SRC)
    if os.path.exists(target) and sha256(target) == src_hash:
        print("本地副本已是最新，无需操作：%s" % target)
        return 0

    old_ver = ""
    if os.path.exists(target):
        old_ver = read_version(target)
    new_ver = read_version(SRC)
    print("本地副本待更新：%s -> %s" % (old_ver or "未知版本", new_ver or "当前构建"))

    if a.check:
        print("（--check：只比较，未复制）")
        return 0

    pids = running_pids(target)
    if pids:
        if not a.close:
            print("目标程序正在运行（PID %s），请先关闭后重试，或加 --close 自动关闭"
                  % ", ".join(pids))
            return 2
        subprocess.run(["taskkill", "/PID"] + pids + ["/F"], capture_output=True,
                       creationflags=0x08000000)
        time.sleep(0.8)

    # 旧版按版本号备份到旁边的 _old/，方便一键回退
    if os.path.exists(target) and old_ver:
        old_dir = os.path.join(os.path.dirname(target), "_old")
        os.makedirs(old_dir, exist_ok=True)
        bak = os.path.join(old_dir, "%s-%s.exe"
                           % (os.path.splitext(os.path.basename(target))[0], old_ver))
        if not os.path.exists(bak):
            shutil.copy2(target, bak)
            print("旧版已备份：%s" % bak)

    shutil.copy2(SRC, target)
    if sha256(target) != src_hash:
        print("复制后校验不一致，请检查磁盘或权限")
        return 1
    print("已同步到本地副本：%s（%s，%.2f MB）"
          % (target, new_ver, os.path.getsize(target) / 1048576))
    return 0


def read_version(path):
    """读 exe 的文件版本号（形如 1.4.2），读不到返回空串。"""
    if os.name != "nt" or not os.path.exists(path):
        return ""
    try:
        import ctypes
        from ctypes import wintypes

        ver = ctypes.WinDLL("version", use_last_error=True)
        p = ctypes.c_wchar_p(path)
        size = ver.GetFileVersionInfoSizeW(p, None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(p, 0, size, buf):
            return ""
        ptr = ctypes.c_void_p()
        ln = wintypes.UINT()
        if not ver.VerQueryValueW(buf, ctypes.c_wchar_p("\\"),
                                  ctypes.byref(ptr), ctypes.byref(ln)):
            return ""

        class VS_FIXEDFILEINFO(ctypes.Structure):
            _fields_ = [
                ("dwSignature", wintypes.DWORD), ("dwStrucVersion", wintypes.DWORD),
                ("dwFileVersionMS", wintypes.DWORD), ("dwFileVersionLS", wintypes.DWORD),
                ("dwProductVersionMS", wintypes.DWORD), ("dwProductVersionLS", wintypes.DWORD),
                ("dwFileFlagsMask", wintypes.DWORD), ("dwFileFlags", wintypes.DWORD),
                ("dwFileOS", wintypes.DWORD), ("dwFileType", wintypes.DWORD),
                ("dwFileSubtype", wintypes.DWORD), ("dwFileDateMS", wintypes.DWORD),
                ("dwFileDateLS", wintypes.DWORD),
            ]

        info = ctypes.cast(ptr, ctypes.POINTER(VS_FIXEDFILEINFO)).contents
        parts = [
            (info.dwFileVersionMS >> 16) & 0xFFFF, info.dwFileVersionMS & 0xFFFF,
            (info.dwFileVersionLS >> 16) & 0xFFFF, info.dwFileVersionLS & 0xFFFF,
        ]
        # 1.4.2.0 这种末位为 0 的按 1.4.2 显示，和发布命名保持一致
        while len(parts) > 2 and parts[-1] == 0:
            parts.pop()
        return ".".join(str(x) for x in parts)
    except Exception:
        return ""


if __name__ == "__main__":
    sys.exit(main())
