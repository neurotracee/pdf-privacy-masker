# 第三方组件声明 / Third-Party Notices

本项目（PDF 隐私打码工具，Windows 与安卓双端）整体以 **GNU AGPL-3.0-or-later** 授权发布，
并附带依据 **AGPL-3.0 第 7 条 (b) 项** 制定的附加条款 —— 见 **[ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md)**。

简而言之：二次开发或商用都可以，但**必须保留作者署名，并在程序里标注原项目地址**
`https://github.com/neurotracee/pdf-privacy-masker`（国内镜像：`https://gitee.com/bio234/pdf-privacy-masker`）。

下面按平台列出用到的第三方组件，各自的授权与版权归其作者所有。

---

## 一、Windows 端（打包进 exe）

| 组件 | 版本 | 授权 | 版权 |
| --- | --- | --- | --- |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) / MuPDF | 1.28.x | **AGPL-3.0** 或 Artifex 商业许可（双授权） | Copyright (C) 2004–2026 Artifex Software, Inc. |
| [Pillow](https://github.com/python-pillow/Pillow) | 13.x | HPND（MIT-CMU 风格） | Copyright (c) 2010 by Jeffrey A. Clark and contributors |
| [PyInstaller](https://github.com/pyinstaller/pyinstaller) | 6.x | GPL-2.0-or-later + Bootloader Exception | — |
| [Python](https://www.python.org/) | 3.11+ | PSF License Agreement | — |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | 1.31.x | **MIT** | Copyright (c) Microsoft Corporation |
| [NumPy](https://numpy.org/) | 2.x | BSD-3-Clause（另含 0BSD / MIT / Zlib / CC0-1.0 片段） | Copyright (c) NumPy Developers |

- **PyMuPDF** 是双授权：本项目选择 AGPL-3.0，正是为了满足它的 AGPL 条款。若要在不适用 AGPL 的场景下使用本项目代码，需自行向 Artifex 购买商业许可，或改用其他 PDF 库。
- **PyInstaller** 的 Bootloader Exception 明确允许把打包后的程序以任何许可发布，不影响本项目的 AGPL-3.0 授权。
- MuPDF 与 Pillow 的构建产物中可能包含 zlib、libpng、libjpeg-turbo、freetype 等基础库，均为宽松许可（zlib / libpng / IJG / FTL），随各自上游声明。

## 二、安卓端（打包进 apk）

| 组件 | 版本 | 用途 | 授权 |
| --- | --- | --- | --- |
| [PDFBox-Android](https://github.com/TomRoush/PdfBox-Android) | 2.0.27.0 | 读取 PDF 文字层与版面坐标 | Apache License 2.0 |
| AndroidX（core-ktx / lifecycle / activity-compose / window / documentfile） | — | 基础框架 | Apache License 2.0 |
| Jetpack Compose（ui / foundation / material3 / material-icons-core） | — | 界面 | Apache License 2.0 |
| Kotlin 标准库 | — | 语言运行时 | Apache License 2.0 |
| [ONNX Runtime Android](https://github.com/microsoft/onnxruntime) | 1.20.0 | 扫描件 OCR 推理（CPU） | **MIT** |

仅用于测试、不进入 apk：

| 组件 | 用途 | 授权 |
| --- | --- | --- |
| Robolectric 4.12.2 | 在 JVM 上渲染界面截图 | MIT |
| JUnit 4 / kotlin-test | 测试框架 | EPL-1.0 / Apache-2.0 |
| Apache PDFBox 2.0.27（桌面版） | 与 Windows 端做同构验证 | Apache License 2.0 |

安卓端**没有**使用 MuPDF / PyMuPDF，因此安卓端的 AGPL 义务来自本项目自身的授权选择，而非依赖传染。

---

## 三、OCR 模型（纯图片 / 扫描件 PDF 识别，双端共用）

用于给**没有文字层**的 PDF 定位文字区域。模型随程序离线分发，运行时不联网。

| 组件 | 版本 | 用途 | 授权 |
| --- | --- | --- | --- |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) PP-OCRv4 模型 | ch_PP-OCRv4_det / rec | 文字检测与识别 | **Apache License 2.0** |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | — | 官方权重的 ONNX 转换版 | **Apache License 2.0** |

- 两份上游仓库均为 Apache-2.0（宽松许可），可以并入以 AGPL-3.0 发布的工程；
  许可原文随模型一起放在 `assets/ocr/LICENSE-APACHE-2.0.txt`，出处与文件哈希见
  `assets/ocr/README.md`。
- 本项目**未修改**模型权重，仅原样打包，因此无需声明修改；若后续做量化或裁剪，
  必须在上述文件中写明改动内容。
- Apache-2.0 第 3 条含**明示专利授权**，对使用者比 MIT 更有保障。
- 检测后处理（连通域、外扩框、灰度归一化）全部自实现（Python 用 NumPy，安卓用 BFS 洪泛），**双端均未使用 OpenCV**，因此 exe 与 apk 里都不含 OpenCV 的几十 MB 动态库。

---

## 四、必须保留的署名（AGPL-3.0 第 5 条，请勿删除）

```
指导作者：项目创作时为初中生 —— 需求、识别规则的设计、验收测试全部由本人完成
开发    ：腾讯 WorkBuddy × DeepSeek-V4.1-Flash
原项目  ：https://github.com/neurotracee/pdf-privacy-masker
镜像    ：https://gitee.com/bio234/pdf-privacy-masker
```

二次开发或商用必须保留以上署名，并在程序中标注原项目地址；改动过的版本须注明
「本程序基于该地址修改，非原作者发布」。详见 [ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md)。

## 五、关于「打包后的程序必须开源」

AGPL-3.0 第 6 条要求：以目标代码形式分发时，必须向接收者提供**对应源代码**（Corresponding Source）。

本仓库即为该对应源代码。任何人拿到本项目的 exe 或 apk，都可以重新构建出功能等价的程序：

```bash
# Windows
pip install -r requirements.txt
pip install pyinstaller
pyinstaller pdfmask.spec --noconfirm --clean

# 安卓
cd android && gradle assembleRelease
```

构建细节见 [docs/05-构建与发布.md](docs/05-构建与发布.md)。

## 六、名称与图标

程序名称「PDF 隐私打码工具」与图标不在授权范围内（AGPL-3.0 第 7 条 (e) 项）。
二次发布请改名、换图标。
