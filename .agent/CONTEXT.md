# CONTEXT.md — 项目长期背景（人手写，改得慢）

> 这里只放**不会因为一次提交就变**的东西：产品是什么、代码怎么分层、哪些坑踩过。
> 会变的事实（版本、tag、最近提交）看 `STATE.md`（自动生成）；一次性的经过看 `HANDOVER.md`。
> 三份加起来读完不超过 5 分钟，读之前先想清楚这次任务要哪一份。

## 1. 产品一句话

**PDF 隐私打码工具**：把 PDF 拖进去，本机认出手机号、身份证号、银行卡、姓名等敏感信息，
用不可还原的马赛克盖掉，生成一份新的打码 PDF。原文件永远只读。

- 三端同一个产品：**Windows / Linux 同一套 Python 代码**，**安卓是 Kotlin 原生重写**
  （不是套壳、不是 WebView），两端规则逐条对齐，`RuleParityTest` 452 条结果一致。
- 全程离线：不联网、不上传、不用云端大模型（内置 PP-OCRv4，`assets/ocr/*.onnx`）。
- 协议 AGPL-3.0-or-later + 三条附加要求（署名、程序内标注原项目地址、改过的要说改过），
  见 `ADDITIONAL-TERMS.md`。

## 2. 架构

### Windows / Linux（Python）

| 文件 | 职责 |
| --- | --- |
| `pdfmask.py` | 主程序：本地 HTTP 服务 + 前端页（`HTML_UI` 内嵌）+ CLI + 检测流水线编排 |
| `pdfengine.py` | PDF 读写与坐标（pymupdf 封装，几何表达式都集中在这里） |
| `pdfmask_webui.py` | 界面文案与前端资源（中英双语） |
| `pdfmask_ocr.py` | 本地 OCR（PP-OCRv4 onnx，numpy+Pillow+onnxruntime，软依赖） |
| `pdfmask_update.py` | 版本检查与新版本提示 |
| `pdfmask_log.py` | 日志落盘与回放 |

界面形态（容易被误会，写清楚）：程序启动后监听 `127.0.0.1` 的**随机端口**，用系统默认
浏览器打开这一页；页面关了 30 分钟没请求就自动退出。「退出」按钮在页面右上角。
**它不是原生桌面窗口程序**，README 配图里那层浏览器外壳也是代码画的（图下有小字说明）。

### 安卓（Kotlin + Compose）

`android/app/src/main/java/com/neurotracee/pdfmask/`：
`core/Detector.kt` 识别规则、`core/PdfTextExtractor.kt` 取文字层、`core/OcrEngine.kt` OCR、
`core/AlignMap.kt` + `core/CharLayout.kt` 字坐标对齐、`core/PdfMasker.kt` 输出打码 PDF、
`core/MaskRegion.kt` 手动框选、`core/DraftStore.kt` 断点草稿、`core/Job.kt` 任务与取消、
`core/Tables.kt` 表格、`core/PageZoom.kt` 缩放。
界面：`MainActivity.kt` + `ui/`（含 `LogDialog.kt` 应用日志、`WheelTimePicker.kt` 时间滚轮）。

改规则时**必须两端一起改**，否则 `RuleParityTest` 会红。

## 3. 已知坑（踩过一次就别再踩）

- **安卓构建必须用 PowerShell 调 `gradle.bat`**：在 Git Bash 里跑 Gradle 会在 AAPT2 阶段失败。
- `maven.google.com` 在本机不可达，仓库地址要用 `https://dl.google.com/dl/android/maven2/`。
- 工具链固定：JDK 17 + Gradle 8.7 + AGP 8.4.2 + compileSdk 34 + minSdk 26。
- 无线调试 adb 命令要加 `MSYS_NO_PATHCONV=1`，否则路径被改写。
- 推送走 https 时本机 hosts 会把 `github.com` 改写到加速镜像；直推要用
  `https://<user>:<token>@github.com:443/...` 并在 Git Bash 下 `env -u https_proxy`。
- 本机 safe-delete 会拦 `Remove-Item -Recurse`；要删目录用重命名或移到临时目录。
- 生成 README 配图（`dev/make_readme_shots.py`）依赖无头 Edge + 真实样例 PDF，
  图下小字统一在 `dev/shot_note.py`，别在别处另写一套文案。

## 4. 测试与自检

| 目的 | 命令 / 文件 |
| --- | --- |
| Python 端全量自检 | `python dev/selfcheck.py` |
| 识别规则基线 | `test/rules_golden.json`（`dev/gen_rules_golden.py` 生成，勿手改） |
| 安卓规则对齐 | `android/` 内 `RuleParityTest`（`gradle test`） |
| exe 冒烟 | `python dev/smoke_exe.py` |
| CI | `.github/workflows/ci.yml`（ubuntu + windows 矩阵）、`linux-appimage.yml` |

扫描件、旋转页、表格、误报这几类问题的**已知边界写在 `docs/03-识别规则与已知限制.md`**，
改识别逻辑前先看那份，别把「已知限制」当 bug 修。

## 5. 发版链路

`dev/publish_all.py` 串起：GitHub Release 正文 + 附件 → 等 CI 产出 AppImage →
`dev/fetch_appimage_accel.py` 经加速站取回 → `dev/sync_gitee_releases.py` 同步 Gitee。
规矩：**两端同时出包**，版本号三处对齐（`STATE.md` 会标出来）。

## 6. 改动红线

- **规则改动要有对照测试**：误报比漏报更伤，基线 `test/rules_golden.json`，改完两端一起跑。
- **不引入联网依赖、不接云端模型**：离线是产品承诺，这条没有例外。
- **原 PDF 只读**：不覆盖、不改名、不删用户文件。
- **只有主对话能动手**：功能、bug、README / 配图、Release / 发版全部归用户主对话；
  其他会话一律不处理，只读背景（见 `AGENTS.md` 第 0 节）。
- **主对话内部一次只做一件事**：不顺手扩范围，避免上下文变长、多花额度；顺手发现的
  问题记进 `HANDOVER.md` 的「本次未做，留待下次」。
