# -*- mode: python ; coding: utf-8 -*-
"""Linux 打包规格（AppImage 用 onedir，不是单文件）。

为什么不用单文件：AppImage 本身就是「一个目录树压成一个可执行文件」，
里面再套一个 PyInstaller 单文件（每次启动都要解压到 /tmp）会慢一倍，
而且 AppImage 自己已经解决了「双击即用」这件事，没必要叠加两层自解压。

产物：dist/pdfmask/ 目录，入口 dist/pdfmask/pdfmask。
平台相关的部分（VC 运行库修补、exe 图标/版本属性）在 Windows 的
pdfmask.spec 里，这里不重复。
"""
import os

# ---------------------------------------------------------------------------
# OCR 模型随包分发（离线、不联网），路径必须与 pdfmask_ocr.model_dir() 一致：
# PyInstaller 6 的 onedir 会把 datas 放进 _internal/，而 sys._MEIPASS 正好指向它，
# 所以 model_dir() 里那条 os.path.join(base, "assets", "ocr") 不用改。
# ---------------------------------------------------------------------------
a = Analysis(
    ['pdfmask.py'],
    pathex=[],
    binaries=[],
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
    # numpy 与 onnxruntime 是 OCR 的运行时依赖，不能排除
    excludes=['pymupdf4llm', 'pymupdf_layout', 'tabulate', 'pandas',
              'PyQt5', 'PySide6', 'matplotlib', 'tkinter'],
    noarchive=False,
    optimize=0,
)

# pymupdf 自带的 layout / table onnx 模型本项目用不到，剔掉能省三十多兆
_DROP = ("pymupdf/layout/", "pymupdf/table/")
a.datas = [d for d in a.datas
           if not d[0].replace("\\", "/").lower().startswith(_DROP)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pdfmask',
    debug=False,
    bootloader_ignore_signals=False,
    # strip 会把 onnxruntime 的 .so 符号表削掉，某些发行版上会加载失败，关掉
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='pdfmask',
)
