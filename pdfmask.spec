# -*- mode: python ; coding: utf-8 -*-
import os

# ---------------------------------------------------------------------------
# VC 运行库：PyInstaller 会从 Python 安装目录里捞 msvcp140.dll（常见是 14.2x），
# 而 onnxruntime 要求更新的版本（14.4+）。版本过旧的表现不是报错，而是
# `import onnxruntime` 直接段错误（退出码 139），非常难查。
# 这里统一换成系统目录里的新版本，保证 exe 自带一份够新的运行库。
# ---------------------------------------------------------------------------
_VCRT = {"msvcp140.dll", "msvcp140_1.dll", "vcruntime140.dll", "vcruntime140_1.dll"}
_SYS32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")


def _fix_vcrt(binaries):
    out, swapped = [], {}
    for entry in binaries:
        dest = entry[0]
        name = os.path.basename(dest).lower()
        if name in _VCRT:
            if name in swapped:          # 同名只留一份
                continue
            real = os.path.join(_SYS32, os.path.basename(dest))
            if os.path.isfile(real):
                out.append((dest, real, entry[2]))
                swapped[name] = real
                continue
            print("[spec] 警告：%s 在 System32 里找不到，沿用 PyInstaller 自带版本" % name)
        out.append(entry)
    return out


a = Analysis(
    ['pdfmask.py'],
    pathex=[],
    binaries=[],
    # OCR 模型随包分发（离线、不联网），路径必须与 pdfmask_ocr.model_dir() 一致
    datas=[
        ('assets/ocr/ch_PP-OCRv4_det_infer.onnx', 'assets/ocr'),
        ('assets/ocr/ch_PP-OCRv4_rec_infer.onnx', 'assets/ocr'),
        ('assets/ocr/ppocr_keys_v1.txt', 'assets/ocr'),
        ('assets/ocr/LICENSE-APACHE-2.0.txt', 'assets/ocr'),
        ('assets/ocr/README.md', 'assets/ocr'),
    ],
    hiddenimports=['onnxruntime.capi._pybind_state'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 注意：numpy 与 onnxruntime 是 OCR 的运行时依赖，不能排除
    excludes=['pymupdf4llm', 'pymupdf_layout', 'tabulate', 'pandas', 'PyQt5', 'PySide6', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
a.binaries = _fix_vcrt(a.binaries)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PDF隐私打码工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # onnxruntime 的 DLL 被 UPX 压缩后容易加载失败，排除掉
    upx_exclude=['onnxruntime*', 'vcruntime*', 'msvcp*'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app.ico'],
    version='version_info.txt',
)
