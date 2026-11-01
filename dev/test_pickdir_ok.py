# -*- coding: utf-8 -*-
"""自测 2：在对话框里按回车直接选定当前文件夹，确认能拿到绝对路径。"""
import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdfmask  # noqa: E402

user32 = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
VK_RETURN = 0x0D

TARGET = pdfmask._fallback_dir()
result = {"value": None, "done": False}


def worker():
    result["value"] = pdfmask._pick_directory("选择打码后 PDF 的保存位置", TARGET)
    result["done"] = True


def main():
    if not os.path.isdir(TARGET):
        print("跳过：桌面目录不存在")
        return 0
    th = threading.Thread(target=worker, daemon=True)
    th.start()

    hwnd = None
    for _ in range(40):
        time.sleep(0.3)
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(h, _):
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(h, cls, 64)
            if cls.value == "#32770" and user32.IsWindowVisible(h):
                found.append(h)
            return True

        user32.EnumWindows(cb, None)
        if found:
            hwnd = found[0]
            break
        if result["done"]:
            break

    if not hwnd:
        print("✗ 没找到对话框")
        return 1

    time.sleep(1.0)
    user32.PostMessageW(ctypes.c_void_p(hwnd), WM_KEYDOWN, VK_RETURN, 0)
    time.sleep(0.15)
    user32.PostMessageW(ctypes.c_void_p(hwnd), WM_KEYUP, VK_RETURN, 0)

    th.join(timeout=15)
    print("结果：", result)
    if not result["done"]:
        print("✗ 卡住")
        return 1
    path, status = result["value"]
    ok = bool(path) and os.path.isdir(path)
    print("状态：", status, "路径：", repr(path))
    print("✓ 通过：能返回选中的文件夹绝对路径" if ok else "✗ 未取到路径")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
