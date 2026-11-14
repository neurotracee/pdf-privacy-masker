# OCR 模型来源与授权 / OCR model provenance

本目录存放「无文字层 PDF」自动识别所需的模型文件。**全部随程序离线分发，运行时不出网。**

| 文件 | 用途 | 大小 | SHA-256 |
| --- | --- | --- | --- |
| `ch_PP-OCRv4_det_infer.onnx` | 文字检测（DB 网络，输出文字区域概率图） | 4,745,517 B | `d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9` |
| `ch_PP-OCRv4_rec_infer.onnx` | 文字识别（CRNN + CTC，输出字符序列） | 10,857,958 B | `48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b` |
| `ppocr_keys_v1.txt` | 识别字典（6623 字） | 26,250 B | `a1c84d9bdb9ab29043c58896224d32941783eb821629618416dcb08f12886492` |
| `LICENSE-APACHE-2.0.txt` | 上述模型的许可原文 | 11,358 B | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |

## 出处

- **模型**：百度 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 的 PP-OCRv4 移动端中英文模型
  （`ch_PP-OCRv4_det` / `ch_PP-OCRv4_rec`，官方中文场景默认档）。
- **ONNX 转换版**：取自 [RapidOCR](https://github.com/RapidAI/RapidOCR)（`SWHL/RapidOCR`）的
  `PP-OCRv4/` 目录，为 PaddleOCR 官方权重转换而来的 ONNX 格式，权重数值未改动。
- **字典**：PaddleOCR 仓库 `ppocr/utils/ppocr_keys_v1.txt`。

## 授权

两份上游仓库均为 **Apache License 2.0**，扫描结果：

```
PaddlePaddle/PaddleOCR   Apache-2.0
RapidAI/RapidOCR         Apache-2.0
```

Apache-2.0 是宽松许可，允许复制、修改、再分发与商用，包括并入以 AGPL-3.0 发布的工程，
条件只有三条，本项目均已满足：

1. **保留版权、专利、商标与归属声明** —— 见本文件与根目录 `NOTICE.md`。
2. **随分发附带许可原文** —— 见同目录 `LICENSE-APACHE-2.0.txt`（不删不改）。
3. **若修改过文件需注明** —— 本项目未修改模型权重，仅原样打包，故无需额外声明；
   后续若对模型做过量化/裁剪，必须在此处写明改了什么。

Apache-2.0 还包含**明示的专利授权**（第 3 条），对使用者比 MIT 更有保障。

## 为什么不打包 OpenCV

本项目的检测后处理（连通域、外扩框）用 numpy 手写实现，未引入 OpenCV。
这样发布包少约 40 MB，也避免 PyInstaller 打包 OpenCV 的动态库时出现兼容问题。
OpenCV 仅在本机开发阶段用于交叉校验算法结果，不进入发布产物。
