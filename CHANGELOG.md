# 未发布（main 分支）

**中文** | [English](#unreleased-main)

更新级别：建议（主要是扫描件识别准确率；另把版本号格式改成四段）

> 版本号：**1.4.6.1**。这一版只动**第四位**——它是「小版本」，日常修缺陷、改文案、补文档就动它。
> 从这一版起版本号统一写成四段 `主.次.修订.小版本`：越靠右越细、动得越勤；
> 第三位才是「大版本」（成体系的新能力，如 v1.4.6 的扫描件 OCR），
> 第二位留给多项大改合并发布，第一位要等整代翻新。规则见 `CONTRIBUTING.md` 第 4 节。

> **一句话**：拿 8 页真实单据当刁难文档压测扫描件，暴露出 6 处识别缺陷，全部修掉；刁难文档 4.0 现在 86 条真值全过。

## 这一轮做了什么

新增 **刁难文档 4.0**：8 页真实单据（简历 / 租房合同 / 门诊病历 / 银行对账单 /
快递面单 / 会议通知 / 理赔申请 / 家长登记），纯文字段落、不打表格，每页多人多号码，
整页渲染成 260~300 dpi 灰度图并叠加倾斜、噪点、光照不均与 JPEG 痕迹，
**成品 PDF 里没有一行文字层**。

验收脚本 `dev/test_hard4.py` 只下发命令，识别与打码全部由程序完成，判定分三层：
漏检（认不出）、泄漏（打码后还读得出）、误伤（业务数据被打）。首次运行结果：
**87 条真值里 43 条漏检、4 条泄漏**——问题不在规则，而在扫描件的图像处理。

## 另外：两端版本号不再互相拖累（Windows + 安卓）

以前 Windows 和安卓共用一个版本号，带来两个麻烦：只改了安卓的文案，Windows 也得把
73MB 的 exe 重打重传一遍；只发一端的版本，另一端的「检查更新」偶尔会拿 tag 版本兜底，
提示一条**下载页里根本没有对应安装包**的假更新。

现在两端版本号各自独立（`pdfmask.VERSION` 归 Windows，`appVersionName` 归安卓），
判断要不要更新时**只比自己安装包文件名里的版本号**；某个 Release 只给另一端发了包，
对本平台就等于「没更新」。只发一端时用 `dev/publish_github_release.py --only exe|apk`，
另一端的包不会被误传。回归测试 `dev/test_platform_split.py`（CI 已接入）守住这条。

## 修掉的六个缺陷

| 缺陷 | 现象 | 修法 |
| --- | --- | --- |
| 倾斜未校正 | 0.9 度倾斜，15 行只认出 5 行 | 检测前用水平投影方差估角并摆正（误差 < 0.1 度） |
| 渲染分辨率固定 180 dpi | 300 dpi 扫描件被降采样，末位数字丢失 | 按页面图片实际像素密度自适应，最高 300 dpi |
| 单行宽度上限 1280 | 一行同时有手机号和邮箱时，号码被压变形 | 上限提到 2560 |
| 检测框外扩 0.45 倍字高 | `139-1111-2222` 读成 `139-1111-222` | 外扩提到 0.85 倍字高（两端同步） |
| 号码少一位就整条不认 | 标签明明写着「手机」，号码差一位就漏 | 新增标签兜底：手机/联系电话后 9~12 位数字形态一律按手机号打 |
| 姓名标签被字段名污染 | `派件员:吴强工号8823` 整段判成姓名不合法 | 在「工号/手机/电话…」处截断再判断 |

另外补了「邮箱」标签兜底（域名被认丢一个点 `example.cn → example.n` 时仍整段打），
以及 `寄件人 / 派件员 / 接收人 / 受益人 / 监护人 / 接送人 / 学生姓名` 等 13 个姓名标签。

## 结果

- 刁难文档 4.0：**86 条真值全过（漏检 0 / 泄漏 0 / 误伤 0）**，单页 1.0~1.4 秒
- 原有 15 项自检全部仍通过（规则改动没有带出误报）
- 安卓端规则表同步改完，`compileDebugKotlin` 与 `testDebugUnitTest` 通过

## 文档补充

- **安卓更新弹窗常驻一块「侧载安装提示」**（`ui/UpdateNotes.kt` 的 `InstallHint()`，中英双语）：
  勾选「已知悉应用风险」→ 仍然安装即可，并说明这是国内四大厂 2026 年 11 月起的校验、
  不是包坏了、每次更新都会再提示。与发布正文是否为空无关，永远显示——用户点「下载」前
  唯一一定会看到的位置就是这里。
- **README 开头新增三段说明**（中英双语）：① 为什么会弹「开发者身份未验证」——四家 ADV 需本人身份证、
  实名银行卡与人脸活体，作者未成年、拿不到本人实名的银行卡，因此无法完成，提示会一直存在但不阻止安装；
  ② 为什么会提示「信息将被第三方收集」——系统安装器对所有非商店来源包的模板文案，本程序没有第三方 SDK；
  ③ 唯一的联网权限是自动/手动检查更新，只连 Gitee 与 GitHub 两个仓库，不上传任何文件或个人信息。
- **README 章节顺序调整**：把「界面」整节移到「打码效果演示」之后（先看效果、再看界面），只搬位置，
  正文一字未改，英文半边同步。隐私说明补了「没有第三方 SDK」「联网只到两个域名」两条。
- **新写 `release/v1.4.6.1/RELEASE-NOTES.md`**：开头先放同样三段说明，再列本版改动；
  `release/v1.4.6/RELEASE-NOTES.md` 也补了这三段（该版本仍是当前下载页）。
- 安卓安装说明与常见问题新增 **ADV「未验证应用提醒」** 与**「信息将被第三方收集」**两条问答，
  并写了「把安装包发给别人时该一起说什么」。
- `docs/06` 发布清单新增一条：Release 正文必须带同一段说明，应用内与发布页两处都要有。
- 新增 `dev/sign_adv_empty_apk.py`：用发版密钥给平台的「含签名 APK 空包」签名，
  并核对指纹与正式发版 apk 一致（ADV 应用验证用；本项目暂未做验证）。
- 自检新增第 18 项：README 中英、常见问题、应用内弹窗四处提示缺一即报错，
  防止以后改文档/改界面时把它抹掉。

## 已知取舍

- 座机一律打码，包括单位总机——宁可多糊一块，不去猜「是不是私人号码」
- 低分辨率（< 200 dpi）下，一长串相同数字（`13655556666`）仍可能被并成更少的位，
  建议用 300 dpi 扫描，并核对识别结果
- **安卓端尚未做倾斜校正**：本机没有 arm64 设备可验证，先只在 Windows 端上线，
  真机验证过再补，避免把没验证过的几何变换塞进安卓

---

# Unreleased (main)

> **Version**: **1.4.6.1**. This release only moves the **fourth part** — the "small" slot
> used for everyday fixes, wording and docs. Versions are now four parts
> (`major.minor.feature.small`): the further right, the finer and the more often it moves.
> The third part is for a "big" release (a whole new capability, such as the scanned-PDF OCR
> in v1.4.6), the second for several big changes shipped together, and the first only when a
> generation turns over.

> **One line**: An 8-page adversarial scan suite exposed six OCR defects — all fixed; 86/86 expected values now pass.

New adversarial set (`dev/make_hard4_pdf.py`): eight realistic single-sided documents
(resume, lease, clinic record, bank statement, waybill, meeting notice, insurance claim,
parent registration), plain prose, several people and numbers per page, rendered to
260–300 dpi grayscale with skew, noise, uneven lighting and JPEG artefacts — **no text
layer at all**. `dev/test_hard4.py` only issues commands; detection and redaction are done
by the program itself, and each case is judged on three axes: missed, leaked, over-redacted.

Fixed: skew correction before detection (0.9° used to cost 10 of 15 lines), adaptive
render DPI (up to 300 dpi instead of a fixed 180), per-line width cap 1280 → 2560,
box padding 0.45 → 0.85 em, label-based fallbacks for phone/email when OCR drops a
character, and name-value truncation at the next field name. Android rule tables updated
in step; Kotlin compiles and unit tests pass. Skew correction is Windows-only for now —
no arm64 device here to verify it on.

Docs: the Android install guide and FAQ now cover the **ADV "unverified developer"
prompt** (the sideload identity check OPPO / vivo / Xiaomi / HONOR started on 9 Nov 2026):
tick "I understand the risk", tap "Install anyway", plus the two reasons the button can
stay greyed out. On the mainland it is a warning only — no 24-hour wait. New helper
`dev/sign_adv_empty_apk.py` signs the platform's empty verification package with the
release key and checks the fingerprint matches the shipped apk. The in-app update dialog
now carries the same instruction permanently (`InstallHint()` in `UpdateNotes.kt`), and
self-check item 18 fails if any of the four places loses that wording.

---

# v1.4.6 版本说明（Windows + 安卓）

**中文** | [English](#v146-release-notes-windows--android)

更新级别：强烈建议

> **一句话**：扫描件、拍照件、截图型 PDF 现在也能自动打码了——文字识别完全在本机跑，不联网、不上传；代价是安装包变大（Windows 73 MB、安卓 47 MB）。

这一版是功能上的一次大跨步：把上一版还明写着「不支持扫描件 PDF」的那道墙拆掉了。以前只有带文字层的 PDF 能自动识别，扫描件只能一页一页手动画框，页数一多就不现实。现在扫描件会先用本机 OCR 把字读出来，再走完全一样的识别规则。**多了一个能力，没有多一次联网。**

---

## 1. 新增：没有文字层的 PDF 也能自动打码（Windows + 安卓）

**原来的限制**：工具靠读 PDF 里的文字层拿到每个字的精确坐标，再把命中处抹掉。扫描件、手机拍照转的 PDF、图片拼成的 PDF 只有一张张图，没有文字层，一个坐标都拿不到，所以只能手动画框。顶部那个红色小标签「不支持扫描件 PDF」，说的就是这件事。

**现在的做法**：走本地文字识别（OCR）。

1. 把页面渲染成图（约 180 dpi），交给检测模型找出一行行文字的位置；
2. 再交给识别模型把每行读成文字；
3. **关键一步**：识别模型吐出来的不只是一行字，还带着「这一行里第几个字占横向的哪一段」。把它换算回页面坐标，就得到**每个字自己的矩形**——和读文字层拿到的东西一模一样；
4. 后面完全不用改：号码、姓名、地址那 700 多行识别规则原样跑，命中就打码。所以扫描件和文字层 PDF 的行为、界面、结果都一致。

**为什么强调「每个字」**：很多 OCR 只给「这一行在这里」一个大框。可打码要知道的是「18 位身份证号是这行的第 3 个字到第 20 个字」——只有一个大框就只能整行糊掉，旁边该看清的合同金额也一起没了。这一步是整件事能不能成立的关键。

**模型与体积**：用的是 PP-OCRv4 mobile 的检测 + 识别两个小模型（4.7 MB + 10.9 MB），纯 CPU 跑，不需要独立显卡。没有引入 OpenCV（连通域那点活自己用 numpy 写了），少带了约 40 MB。

**速度**（普通四核，未做任何针对性优化）：

- 模型首次加载 0.55 秒（启动后空闲时预加载，点下去不卡）；
- 单页识别 0.8–1.3 秒。10 页扫描件十几秒，可以接受。

**准确率**（A4 表单 11 行，200 dpi 扫描，文字层字符数为 0）：

- 11 行文字**全部读对**，含 18 位身份证号、19 位银行卡号、邮箱、地址、日期；
- 该打的 8 处敏感信息**全部打上**，该留的（会议日期、合同金额）**一处没误打**；
- 打码后再跑一遍 OCR 复核：5 类号码全部读不出来，该保留的仍然可读。

**什么时候才会用到 OCR**：不是每页都跑。只有「这页几乎没字（少于 24 个字符）」，或者「有字但很少、同时整页被图片盖住一半以上」才走 OCR。纯文字 PDF 一个模型都不加载，速度和以前完全一样。

## 2. 修复：全角数字、全角字母一直漏检（Windows + 安卓）

**现象**：从别处拷来的一段文字里，手机号打不出来。看着是 `１３８００１３８０００`，和普通数字长得几乎一样。

**原因**：这是「全角」字符，编码和普通数字（半角）不是同一个。识别规则里按数字匹配的模式认不出它，整串就跳过了。这个缺陷在文字层路径里一直存在，不是这版引入的——只是以前很少有人碰到全角内容。

**改法**：所有从 PDF 读出来的字符，先统一折成半角再进识别（`０-９`→`0-9`，`Ａ-Ｚ`→`A-Z`，全角空格→半角）。一个字符换一个字符，不改变字数，所以坐标不会错位。OCR 出来的字也走同一道折换——识别模型本身也常把数字认成全角。

## 3. 界面：从「不支持扫描件」改成「支持扫描件」（Windows + 安卓）

- 顶部那个红色小标签换成绿色「支持扫描件」，悬停解释改成「会自动用本地 OCR 识别（离线运行、不联网）；识别不到时可手工框选」；
- 副标题「扫描件可用「框选手动打码」」→「扫描件自动识别 · 也可手动框选」；
- 打开文件后的提示分四种情况，不再一律说「没法识别」：全部识别成功 / 部分页没认出 / 一页都没认出 / 这个安装包没带 OCR 组件；
- 翻页栏会写「OCR 已识别」还是「无文字层」，一眼能看出这页结果是怎么来的。

## 4. 降级：缺组件时自动退回手动框选，不会崩（Windows + 安卓）

OCR 是软依赖。模型文件缺失、或者运行库装不上时，程序照常启动、照常处理文字层 PDF，扫描件退回手动框选，并在提示里说明原因——不会「点开就报错」，也不会「悄悄什么都不做」。

另外留了一个开关：Windows 端设了环境变量 `PDFMASK_NO_OCR=1` 就完全不加载 OCR（比如在很老的机器上想换回原来的轻量行为）。

## 5. 工程：打包踩到一个很隐蔽的坑（Windows）

打出来的 exe 一打开就消失，命令行跑直接退出、没有任何报错。

查了很久才定位到：打包时从 Python 目录顺手捞了一个很旧的 C++ 运行库（14.26），而 OCR 的推理库要求 14.4 以上，版本对不上就**直接崩，连异常都抛不出来**。现在打包脚本会把系统里较新的那份 DLL 换进去，构建文档里也把这条写成了必看提示。

## 6. 工程：模型首次使用时复制到应用私有目录（安卓）

安卓的安装包本身是压缩包，而推理库只认磁盘上的文件路径，所以模型不能直接从安装包里读。做法是第一次真正用到识别时，把两个模型（约 15 MB）从安装包解到应用私有目录，之后一直复用。

这意味着：**首次处理扫描件会多花一两秒**，并且应用会额外占用约 15 MB 存储（卸载时一并清掉）。模型文件本身在安装包里是「不压缩」存的，否则每次解压要多花几百毫秒。

## 7. 工程与许可：自检新增一项，开源义务补齐（Windows + 安卓）

- `dev/selfcheck.py` 加第 15 项：造一份没有文字层的表单，跑完整链路（识别 → 打码 → 再识别复核），15 项全过；
- 新增 `dev/test_ocr.py`（造样张）与 `dev/test_ocr_redact.py`（端到端）；
- OCR 模型与推理库分别是 Apache-2.0 / MIT，都可以并入本项目的 AGPL-3.0。许可原文、模型出处与 SHA-256 放在 `assets/ocr/`，`NOTICE.md` 与 `README` 的依赖表新增一节说明；模型权重未做任何改动。

## 8. 已知限制（新增两条）

- **OCR 不是万能的**：手写体、严重倾斜、褶皱、极低分辨率（比如 72 dpi 的传真件）可能认不出或认错。认错就会漏打——扫描件处理完**请顺手核对一遍**，界面也会提示这一点；
- **只对「几乎没字」的页面启用**：一页里既有文字层又贴了一张扫描图（比如合同正文里插了一张证件扫描），那一页不会走 OCR，仍然需要手动画框；
- 以下两条是原有的，没变：安卓端输出仍是整页图片（打码后不能搜索、不能复制文字）；注释是整块盖掉的。

## 9. 下载

这一版 Windows 从 36.7 MB 涨到 **73.2 MB**，安卓从 14.9 MB 涨到 46.8 MB——增加的几乎就是那两个模型（14.9 MB）和各平台的推理库（安卓约 18.5 MB）。这是「本地离线识别」绕不开的成本，换来的是**不联网、不上传**。如果这个体积不能接受，可以用 `PDFMASK_NO_OCR=1` 跑回旧行为。

- Windows：`PDFPrivacyMasker-1.4.6.exe`（免安装，双击即用）
- 安卓：`PDFPrivacyMasker-1.4.6-arm64.apk`（arm64-v8a，Android 8.0+）
- 校验和：`SHA256SUMS.txt`

升级不用卸载旧版，直接覆盖安装即可。第一次处理扫描件会多等一两秒（模型要读进内存），之后每页 1 秒左右。

---

# v1.4.6 Release Notes (Windows + Android)

[中文](#v146-版本说明windows--安卓) | **English**

Update level: strongly suggested

> **In one line**: scanned, photographed and image-only PDFs can now be masked automatically — recognition runs entirely on your machine, with no network and no uploads; the cost is a bigger installer (73 MB on Windows, 47 MB on Android).

This is a large step for the tool: it removes the "no scanned PDFs" wall that the previous version still advertised. Only PDFs with a text layer could be checked automatically; a scan meant drawing every box by hand, which does not scale past a few pages. Scans are now read with a local OCR pass and then go through exactly the same detection rules. **One more capability, not one more network call.**

---

## 1. New: PDFs without a text layer can be masked automatically (Windows + Android)

**The old limit**: the tool read the PDF's text layer to get the exact coordinate of every character, then removed the hits. A scan, a phone photo turned into a PDF, or a PDF assembled from images is just pictures — no text layer, no coordinates — so manual boxes were the only option. The small red "no scanned PDFs" label at the top referred to exactly this.

**What it does now**: a local OCR pass.

1. The page is rendered to an image (about 180 dpi) and a detection model finds each line of text;
2. A recognition model then reads every line;
3. **The key step**: the recogniser does not just return a line of text — it also carries "which horizontal slice of the line each character occupies". Mapped back to page coordinates, that gives **a rectangle per character**, identical to what the text layer provides;
4. Nothing downstream changes: the 700-odd rules for numbers, names and addresses run as-is. Scans therefore behave, look and mask exactly like text-layer PDFs.

**Why "per character" matters**: most OCR returns one big box per line. Masking needs to know that an 18-digit ID is characters 3–20 of that line. With one big box, the whole line has to be blacked out — and the contract amount next to it goes with it. This step is what makes the feature possible at all.

**Models and size**: the PP-OCRv4 mobile detection and recognition pair (4.7 MB + 10.9 MB), CPU only, no discrete GPU required. OpenCV is not used — the connected-component work is done with numpy instead, saving roughly 40 MB.

**Speed** (ordinary quad-core, no tuned build):

- First model load: 0.55 s (pre-loaded while idle after launch, so clicking feels instant);
- About 0.8–1.3 s per page. Ten scanned pages take a dozen seconds, which is acceptable.

**Accuracy** (A4 form, 11 lines, 200 dpi scan, exactly 0 characters in the text layer):

- All 11 lines read **correctly**, including an 18-digit ID, a 19-digit bank card, an e-mail address, a street address and dates;
- All 8 sensitive items that should be masked **were masked**; the ones that should stay (meeting date, contract amount) were **not touched**;
- Re-running OCR on the masked output: none of the five number types can be read any more, while everything meant to stay is still legible.

**When OCR is used at all**: not on every page. Only when a page has almost no text (fewer than 24 characters), or has very little text *and* is more than half covered by images. A pure text PDF never loads a model, so its speed is unchanged.

## 2. Fixed: full-width digits and letters were missed (Windows + Android)

**Symptom**: a phone number copied in from elsewhere was not detected. It looks like `１３８００１３８０００` — visually almost identical to ordinary digits.

**Cause**: these are "full-width" characters with different code points from ordinary (half-width) digits. The digit patterns in the rules do not match them, so the whole run is skipped. The defect has always existed on the text-layer path; this release did not introduce it — full-width content is simply rare.

**Fix**: every character read from the PDF is folded to half-width before detection (`０-９`→`0-9`, `Ａ-Ｚ`→`A-Z`, ideographic space → space). One character maps to one character, so no coordinates shift. OCR output goes through the same fold — the recogniser itself frequently returns full-width digits.

## 3. UI: from "no scanned PDFs" to "scans supported" (Windows + Android)

- The small red label is now a green "scans supported", with the tooltip reading "read automatically with local OCR (offline, nothing uploaded); fall back to manual boxes if needed";
- The subtitle changed from "use the manual box tool for scans" to "scans read automatically · manual box too";
- The notice after opening a file now has four cases instead of one blanket "cannot be detected": all pages read / some pages not read / nothing read / this build has no OCR component;
- The page bar shows either "OCR read" or "no text layer", so it is obvious where the results came from.

## 4. Graceful degradation: missing components fall back to manual boxes (Windows + Android)

OCR is a soft dependency. If the model files are missing or the runtime cannot load, the app still starts, still handles text-layer PDFs, and falls back to manual boxes for scans with an explanation — it never fails to open, and never silently does nothing.

There is also a switch: on Windows, setting `PDFMASK_NO_OCR=1` disables OCR entirely (useful on very old machines if you want the previous lightweight behaviour).

## 5. Engineering: a very well-hidden packaging trap (Windows)

The built exe vanished on launch — from a terminal it exited immediately with no message at all.

It took a while to pin down: packaging pulled a very old C++ runtime (14.26) out of the Python directory, while the OCR runtime requires 14.4 or newer. A version mismatch like that **crashes outright, without even raising an exception**. The build script now substitutes the newer DLL from the system, and the build documentation lists this as a must-read warning.

## 6. Engineering: models are copied to private storage on first use (Android)

An APK is a compressed archive, and the runtime only accepts real file paths, so models cannot be read straight out of the package. The first time recognition is actually needed, the two models (about 15 MB) are unpacked from the package into the app's private directory and reused from then on.

That means **the first scan costs an extra second or two**, and the app takes about 15 MB more storage (removed on uninstall). The model files are stored uncompressed inside the APK — compressing them would add several hundred milliseconds of decompression every time.

## 7. Engineering and licensing: one more self-check, obligations covered (Windows + Android)

- `dev/selfcheck.py` gained step 15: build a form with no text layer and run the whole chain (recognise → mask → recognise again). All 15 steps pass;
- New `dev/test_ocr.py` (sample generator) and `dev/test_ocr_redact.py` (end to end);
- The OCR models and runtime are Apache-2.0 / MIT, both compatible with this project's AGPL-3.0. Licence texts, model provenance and SHA-256 live in `assets/ocr/`, and `NOTICE.md` plus the dependency table in `README` have a new entry. The model weights were not modified in any way.

## 8. Known limitations (two new ones)

- **OCR is not magic**: handwriting, heavy skew, folds and very low resolution (a 72 dpi fax, say) may be missed or misread. A misread means a missed mask — so **please glance over the result** after processing a scan. The UI says so too;
- **Only enabled on pages with almost no text**: a page that has a text layer *and* a pasted scan (a contract with an ID scan dropped in, for instance) will not use OCR. Manual boxes are still needed there;
- The following two are unchanged: Android output is still full-page images (not searchable, text not copyable); annotations are covered whole.

## 9. Downloads

Windows grew from 36.7 MB to **73.2 MB**, and Android grew from 14.9 MB to 46.8 MB. Nearly all of the increase is the two models (14.9 MB) plus the runtime for each platform (about 18.5 MB on Android). That is the unavoidable cost of local, offline recognition — and it buys **no network, no uploads**. If the size is a problem, `PDFMASK_NO_OCR=1` restores the old behaviour.

- Windows: `PDFPrivacyMasker-1.4.6.exe` (portable, no install)
- Android: `PDFPrivacyMasker-1.4.6-arm64.apk` (arm64-v8a, Android 8.0+)
- Checksums: `SHA256SUMS.txt`

Install straight over the previous version. The first scan takes an extra second or two while the models load, then about a second per page.

---

# v1.4.5 版本说明（Windows + 安卓）

**中文** | [English](#v145-release-notes-windows--android)

更新级别：建议

> **一句话**：安卓更新不再下成「.apk.zip」；默认更新源稳定走 Gitee，只有明显海外环境才用 GitHub；返回手势先问一句，能先保存再走。

这一版修的都是「用着用着才撞上」的问题：更新下载下来的安装包被浏览器加了个 `.zip`；明明默认 Gitee，更新却跑到 GitHub 去读；还有全面屏手势往边上一滑，应用直接没了，刚框好还没保存的东西全丢。三条都在这版里堵住了。

---

## 1. 修复：安卓更新下到的包变成「.apk.zip」，装不上（安卓）

**现象**：在应用里点「立即更新」，跳去浏览器下载，下载完文件名变成 `PDFPrivacyMasker-1.4.4-arm64.apk.zip`，点开装不了；而去发布页手动点下载又是正常的 `.apk`。

**原因不在文件本身**。Gitee 的附件 CDN 对 `.apk` 返回的类型是 `application/zip`（同一个仓库的 `.exe` 返回的是 `application/vnd.microsoft.portable-executable`，是正常的）。APK 本来就是 zip 容器，字节完全一致，只是类型标注错了；浏览器按类型命名，就给它补了一个 `.zip`。这是服务器端的类型标注问题，客户端改不了。

**改法**：不再把安装包交给浏览器。

1. 应用自己下载到应用缓存目录，文件名由我们自己定，永远是 `.apk`；
2. 下完先核对四件事：头 4 字节是 `PK`、大小和服务器给的一致、包名是 `com.neurotracee.pdfmask`、版本号等于这次要装的版本——任何一项不对就当失败处理，绝不让用户去装一个看不懂的文件；
3. 校验通过后交给系统安装器，系统会再问一次「是否安装」，你不点就不会装；
4. 装完或取消后缓存的安装包会被清掉。

浏览器那条路还留着（「用浏览器下载」），万一应用内下载被网络拦了还能走，旁边写明了「文件末尾被加了 .zip 就把 .zip 去掉」。

因为多了这一步，安卓端新增了一个「安装应用」权限（`REQUEST_INSTALL_PACKAGES`），只用于把下载好的新版本交给系统安装器，不联网、不读任何文件。清单里的权限说明已同步更新。

## 2. 修复：默认更新源会莫名其妙跑到 GitHub（Windows + 安卓）

**现象**：明明没手动选过 GitHub，默认就是 Gitee，但启动时的更新检查却从 GitHub 读；把窗口关掉再看，又变回 Gitee 了。

**有两个原因，都在判断逻辑上**：

- 判断「该不该用 Gitee」时把**界面语言**当成了「用户人在哪里」——界面切成英文就判定为海外，直接去 GitHub。可用户只是换了个界面语言。
- 安卓端每次调用都现读进程默认的语言环境。这个值在应用刚启动、系统配置还没应用时可能还是英文，界面渲染完之后才变成中文，于是同一个「自动」在启动那一刻判成 GitHub，过一会儿又变回 Gitee——就是用户看到的「一进来 GitHub、关掉窗口又 Gitee」。

**改法**：

- 判断只看系统本身，**界面语言不再参与**；
- 启动时算一次就固定下来，全程一致，不再抖动；
- 规则改成：中文系统 → Gitee；语言不是中文但时区在东八区（中国大陆、中国港澳台、新加坡等）→ 仍然 Gitee；只有「语言不是中文 + 时区也不在东八区」这种明确的海外环境才用 GitHub；任何一项取不到，一律按 Gitee 兜底；
- 单个通道的超时从 8 秒放宽到 10 秒（安卓 10 / 12 秒）：移动网络首包稍慢就会被判死，一超时就静默换下一个通道，用户只看到来源莫名其妙变了；
- 真的发生自动换源时，界面上会写明「Gitee 这次没连上，已经自动改用 GitHub」，不再让人猜。

`dev/test_source_pick.py` 把这几条规则钉成了用例（含「界面语言是英文也不该把中文用户赶到 GitHub」），并进了主自检第 14 项。

## 3. 新增：安卓按返回 / 左右滑手势，先问一句再离开（安卓）

**现象**：文件已经选好、框也画好了，手一滑从屏幕边缘返回，应用直接退到桌面——没保存的东西全没了，也没有任何挽回的机会。

**改法**：工作区里还有文件时，返回键和全面屏手势都会被接住，弹一个小窗口，给三个出口：

- **继续编辑**（主按钮，默认最安全）；
- **保存后离开**：只有已经打出结果时才出现，存完再回主页；
- **直接离开**：回到应用主页（不是杀进程），随时能重新选文件。

按返回不再等于「退出应用」：第一下返回是回主页，在主页再返回才是退出。

## 4. 改进：Windows 关标签页前也会提醒（Windows）

Windows 版是本地页面 + 默认浏览器，没有原生窗口可以拦，所以用的是浏览器唯一允许的方式：工作区里开着文件时，关标签页或刷新会先弹浏览器的「确定要离开吗」。文案由浏览器决定、改不了，但足够避免手一滑把刚框好的选区关掉。

另外，Windows 端的更新弹窗也补上了「本次从 Gitee / GitHub 读取」以及自动换源的说明。

## 5. 工程：自检新增默认更新源回归

- 新增 `dev/test_source_pick.py`：中文系统、非中文但东八区、明确海外、环境取不到、界面语言干扰、手动指定优先级，六组用例；
- 接进 `dev/selfcheck.py` 第 14 项，和前面的正文解析、注释/书签回归一起跑；
- 顺带把 `UPDATE_TIMEOUT` 的注释写清楚，说明为什么是 10 秒。

## 6. 已知限制（未变）

- 安卓端的输出仍是整页图片（JPEG 重绘再组装），打码后不能搜索、不能复制文字，体积通常更大；Windows 版保留矢量版面，只抹掉命中处的文字层。
- 注释是整块盖掉的：一条注释里既有敏感内容又有需要保留的说明时，整条都会没。

## 7. 下载

- Windows：`PDFPrivacyMasker-1.4.5.exe`（免安装，双击即用）
- 安卓：`PDFPrivacyMasker-1.4.5-arm64.apk`（arm64-v8a，Android 8.0+）
- 校验和：`SHA256SUMS.txt`

升级不用卸载旧版，直接覆盖安装即可。**安卓从 v1.4.3 / v1.4.4 升上来时**，如果下载到的文件名末尾被加了 `.zip`，那是旧版本还在走浏览器下载，把结尾的 `.zip` 去掉就能安装；装上这一版之后就不会再出现了。

---

# v1.4.5 Release Notes (Windows + Android)

[中文](#v145-版本说明windows--安卓) | **English**

Update level: suggested

> **In one line**: Android updates no longer arrive as “.apk.zip”; Gitee stays the default update source; the back gesture now asks before discarding unsaved work.

Everything fixed here is something you only hit after using the app for a while: the downloaded installer picked up a `.zip` suffix, updates went to GitHub even though Gitee is the default, and a swipe from the screen edge closed the app with unsaved work still in it. All three are closed in this build.

---

## 1. Fixed: Android downloads arrived as “.apk.zip” and would not install (Android)

**Symptom**: tapping “Update now” opened a browser, and the downloaded file was named `PDFPrivacyMasker-1.4.4-arm64.apk.zip` — uninstallable. Downloading the same file from the release page by hand produced a normal `.apk`.

**The file was never the problem.** Gitee's attachment CDN serves `.apk` with the type `application/zip` (the same repository's `.exe` comes back as `application/vnd.microsoft.portable-executable`, which is correct). An APK is a zip container, so the bytes are identical — only the type label is wrong, and browsers name the file after the type. That is a server-side labelling problem the client cannot fix.

**Fix**: stop handing the download to the browser.

1. The app downloads the file itself into its own cache directory and names it, so the extension is always `.apk`;
2. Four checks before anything is installed: the first four bytes are `PK`, the byte count matches the server's, the package name is `com.neurotracee.pdfmask`, and the version equals the one being installed. Any mismatch is treated as a failure — never ask the user to install an unknown file;
3. The system installer then asks you to confirm; nothing installs unless you tap it;
4. The cached installer is removed after installing or cancelling.

The browser route stays as a fallback (“Browser”), with a note that a trailing `.zip` just needs deleting.

This adds one Android permission (`REQUEST_INSTALL_PACKAGES`), used only to hand a verified installer to the system. It does not go online and reads no files. The permission notes in the manifest were updated to say so.

## 2. Fixed: the default update source kept landing on GitHub (Windows + Android)

**Symptom**: GitHub was never selected by hand and Gitee is the default, yet the update check at launch read from GitHub — and after closing that window it showed Gitee again.

**Two causes, both in the decision logic**:

- The “should this be Gitee?” check treated the **interface language** as “where the user is”. An English interface was read as “abroad” and sent the check to GitHub. The user had only changed the interface language.
- On Android the check re-read the process-default locale on every call. Right at launch, before the system configuration is applied, that value can still be English and only becomes Chinese after the UI renders — so the same “auto” decision was GitHub at that instant and Gitee a moment later. That is exactly the “GitHub on launch, Gitee after closing the window” behaviour.

**Fix**:

- The decision looks only at the system, **the interface language no longer takes part**;
- It is computed once at launch and cached, so it cannot flip mid-session;
- The rule: Chinese system → Gitee; non-Chinese but UTC+8 (mainland China, Hong Kong/Macao/Taiwan of China, Singapore, etc.) → still Gitee; GitHub only when the language is non-Chinese **and** the time zone is not UTC+8; if either cannot be determined, Gitee is the fallback;
- Per-channel timeout went from 8s to 10s (Android 10s connect / 12s read): a slow first packet on mobile data used to be judged as dead and silently fell through to the next channel;
- When a fallback does happen, the UI now says “Gitee could not be reached, so GitHub was used” instead of leaving the user to guess.

`dev/test_source_pick.py` pins these rules (including “an English interface must not push Chinese users to GitHub”) and runs as step 14 of the main self-check.

## 3. New: the back button / edge swipe asks before leaving (Android)

**Symptom**: file loaded, boxes drawn, one swipe from the screen edge — the app closed and the unsaved work was gone, with no chance to save.

**Fix**: while a file is open, both the back button and the full-screen gestures are caught, and a small dialog offers three ways out:

- **Keep editing** (primary, the safe default);
- **Save, then leave** — only shown once a masked result exists; it saves first, then returns;
- **Leave anyway** — returns to the app's home screen (not a process kill), where another file can be picked.

Back no longer means “exit”: the first back goes to the home screen, and back from there exits.

## 4. Improved: Windows warns before the tab is closed (Windows)

The Windows build is a local page in your default browser, with no native window to intercept, so it uses the only mechanism browsers allow: while a file is open, closing or reloading the tab raises the browser's “leave this page?” prompt. The wording is the browser's and cannot be customised, but it does prevent a stray close from discarding your selection.

The Windows update dialog also now says which source the result came from, and when a fallback happened.

## 5. Engineering: a regression suite for the default update source

- New `dev/test_source_pick.py`: six groups — Chinese system, non-Chinese in UTC+8, clearly abroad, undeterminable environment, interface-language interference, explicit choice wins;
- Wired into `dev/selfcheck.py` as step 14, alongside the release-body and annotation/bookmark suites;
- `UPDATE_TIMEOUT` is documented, so nobody "optimises" it back to 8s.

## 6. Known limitations (unchanged)

- Android output is still full-page images (JPEG re-render, then assembled): the masked PDF is not searchable, its text cannot be copied, and it is usually larger. The Windows build keeps the vector layout and removes only the text layer at the hits.
- Annotations are covered whole: if one annotation mixes sensitive content with text worth keeping, the whole annotation goes.

## 7. Downloads

- Windows: `PDFPrivacyMasker-1.4.5.exe` (portable, no install)
- Android: `PDFPrivacyMasker-1.4.5-arm64.apk` (arm64-v8a, Android 8.0+)
- Checksums: `SHA256SUMS.txt`

Install straight over the previous version. **When upgrading from v1.4.3 / v1.4.4 on Android**, a trailing `.zip` on the downloaded file means the old build still used the browser — delete the `.zip` and it installs. After this build it no longer happens.

---

# v1.4.4 版本说明（Windows + 安卓）

**中文** | [English](#v144-release-notes-windows--android)

更新级别：建议

> **一句话**：注释和书签里只出现的姓名地址不再漏打；安卓注释文字改成整块马赛克；4 位一组的银行卡认得出；座机号在列表里也遮住了；更新弹窗先给一句话摘要，再按 Windows / 安卓分开列详细。

这一版补掉上一版留下的三处同类残口：注释和书签里**只出现**姓名或地址时不再漏打；安卓端注释里的文字会被渲染成像素、原来永远打不到，现在按注释矩形整块盖马赛克；顺带把「4 位一组」印法的银行卡号纳入识别，并修正座机号在列表里没有遮挡的问题。校验和文件这次也一起挂到发布页了。

---

## 1. 修复：注释和书签里独自出现的姓名、地址会漏（Windows）

上一版清洗注释和书签时，只把「正文已经命中的值」当匹配表。问题是注释和书签是独立对象——正文里压根没出现过的姓名、地址，根本不会进这张表，于是原样留着：

```
书签: 附件：赵子墨 体检报告                ← 没打
注释: 复核：赵子墨 江苏省苏州市姑苏区干将东路88号   ← 整条保留
```

现在把注释的正文 / 主题 / 标题、以及书签标题本身，直接喂给行内识别器（`_scan_line`）跑一遍，号码、姓名、地址、出生日期都能就地认出来，不再依赖正文命中：

```
书签: 附件：赵** 体检报告
注释: 整条删除（注释的弹出内容、作者名都可能带残留，改一半容易漏）
```

姓氏仍然保留，干净的书签和注释不动。

## 2. 修复：安卓端注释里的文字会变成像素，永远打不到（安卓）

安卓打码是「整页渲染成位图 → 在命中处做马赛克 → 重组成新 PDF」。注释对象确实不会跟着进新文件，但 **PdfRenderer 渲染整页时会把注释一起画进位图**：FreeText（自由文本）和高亮附言里的号码，就在渲染那一刻变成了像素，正文文字识别永远看不到它们。

所以上一版发布说明里那句「安卓整页重绘、注释不会带过去，无需改动」不准确，这里更正：普通便签通常只剩一个小图标，风险低；FreeText 是实打实会漏的。

修法是打码时先用 PDFBox 读出每页注释的内容、主题和标题，命中敏感内容就把该注释的矩形整块做像素马赛克（页面带 `/Rotate` 时按顺时针角度换算到渲染方向），结果里统计为「注释」。宁可整块盖掉，也不去猜注释内部的字形位置——注释的排版由阅读器决定。

## 3. 新增：认得出「4 位一组」印法的银行卡号（Windows + 安卓）

真实卡面和银行回单几乎都是 `6222 0212 3456 7890` 这种 4 位一组的写法，原来只认连续 16~19 位数字，整串被漏掉。现在两种写法都认，去掉分隔符后仍然要过 Luhn 和「至少 5 种不同数字」两道校验，所以订单号之类的不会被误判（实测「订单号 2026 1112 3344 5566」不打码）。另外标签兜底里补上了「银行卡 / 储蓄卡 / 信用卡」这几种写法。

## 4. 修复：座机号在列表里没有被遮住（Windows + 安卓）

掩码函数里没有座机号分支，`0512-66881234` 会原样显示在结果列表和注释打码里。现在与手机号一致：`0512****1234`。

## 5. 工程：注释 / 书签回归并进主自检

- `dev/test_scrub_notes.py` 增加了「正文里没有、只在注释或书签里出现」的姓名和地址用例，正好是这次修的那一类；
- `dev/selfcheck.py` 主流程新增第 12 项，自动跑上面那套注释/书签用例——以前只靠单独执行，改别的地方时容易忘。

## 6. 改进：更新弹窗先给一句话，再按平台列详细（Windows + 安卓）

检查更新的弹窗（启动时自动检查、设置里手动检查，两个都一样）现在分成三层：

1. **一行摘要**：取自发布页正文里那句「一句话」，控制在 100 字内，只说最要紧的几条；
2. **详细条目**：按 Windows / 安卓 分开标注，可以上下翻看，不用跳出去；
3. **末尾一条「具体详见 Release 页面」**：想看全文点这里。

摘要是从仓库的发布页正文里读的，不是写死在程序里——以后发版只要正文里带上那行「一句话」，弹窗自动就跟着变；正文没写也不会报错，弹窗就和以前一样。

## 7. 已知限制（补充说明）

- **安卓端的输出是图片**：整页重绘为 JPEG 再组装，所以打码后的 PDF 不能搜索、不能复制文字，体积通常也比原文件大；Windows 版保留矢量版面、只抹掉命中处的文字层。这是为了「彻底抹除文字层」有意做的取舍，之前的发版说明没有写清楚，这次补上。
- 注释是整块盖掉的：如果一条注释里既有敏感内容、又有需要保留的说明，那整条都会没。想保留就单独再写一条干净注释。

## 8. 下载

- Windows：`PDFPrivacyMasker-1.4.4.exe`（免安装，双击即用）
- 安卓：`PDFPrivacyMasker-1.4.4-arm64.apk`（arm64-v8a，Android 8.0+）
- 校验和：`SHA256SUMS.txt`（这次随发布一起上传）

升级不用卸载旧版，直接覆盖安装即可。

---

# v1.4.4 Release Notes (Windows + Android)

[中文](#v144-版本说明windows--安卓) | **English**

Update level: suggested

> **In one line**: Annotation and bookmark leaks fixed; Android comment text now mosaicked; grouped bank cards and landlines covered; the update dialog now leads with a one-line summary and splits the details by platform.

This release closes the three related gaps left by the previous one: names and addresses that appear **only** inside annotations or bookmarks are no longer missed; on Android, text inside annotations was being rendered into pixels and could never be masked, so those annotation boxes are now mosaicked whole; on top of that, bank cards printed in groups of four are now detected, and landline numbers are masked in the result list. The checksum file is attached to the release this time as well.

## 1. Fixed: names and addresses that only appear in annotations or bookmarks (Windows)

The previous release scrubbed annotations and bookmarks by reusing only the values already found in the body text. Annotations and bookmarks are separate objects, so a name or address that never appeared in the body was not in that list and stayed untouched:

```
bookmark: 附件：赵子墨 体检报告                <- not masked
annotation: 复核：赵子墨 江苏省苏州市姑苏区干将东路88号   <- kept as is
```

The scrubber now feeds the annotation's contents / subject / title and the bookmark title through the same line scanner used for the body (`_scan_line`), so numbers, names, addresses and birth dates are recognised in place, with no dependency on the body:

```
bookmark: 附件：赵** 体检报告
annotation: deleted entirely (popup contents and author name can carry leftovers; a partial rewrite is easy to get wrong)
```

Surnames are still preserved, and clean bookmarks/annotations are left alone.

## 2. Fixed: text inside annotations became pixels on Android and was never masked (Android)

Android redaction renders each page to a bitmap, mosaics the hits, then assembles a new PDF. The annotation objects themselves do not carry over — but **PdfRenderer draws annotations into that bitmap**. A phone number inside a FreeText annotation or a highlight note becomes pixels at render time, so text detection can never see it.

That makes the previous release note ("Android re-renders the page, annotations never make it into the output — nothing to fix there") inaccurate. Correcting it: a plain sticky note usually leaves only a small icon, which is low risk; FreeText genuinely leaks.

The fix reads each page's annotation contents, subject and title with PDFBox before masking, and mosaics the annotation's whole rectangle when it contains sensitive content (converted for `/Rotate` when present); the tally shows up as "Comment". Covering the whole box beats guessing where the glyphs sit inside an annotation — its layout is up to the reader.

## 3. New: bank cards printed in groups of four (Windows + Android)

Real cards and bank receipts almost always read `6222 0212 3456 7890`; only contiguous 16–19 digit runs were detected before, so the whole number was missed. Both forms are accepted now, and the digits still have to pass Luhn plus the "at least 5 distinct digits" check, so order numbers are not flagged (measured: `订单号 2026 1112 3344 5566` stays untouched). The label fallback also accepts 银行卡 / 储蓄卡 / 信用卡.

## 4. Fixed: landline numbers were not masked in the result list (Windows + Android)

The masking helper had no landline branch, so `0512-66881234` was displayed verbatim in the result list and in annotation scrubbing. It now matches the mobile rule: `0512****1234`.

## 5. Engineering: annotation/bookmark regression joined the main self-check

- `dev/test_scrub_notes.py` gained cases for names and addresses that appear only inside annotations or bookmarks — exactly the gap fixed here;
- `dev/selfcheck.py` gained step 12, which runs that suite automatically. Previously it was a separate script and easy to forget.

## 6. Improved: the update dialog leads with one line, then lists details per platform (Windows + Android)

The update dialog (both the automatic check at launch and the manual one under Settings) now has three layers:/n/n1. **A one-line summary** — taken from the “In one line” line in the release body, kept under 100 characters, only the changes that matter most;
2. **Detailed items** — tagged Windows / Android, scrollable in place, no need to leave the app;
3. **“Full notes on the release page”** at the bottom — click through for everything.

The summary is read from the release page body at runtime, not hard-coded: keep that line in the release notes and the dialog follows automatically. If a release omits it, nothing breaks — the dialog looks like it used to.

## 7. Known limitations (added)

- **Android output is images**: pages are re-rendered as JPEG and assembled, so the redacted PDF is not searchable, its text cannot be copied, and the file is usually larger. The Windows build keeps the vector layout and only removes the text layer at the hits. This is a deliberate trade for wiping the text layer, and earlier release notes never spelled it out — now they do.
- Annotations are covered as a whole: if one annotation holds both sensitive content and text worth keeping, the entire annotation goes. Write a separate clean note in that case.

## 8. Downloads

- Windows: `PDFPrivacyMasker-1.4.4.exe` (portable, no install)
- Android: `PDFPrivacyMasker-1.4.4-arm64.apk` (arm64-v8a, Android 8.0+)
- Checksums: `SHA256SUMS.txt` (uploaded with the release this time)

You can install straight over the previous version.

# v1.4.3 版本说明（Windows + 安卓）

更新级别：建议

**一句话结论**：这一版对着豆包 AI 在云端 Linux 沙箱里实测出的问题清单逐条核实——真实存在的全部修掉，判断有误的也写明理由。更新器不再放宽证书校验、只认官方下载域名；检查方式（自动/手动）和更新源（Gitee/GitHub）都能自己选，默认按环境走 Gitee；打码时连 PDF 注释和书签标题也一起清洗；跨年后身份证不会因为年份上限写死而漏打。工程上拆了 4000 行的单文件，并加了跨端一致性测试。

---

## 1. 安全：更新器不再接受不可信的下载地址

- **删掉了放宽证书校验的兜底分支。** 旧版在直连失败时会用 `ssl.CERT_NONE` 再试一次，等于放弃证书验证——链路上只要有人做中间人，返回的 JSON 就能把「下载地址」换成任意站点。现在只有严格校验一条路，失败就如实报错（提示里会显示是哪个通道、什么原因）。
- **新增下载域名白名单。** GitHub 的发布资产只认 `github.com` / `objects.githubusercontent.com` / `release-assets.githubusercontent.com` / `codeload.github.com`，Gitee 只认 `gitee.com`（含子域）。白名单外的地址一律不使用，只给发布页链接。安卓端同样加了一份白名单。

## 2. 新增：更新方式和更新源都能自己选（Windows + 安卓）

设置里多了两个选项，两端界面一致：

- **检查方式**：「自动检查（启动时）」/「手动检查」。选自动，每次启动在后台静默查一次，没网就跳过；选手动，只有点「检查更新」才联网，平时一个请求都不发。
- **更新源**：「Gitee（建议中国大陆用户）」/「GitHub」。默认值按环境判断：

| 环境 | 默认源 |
| --- | --- |
| 简体中文系统 + 中文界面 | Gitee |
| 明确是其他语言 | GitHub |
| 语言取不到、判断失败 | Gitee（兜底） |

判断依据是系统界面语言（Windows 读 `GetUserDefaultUILanguage`，安卓读 `Locale`）加软件内语言设置。选中的源连不上时会自动换另一个再试，不会因为选错源就查不了更新；系统代理是坏配置（指向已失效的端口）时，每个通道还会再直连试一次——这一步只换连接方式，证书校验始终严格。窗口标题里会标出这次结果来自哪个通道。

## 3. 隐私：注释与书签也一起清洗（Windows）

正文打码用的是「抹除文本层 + 贴马赛克」，碰不到 PDF 的注释（批注、便签、高亮附言）和书签标题——这两类是独立对象，内容会原样留在成品里，和 README 里「文字层一并抹除」的说法确实矛盾。现在 `redact()` 末尾会再洗一遍：

- **注释**：内容 / 标题 / 主题里出现手机号、身份证、银行卡、邮箱、座机，或本次正文已命中的姓名、地址 → 整条删除（改一半容易漏，尤其是回复串）。
- **书签**：标题按同一套规则打码（`第一章 联系人 13812346780` → `第一章 联系人 138****6780`），层级和目标页保持不变，条数不变。
- 干净的注释和书签不受影响。

安卓端本来就是按页重绘成图片再组装新 PDF，注释和书签天然不会带过去，无需改动。

## 4. 修复：跨年后身份证会漏打

身份证合理性校验里把出生年份上限写死成了 `2026`（Python 和 Kotlin 各一处）。跨年之后，当年出生的号码会被判成「不合法」而漏打。现在改成跟随系统时钟取当前年份。

## 5. 工程改动

- **声明里补上 Gitee 镜像地址**：关于窗口、首页页脚、`--about` 输出、`NOTICE.md` 和附加条款里出现的 GitHub 地址，都并列了 `gitee.com/bio234/pdf-privacy-masker`。国内打不开 GitHub 时，使用者和二次开发者仍然能追溯到出处。
- **拆分了单文件**：`pdfmask.py` 从 4077 行降到 2644 行。首页那一整页 HTML/CSS/JS 移到 `pdfmask_webui.py`，检查更新移到 `pdfmask_update.py`。打包仍是单文件 exe，行为不变。
- **新增跨端一致性测试**：`test/rules_golden.json` 存的是 Python 端在同一份样张上的识别结果，安卓单元测试 `RuleParityTest` 用 PDFBox 读同一份 PDF、跑 Kotlin 的 `Detector`，逐条比对 `page/type/text`。任何一端改了规则没同步，测试立刻失败。
- **测试产物不再污染工作区**：`selfcheck.py` 及其调用的生成脚本统一写到临时目录（可用 `PDFMASK_TEST_DIR` 指定），跑完 `git status` 是干净的。
- **Kotlin 正则提前编译**：`Detector` 里循环内反复 `Regex(...)` 的两处改为对象级常量。
- **马赛克种子**：`hash((page, y))` 实测跨进程稳定（整数/浮点的 hash 不受 `PYTHONHASHSEED` 影响），没有改动；已加注释说明，避免以后被误判成随机种子。

## 6. 下载

- Windows：`PDFPrivacyMasker-1.4.3.exe`（免安装，双击即用）
- 安卓：`PDFPrivacyMasker-1.4.3-arm64.apk`（arm64-v8a，Android 8.0+）

安装包 SHA256 见 `SHA256SUMS.txt`。升级不用卸载旧版，直接覆盖安装即可。

---

# v1.4.3 Release Notes (Windows + Android)

Update level: suggested

**TL;DR** — this release works through the list of issues Doubao AI reported after testing the app in a cloud Linux sandbox: every real issue is fixed, and the few that were not are explained below. The updater no longer relaxes TLS verification and only accepts download links from the official release hosts; both the checking mode (automatic / manual) and the update source (Gitee / GitHub) are now user-selectable, defaulting to Gitee by environment; redaction also scrubs PDF annotations and bookmark titles; the hard-coded year cap that leaked ID numbers after New Year is gone. On the engineering side, the 4,000-line single file was split up and a cross-platform parity test was added.

## 1. Security: the updater refuses untrusted download URLs

- **Removed the `ssl.CERT_NONE` fallback.** The old code retried with certificate verification disabled, which is exactly what a man-in-the-middle needs to swap the "download URL" in the JSON response. Only strict verification is used now; on failure it reports the channel and the reason.
- **Download host allowlist.** GitHub assets are only accepted from `github.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com` and `codeload.github.com`; Gitee only from `gitee.com` (and subdomains). Anything else falls back to the release page. Same rule on Android.

## 2. New: pick how and where updates are checked (Windows + Android)

Two new settings, identical on both platforms:

- **Checking mode**: "Automatic (at launch)" / "Manual only". Automatic runs one silent check at startup and skips it when offline; manual sends nothing at all until you press "Check for updates".
- **Update source**: "Gitee (recommended in mainland China)" / "GitHub". The default follows the environment:

| Environment | Default source |
| --- | --- |
| Simplified Chinese system + Chinese UI | Gitee |
| Clearly another language | GitHub |
| Language unavailable / detection failed | Gitee (fallback) |

The decision uses the system UI language (Windows: `GetUserDefaultUILanguage`; Android: `Locale`) plus the in-app language setting. If the chosen source cannot be reached, the other one is tried automatically, so picking the "wrong" source never blocks updates. When the system proxy is a stale broken config, each channel also gets one direct-connect retry — that only changes the route, certificate verification stays strict. The result card shows which channel answered.

## 3. Privacy: annotations and bookmarks are scrubbed too (Windows)

Redaction only covered page text; annotations (comments, sticky notes, highlight notes) and bookmark titles are separate objects and used to survive untouched, contradicting the README's "text layer erased as well". `redact()` now also:

- **Deletes annotations** whose content / title / subject contains a phone number, ID number, bank card, email, landline, or a name/address already matched in the text.
- **Masks bookmark titles** with the same rules (`Contact 13812346780` → `Contact 138****6780`), keeping level, target page and count unchanged.
- Leaves clean annotations and bookmarks alone.

Android renders each page to a bitmap and assembles a new PDF, so annotations and bookmarks never make it into the output — nothing to fix there.

## 4. Fixed: ID numbers leaking after New Year

The plausibility check capped birth year at `2026` (one place in Python, one in Kotlin), so IDs of people born in the new year were rejected and therefore not masked. It now follows the system clock.

## 5. Engineering

- **Gitee mirror added to every attribution spot**: the About window, footer, `--about` output, `NOTICE.md` and the additional terms now list `gitee.com/bio234/pdf-privacy-masker` next to the GitHub URL, so users and downstream developers can still trace the origin when GitHub is unreachable.
- **Single file split**: `pdfmask.py` went from 4,077 to 2,644 lines; the web UI moved to `pdfmask_webui.py`, the update logic to `pdfmask_update.py`. The packaged app is still a single exe.
- **Cross-platform parity test**: `test/rules_golden.json` holds the Python results on a fixed sample; the Android `RuleParityTest` reads the same PDF with PDFBox, runs the Kotlin `Detector` and compares `page/type/text` item by item.
- **Test output no longer pollutes the work tree**: `selfcheck.py` writes to a temp directory (`PDFMASK_TEST_DIR` to override).
- **Kotlin regexes hoisted** out of loops in `Detector`.
- **Mosaic seed**: `hash((page, y))` is in fact stable across processes (int/float hashing is not affected by `PYTHONHASHSEED`), so it was left as is with a comment.

## 6. Downloads

- Windows: `PDFPrivacyMasker-1.4.3.exe` (portable, no install)
- Android: `PDFPrivacyMasker-1.4.3-arm64.apk` (arm64-v8a, Android 8.0+)

SHA256 sums in `SHA256SUMS.txt`. You can install straight over the previous version.

---

# v1.4.2 版本说明（Windows + 安卓）

> 最新一版在最上面。要发版就照这一节写 Release 正文，历史版本原样往下翻。
> 文档地图看 [DOCS.md](DOCS.md)，发版步骤看 [docs/06](docs/06-发布Release操作指南.md)。

**一句话结论**：这一版把「检查更新」从手动变成自动——打开程序就查一次，有新版本直接用默认浏览器打开下载页；网络不通就静默跳过，绝不影响你打码；更新窗口全程都能关，关之前最多劝你一句（建议 / 强烈建议两档，都不拦路）。顺便在赞赏码那一页加了「给仓库点个 Star」，不想花钱也有表达支持的方式。

---

## 1. 新增：打开即自动检查更新（双端）

| | 安卓 | Windows |
| --- | --- | --- |
| 触发时机 | 每次冷启动 `AppRoot` 时 | 每次打开主窗口、页面脚本加载完时 |
| 用的是哪套逻辑 | 与「设置 → 检查更新」同一个 `Updater.check()` | 与手动检查同一个 `/api/check_update` |
| 发现新版本 | 自动 `ACTION_VIEW` 调用系统默认浏览器打开发布页 | 自动 `webbrowser` 打开默认浏览器 |
| 备选路径 | 窗口里同时给「用浏览器下载」「复制链接」 | 窗口里同时给「用浏览器下载」「复制链接」 |
| 已是最新 | 什么都不显示 | 什么都不显示 |
| 断网 / 超时 / 没有适用安装包 | 静默跳过，直接进主程序 | 静默跳过，直接进主程序 |
| 网络慢 | 1.2 秒还没结果才弹提示，右上角可关 | 同左 |

手动检查没有删除，位置还是「设置 → 版本与更新 → 检查更新」，两种方式共用同一套版本解析。

## 2. 新增：卡住能跑，全程可关

自动检查最怕的是「网络半通不通、转圈转到天荒地老」。这一版给了三道保险：

1. **单次请求 8 秒超时**：`connectTimeout` / `readTimeout` 都是 8 秒（Windows 是 `UPDATE_TIMEOUT = 8`）。
2. **总预算 12 秒**：超过就当作卡住，直接给「进入主程序」；安卓端另有一个「跳过，先进入」。
3. **任何时候都有出口**：检查中窗口右上角有 ×；超时窗口有「进入主程序」；发现新版本的窗口有「暂不更新」，点了也一定能关掉。

没有「不更新就不给用」这一档，原因很简单：工具的优先级永远是「先把活干完」。提醒方式见第 3 节。

## 3. 新增：建议更新 / 强烈建议更新两档（双端，都能关）

更新级别由**发布正文**决定，客户端只认一个标记：

| 正文里写 | 客户端表现 |
| --- | --- |
| `更新级别：强烈建议` | 橙红徽标 + 「强烈建议更新到 vX」；点「暂不更新」先弹一次挽留话术 |
| `更新级别：建议` | 蓝色徽标 + 「发现新版本 vX」；点「暂不更新」同样先挽留一次，语气更轻 |
| 什么都没写 | 按**建议**处理 |

**两档都能关**：窗口右上角一直有 ×，挽留只有一次——第一次点「暂不更新 / 以后再说 / ×」给一段挽留话术，再点「我还是要用旧版（先这样，下次再说）」就真的放行，不会再拦。

早期版本用过的隐藏注释 `<!-- update:force -->` 仍然认，但只降级成「强烈建议」，不再锁人——历史 Release 正文不用改也不会突然卡住谁。

**刻意不做的判断**：正文里单独出现「强烈建议」几个字**不算**标记。正文里难免会写「强烈建议先备份原文件」这种句子，用它当关键词会误判，所以只认行首的完整标记。

## 4. 新增：赞赏页加「给仓库点 Star」+ 国内赞赏入口（双端）

| 位置 | 加了什么 |
| --- | --- |
| 安卓「关于与开源信息」 | 「星标仓库 = 最好的支持」卡片 + 「去点 Star」按钮；下面才是「国内用户：微信扫码，请我喝杯奶茶」与赞赏码；赞赏码下方新增「保存赞赏码」按钮（长按依然有效） |
| Windows「关于」 | 同样的 Star 卡片与按钮；赞赏码上方加了「国内用户：微信扫码，请我喝杯奶茶（金额随意）」一行 |

「去点 Star」直接打开发布仓库首页，打不开浏览器时自动把地址复制到剪贴板并提示。

## 5. 版本号

| 项目 | 上一版 | 本版 | 安装包 |
| --- | --- | --- | --- |
| Windows | 1.4.1 | **1.4.2** | `PDFPrivacyMasker-1.4.2.exe` |
| 安卓 | 1.4.1 | **1.4.2**（versionCode 9） | `PDFPrivacyMasker-1.4.2-arm64.apk` |

两端继续共用同一个版本号 —— 自动检查会读「本平台最新包」，两端同时发才不会出现「提示有新版本、点开只能下到另一种格式」的尴尬。

## 6. 验证情况

- 安卓：`testDebugUnitTest` / `testReleaseUnitTest` 全量通过，含更新级别标记解析 3 例（识别、不误判、跟随最新版本）。
- Windows：`python dev/make_ui_preview.py` + Edge 无头渲染，核对「建议更新 / 强烈建议更新 / 检查中卡住 / 两档挽留」五个状态的中文界面；`node --check` 校验内嵌前端 JS；`dev/smoke_exe.py` 跑通打包后的 exe。
- **如实说明**：自动检查的真实联网行为没法在这台机器上完整复现（GitHub 访问受限），验证的是「解析 + 分支 + 界面」这三段；真机上第一次启动的表现请你亲自看一次。

## 7. 发版时怎么标级别

在 Release 正文**最上面**加一行：

- 建议更新：`更新级别：建议`
- 强烈建议更新：写成 `更新级别：强烈建议`

两档都能关，强烈建议只是提醒更醒目、关之前多劝一句。正文里没有这一行时一律按建议处理。这一行同时给两个平台读，不用分开写。

## 8. 顺手修掉：Windows 端手动检查其实一直是 404

做自动检查时发现的：前端调 `/api/check_update` 用的是 GET，可这个接口当初只注册在 POST 分支里，所以 Windows 端点「检查更新」拿到的永远是 `HTTP 404`，界面上表现为「检查失败 · 请求失败 (404)」——很容易被当成网络问题。

这一版给同一个地址补上了 GET 分支（POST 仍然保留），手动和自动走的是同一条路。**这是这一版唯一一个「修老问题」性质的改动**，其余都是新增。

## 9. 升级须知

- 安卓可覆盖安装（同签名、versionCode 递增）。
- Windows 换 exe 即可，配置文件与保存位置设置都保留。
- 自动检查只读一个公开版本号，不上传文件；断网时它连提示都不会有，不影响离线使用。

---

# v1.4.1 版本说明（Windows + 安卓）

> 最新一版在最上面。要发版就照这一节写 Release 正文，历史版本原样往下翻。
> 文档地图看 [DOCS.md](DOCS.md)，发版步骤看 [docs/06](docs/06-发布Release操作指南.md)。

**一句话结论**：上一版关于页写着「长按图片可保存」，实际上那张赞赏码压根没接长按手势，按下去毫无反应。这一版把保存真正做出来了——安卓长按存进相册，Windows 加了一个看得见的「保存赞赏码」按钮。

---

## 1. 修复：赞赏码长按无反应（安卓）

| | 说明 |
| --- | --- |
| 现象 | 关于页文案写「微信扫码 · 金额随意 · 长按图片可保存」，但长按没有任何反馈，也存不下来。 |
| 原因 | 那张图就是一个纯静态 `Image`，`Modifier` 上从来没挂过长按手势。文案是 1.4.0 写死的，功能没跟上。 |
| 现在 | 长按立刻有触觉反馈，并把二维码存进相册 `Pictures/PDFPrivacyMasker/PDFPrivacyMasker-赞赏码.png`，底部弹一条「已保存到相册：…」提示。 |
| Android 8 / 9 | 这两版往相册写需要存储权限，而本项目坚持不申请存储权限，所以改为弹出系统「保存到…」选择器，由你当场决定存哪里——同样零权限。 |
| 失败怎么办 | 不会静默失败：弹「保存失败，可以截屏后用微信提取文字」。 |
| 连点会不会存一堆 | 不会。保存过程中重复长按会被忽略，存完才恢复。 |

顺带确认：这次没有新增任何权限，`AndroidManifest.xml` 里仍然只有一条 `INTERNET`（只用于手动检查更新）。

## 2. 改进：Windows 关于窗的赞赏码

原来只有一行小字「右键可保存图片」——确实能用，但绝大多数人不会想到去右键。现在二维码下面多了一个**「保存赞赏码」**按钮，点一下直接下载成 `PDFPrivacyMasker-赞赏码.png`，说明文字也改成「微信扫码 · 金额随意 · 点下面的按钮保存图片」。

英文界面下按钮是「Save the tip QR」，说明文字同步为英文，下载文件名变成 `PDFPrivacyMasker-thanks-qr.png`。

## 3. 版本号

| 项目 | 上一版 | 本版 | 安装包 |
| --- | --- | --- | --- |
| Windows | 1.4.0 | **1.4.1** | `PDFPrivacyMasker-1.4.1.exe`（34.08 MB） |
| 安卓 | 1.4.0 | **1.4.1**（versionCode 8） | `PDFPrivacyMasker-1.4.1-arm64.apk`（14.14 MB） |

两端继续共用同一个版本号。**Windows 这一版功能上只有第 2 节那一处改动**，其余与 1.4.0 完全一致；之所以也发一个包，是为了让两端版本号对齐、免得 Windows 用户点「检查更新」时看到「有新版本 1.4.1」却只能下到 apk。

## 4. 验证情况

- 安卓：新增 2 条长按回归测试（长按触发保存、单击不触发），Robolectric 真实控件点击；`testDebugUnitTest` 44 例全通过，`testReleaseUnitTest` 42 例全通过。
- Windows：用 `dev/make_ui_preview.py` + Edge 无头渲染核对中英文关于窗，按钮位置、文案、下载文件名均正确。
- **如实说明**：手上没有安卓真机，相册实际落盘只在测试环境与代码路径上验证过，没做真机验收。装到手机上点一次长按，能弹出「已保存到相册」即算通过。

## 5. 升级须知

- 安卓可直接覆盖安装，数据不受影响（同一签名、versionCode 递增）。
- Windows 换 exe 即可，配置文件与保存位置设置都留着。
- 提醒一句：Release 附件必须叫 `PDFPrivacyMasker-1.4.1.exe` / `PDFPrivacyMasker-1.4.1-arm64.apk`，检查更新就是从文件名里读版本号的。

---

# 版本升级说明 · v1.4.0（Windows + 安卓）

> 这是**唯一一份**版本升级说明。以前 Windows 和安卓各写一份、内容还互相打脸的情况，从这一版起不再有。
> 想找别的文档，看 [DOCS.md](DOCS.md)；想直接上手用，看 [README.md](README.md)。

**一句话结论**：这一版把 Windows 端和安卓端拉到同一个版本号 1.4.0，两端都能在设置里手动检查更新、都能中英文切换、都能双击方框取消/恢复打码；安卓端补上了拖框放大镜，并且把手指挡字和"预览时勾选项跑没"这两个老问题一次解决。

---

## 0. 版本对照

| 项目 | 上一公开版本 | 本版 | 安装包 | 体积 | 适配 |
| --- | --- | --- | --- | --- | --- |
| Windows | v1.3.0 | **v1.4.0** | `PDFPrivacyMasker-1.4.0.exe` | 35.73 MB | Windows 10 / 11，64 位，免安装单文件 |
| 安卓 | 无（首次公开） | **v1.4.0** | `PDFPrivacyMasker-1.4.0-arm64.apk` | 14.83 MB | Android 8.0+（minSdk 26），arm64-v8a |

安卓端 1.0.0 ~ 1.2.3 都是内部迭代，从未公开；本次直接以 1.4.0 与 Windows 端对齐发布。

---

## 1. 双端同步新增

### 1.1 双击取消 / 恢复单处打码

| | 说明 |
| --- | --- |
| 怎么操作 | **安卓**：手指双击预览页上的任意一个方框。**Windows**：鼠标双击页面上的任意一个方框。 |
| 管哪些框 | 自动识别出来的红框、手动拖出来的蓝虚线框，一视同仁。 |
| 效果 | 双击 → 该处打码取消，框变灰；再双击 → 恢复打码。 |
| 点得中吗 | 命中判定在框外各留了一点余量（安卓 10dp、Windows 6px），小字框也能点中；框重叠时取最上面那一层。 |
| 会提示吗 | 会。安卓弹底部短提示「已取消这处打码 / 已恢复这处打码」，Windows 弹同样的 toast，并带上这一处的文字内容。 |

以前要取消某一处，只能去列表里找到那一行再取消勾选；小字、密集表格里根本找不到。现在直接在页面上点。

### 1.2 顶部功能提示条

两端都在处理页顶部加了一条不占地方的浅底提示，写明这两个新操作：

- 安卓：`拖动可框选 · 双击方框取消或恢复打码`
- Windows：`拖动框选 · 双击方框取消/恢复打码`

Windows 窗口宽度小于 1040px 时这条会**自动隐藏**，避免和工具栏挤在一起；鼠标悬停原位置仍有完整说明。安卓在平板双栏布局下横跨顶部，不会挤压预览。

### 1.3 设置里手动「检查更新」

| | 说明 |
| --- | --- |
| 入口 | **安卓**：设置 → 版本与更新 → 检查更新。**Windows**：右上角「设置」→ 版本与更新 → 检查更新。 |
| 做什么 | 去 GitHub 读一次公开发布的版本号，和当前版本比大小。 |
| 有新版本 | 直接把默认浏览器打开到下载页，同时把链接明文显示出来。 |
| 已是最新 | 显示「已是最新版本」和当前版本号。 |
| 打不开浏览器 / 网络被拦 | 不装作没事：把链接明文摆出来，给一个「复制链接」按钮，再列出三步排查清单（安全软件或家长控制是否拦截浏览器、系统代理是否开着、防火墙是否拦截本程序联网）；最后还留了兜底——直接截屏这一屏，用微信「提取文字」把链接抠出来手动粘贴。 |
| 版本号从哪读 | 优先读安装包文件名里的版本（`PDFPrivacyMasker-1.4.0.exe` / `-1.4.0-arm64.apk`），读不到再退回 release 的 tag（`v1.4.0`）。 |
| 隐私 | 只发一个查版本号的请求，**不上传文件、不上传任何个人信息、不做任何埋点**。不点这个按钮就完全不联网。 |

### 1.4 中英双语即时切换

| | 说明 |
| --- | --- |
| 入口 | **安卓**：设置 → 界面语言。**Windows**：设置 → 界面语言 / Language。 |
| 切换方式 | 点一下立即整页切换，**不用重启**，选择会记住，下次打开还是这个语言。 |
| Windows 本版补齐了什么 | 以前只译了按钮和标题，正文段落、文件摘要、识别类型标签、状态栏仍是中文。本版把整段带行内标签的说明文字、随状态变化的文件摘要、状态栏提示、类型标签（手机号 / 身份证号 / 姓名…）全部纳入词表，切换时整页重算。 |
| 安卓本版补齐了什么 | 识别结果的分类标题、默认导出文件名（`文档.pdf` / `document.pdf`）、地址与生日的掩码格式（`（共 N 字）` / `-**-**`）都改为随语言走。 |

---

## 2. 安卓端本次新增（首次公开的功能全景）

安卓端此前没有公开版本，所以除了上面 4 项，下面这些也是这次一起交付的：

| 功能 | 说明 |
| --- | --- |
| 拖框放大镜 | 手指拖虚线框时，手指右上方浮出一个 96dp 的圆形放大镜（2.8 倍），实时放大手指底下的字。靠近屏幕边缘时自动翻到另一侧，不会被屏幕切掉。 |
| 镜内同步虚线框 | 镜子里不只有放大的字，**你正在拖的那条蓝色虚线框也一起放大画在镜内**，边框和手指位置始终对得上，不会出现"看到字但不知道框到哪"的情况。松手即消失。 |
| 预览与勾选同屏 | 预览区占满内容区（约 80% 屏高），识别结果做成底部折叠条 + 浮层面板：想看预览就收起，想勾选就点开，两者不再抢屏幕。 |
| 手动框选 | 在预览页按住拖出虚线框，松手即成为一个打码区域，与自动识别结果同一条打码路径，效果一样不可还原。 |
| 保存两问 | 首次导出时问你存到哪个文件夹，可勾「下次默认使用这个路径」「不再询问」；勾了不再询问且已授权目录，之后静默写入，重名自动加序号。 |
| 深色 / 浅色 / 跟随系统 | 三态可选，深色下红标、橙标另有一套配色（不是把浅色硬压暗）。 |
| 适配折叠屏与平板 | 宽屏走双栏，折叠屏按铰链宽度留白，空间太矮时自动收起预览区/翻页栏，不溢出。 |
| 全屏查看 | 点一下预览进全屏，全屏里同样能拖框、双击。 |

---

## 3. Windows 端本次新增

| 功能 | 说明 |
| --- | --- |
| 双击取消 / 恢复打码 | 见 1.1，鼠标双击即可，不用回列表找。 |
| 顶部提示条 | 见 1.2。 |
| 检查更新 | 见 1.3，走本地 `/api/check_update`，网络异常时会用放宽证书的方式重试一次再报错。 |
| 界面语言 | 见 1.4，设置面板里新增「界面语言 / Language」，与「版本与更新」并列。 |
| 版本号与文件属性 | 程序版本、`version_info.txt` 里的产品版本、关于页显示的版本统一为 1.4.0。 |

Windows 端原有的自动识别、手动框选、逐条确认、自定义保存位置、零改动原文件等能力没有变化，不重复列。

---

## 4. 本次修复的已知问题

| # | 端 | 现象（用户看到的） | 原因 | 现在 |
| --- | --- | --- | --- | --- |
| 1 | 安卓 | 手动拖了框，预览上什么都没有，看不出框住了哪 | 手动框只在导出时才参与打码，预览层没有画它 | 松手立刻出现蓝色虚线框，与自动框同一套绘制，翻页、切换语言后都在 |
| 2 | 安卓 | 看预览时，下面的识别结果和勾选项被挤出屏幕，"勾选没了" | 预览区与列表面板抢同一块高度，列表被压到视口外 | 预览固定占满内容区，列表改成底部折叠条 + 浮层面板，随时展开/收起，勾选状态不再被重置 |
| 3 | 安卓 | 放大镜里只有一个小圆点，看不到正在拖的虚线框 | 镜内只画了中心标记，没有把框坐标映射进去 | 框按同一倍率映射进镜内，镜里的边和手指位置一致 |
| 4 | 安卓 | 手指压在字上，看不出框边落在哪，只能凭感觉 | 没有放大，手指本身挡住了文字 | 手指右上方 2.8 倍放大镜，贴边自动翻转，松手消失 |
| 5 | 安卓 | 设置项变多后，面板底部按钮被切掉、点不到 | 面板高度写死 | 高度改为屏高的 88%，内容可滚动，任何机型都够按 |
| 6 | 安卓 | 英文界面下，分类标题、默认文件名、掩码格式还是中文 | 部分文案没走双语取值，直接写死 | 全部改为按语言取值 |
| 7 | 双端 | 英文界面里仍有零星中文残留 | 个别文案键尾部带全角空格，与词表键对不上 | 词表键统一去空白再匹配，命中率补齐 |
| 8 | Windows | 英文说明段落被截断、后半句消失 | 段落属性里用了单引号，英文 `don't` 的撇号把属性提前闭合 | 改用排版撇号 `don’t`，段落完整显示 |
| 9 | Windows | 切换语言后，文件摘要、状态栏、类型标签还停在旧语言 | 这些文字在渲染时算一次就不再更新 | 切换语言时整页重算，随语言变化的文字一起刷新 |
| 10 | 双端 | 检查更新在跳不过去时无路可走，只能干瞪眼 | 只尝试打开浏览器，没有别的出口 | 链接明文 + 复制按钮 + 三步排查清单 + 截屏 OCR 兜底 |

---

## 5. 升级前需要知道的几件事

1. **安卓端新增了一个网络权限**：`android.permission.INTERNET`。
   只在你主动点「设置 → 检查更新」时用一次；识别、打码、保存仍然全部在本机完成。
   安装时如果看到"网络"字样，不代表文件会被上传。
2. **安卓端仍然没有存储权限**：选文件走系统文件选择器，只拿到你挑中那一个文件的临时读权限；保存时由你当场决定写到哪里。
3. **版本号跳号是有意的**：为了两端共用同一个版本号，安卓从内部版本 1.2.3 直接跳到 1.4.0；Windows 公开版是 1.3.0（内部迭代到 1.3.4），本版统一为 1.4.0。功能上没有跳过任何东西。
4. **Windows 顶部提示条窄窗口会消失**：窗口宽度小于 1040px 时自动隐藏，这是为了不挤坏工具栏，不是坏了。
5. **旧设置会保留**：两端的语言、主题、保存位置偏好都存在本地，升级后沿用，不用重设。

---

## 6. 验证情况

已经做到的：

- 安卓 **42 例**单元测试与界面截图测试全部通过（含新增的 5 例检查更新解析测试、2 张更新结果卡片截图）。
- 识别内核回归：6 份测试文档共 **452 条**识别结果与 Windows 端**逐条 100% 一致**；纯净文档 **0 误报**。
- Windows 界面用 Edge headless 渲染导出 HTML 逐张核对：设置（中/英）、检查更新·有新版本、检查更新·失败、处理页英文、关于页英文。
- Windows 打包产物做过启动冒烟：进程存活，WebView 子进程正常拉起。

还没做到的（如实说明）：

- **安卓未做真机安装验收**。放大镜尺寸（96dp / 2.8 倍）、双击手感、不同机型的状态栏遮挡，只经过本地渲染核对，需要装到手机上实测。觉得放大镜太大/太小，可以在 `android/app/src/main/java/com/neurotracee/pdfmask/ui/WorkScreen.kt` 里改 `d` 与 `zoom` 两个参数。
- Windows 的浏览器跳转只在本机环境验证，未覆盖所有安全软件组合。

---

## 7. 发布附件命名（关系到检查更新能不能用）

「检查更新」是从**安装包文件名**里读版本号的。发布 Release 时附件必须按这个格式命名，否则只会退回读 tag，甚至提示「没有可用安装包」：

```
PDFPrivacyMasker-1.4.0.exe
PDFPrivacyMasker-1.4.0-arm64.apk
```

规则：`PDFPrivacyMasker-<版本号>` + 平台标识，安卓补 `-arm64`。中间不要加空格、不要写中文、不要省略版本号。
