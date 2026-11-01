# 第三方组件声明 / Third-Party Notices

本项目（PDF 隐私打码工具）以 **GNU AGPL-3.0-or-later** 授权发布，
并附带依据 **AGPL-3.0 第 7 条 (b) 项** 制定的附加条款 —— 见 **[ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md)**。

简而言之：二次开发或商用都可以，但**必须保留作者署名，并在程序里标注原项目地址**
`https://github.com/neurotracee/pdf-privacy-masker`。

打包发布的可执行文件内包含了下列第三方组件，各自的授权与版权归其作者所有。

---

## PyMuPDF / MuPDF

- 项目地址：<https://github.com/pymupdf/PyMuPDF>
- 使用版本：1.28.x
- 授权方式：**AGPL-3.0** 或 Artifex 商业许可（双授权）
- 版权：Copyright (C) 2004–2026 Artifex Software, Inc.
- 说明：本项目选择 AGPL-3.0，正是为了满足 PyMuPDF 的 AGPL 条款。若你希望在不适用 AGPL 的场景下使用本项目的代码，需要自行向 Artifex 购买商业许可，或改用其他 PDF 库。

## Pillow

- 项目地址：<https://github.com/python-pillow/Pillow>
- 使用版本：13.x
- 授权方式：HPND License（MIT-CMU 风格）
- 版权：Copyright (c) 2010 by Jeffrey A. Clark and contributors；基于 Python Imaging Library 的 Work of the Imaging Authors。

## PyInstaller

- 项目地址：<https://github.com/pyinstaller/pyinstaller>
- 使用版本：6.x
- 授权方式：GPL-2.0-or-later，并附有 **Bootloader Exception**
- 说明：例外条款明确允许把用 PyInstaller 打包的程序以任何许可发布，因此不影响本项目的 AGPL-3.0 授权。

## Python

- 项目地址：<https://www.python.org/>
- 授权方式：PSF License Agreement

## zlib / libpng / freetype 等

MuPDF 与 Pillow 的构建产物中可能包含 zlib、libpng、libjpeg-turbo、freetype 等基础库，均为宽松许可（zlib / libpng / IJG / FTL），随各自上游声明。

---

## 关于「打包后的 exe 必须开源」

AGPL-3.0 第 6 条要求：以目标代码形式分发时，必须向接收者提供**对应源代码**（Corresponding Source）。

本仓库的源码即为该对应源代码。任何人拿到本项目的 exe，都可以用以下命令重新构建出功能等价的程序：

```bash
pip install -r requirements.txt
pyinstaller pdfmask.spec --noconfirm --clean
```

因此分发本项目的 exe 不构成对 AGPL-3.0 的违反。
