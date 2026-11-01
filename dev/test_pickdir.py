# -*- coding: utf-8 -*-
"""自测：Windows 原生「选择文件夹」对话框能否正常弹出 / 取消。

不弹窗给人看的自动化测试：子线程调 _pick_directory，主线程找到对话框再关掉，
确认返回 "cancel" 而不是崩进程或卡死。
"""
import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pdfmask  # noqa: E402

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010

result = {"value": None, "done": False}


def worker():
    t0 = time.time()
    result["value"] = pdfmask._pick_directory("选择打码后 PDF 的保存位置",
                                              os.path.expanduser("~"))
    result["secs"] = round(time.time() - t0, 2)
    result["done"] = True


def find_dialog():
    hwnds = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(256)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if cls.value == "#32770" and user32.IsWindowVisible(hwnd):
            hwnds.append((hwnd, buf.value))
        return True

    user32.EnumWindows(cb, None)
    return hwnds


def main():
    th = threading.Thread(target=worker, daemon=True)
    th.start()

    target = None
    for _ in range(40):          # 最多等 12 秒
        time.sleep(0.3)
        for hwnd, title in find_dialog():
            print("发现对话框：cls=#32770 title=%r" % title)
            target = hwnd
            break
        if target:
            break
        if result["done"]:
            break

    if not target:
        print("✗ 没有检测到系统对话框")
        print("  结果：", result)
        return 1

    time.sleep(0.6)
    user32.PostMessageW(ctypes.c_void_p(target), WM_CLOSE, 0, 0)

    th.join(timeout=10)
    print("返回值：", result)
    if not result["done"]:
        print("✗ 关闭对话框后函数没有返回（可能卡死）")
        return 1
    path, status = result["value"]
    ok = (path == "" and status == "cancel")
    print("状态：", status, "路径：", repr(path))
    print("✓ 通过：对话框能弹出、能取消、函数正常返回" if ok else "✗ 结果与预期不符")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
