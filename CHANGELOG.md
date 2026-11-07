# v1.4.3 版本说明（Windows + 安卓）

更新级别：建议

**一句话结论**：这一版主要是「把被指出的问题一条条修掉」——检查更新不再放宽证书校验、只认 GitHub/Gitee 官方下载域名；国内用户默认走 Gitee 通道，不用再靠代理；打码时连 PDF 注释和书签标题里的隐私也一起清洗掉；跨年后身份证不会因为年份上限写死而漏打。工程上把 4000 行的单文件拆开了，并加了跨端一致性测试，防止 Windows 和安卓两套规则各走各的。

---

## 1. 安全：更新器不再接受不可信的下载地址

- **删掉了放宽证书校验的兜底分支。** 旧版在直连失败时会用 `ssl.CERT_NONE` 再试一次，等于放弃证书验证——链路上只要有人做中间人，返回的 JSON 就能把「下载地址」换成任意站点。现在只有严格校验一条路，失败就如实报错（提示里会显示是哪个通道、什么原因）。
- **新增下载域名白名单。** GitHub 的发布资产只认 `github.com` / `objects.githubusercontent.com` / `release-assets.githubusercontent.com` / `codeload.github.com`，Gitee 只认 `gitee.com`（含子域）。白名单外的地址一律不使用，只给发布页链接。安卓端同样加了一份白名单。

## 2. 新增：Gitee 更新通道（国内直连）

| 环境 | 通道顺序 |
| --- | --- |
| 简体中文系统 + 中文界面 | 先 Gitee，失败再 GitHub |
| 其它语言 | 先 GitHub，失败再 Gitee |

判断依据是系统的界面语言（Windows 读 `GetUserDefaultUILanguage`，安卓读 `Locale`）加上软件内的语言设置，两个都是中文才走 Gitee 优先。两个通道都拿不到才报错，报错里会列出每个通道各自的失败原因。窗口标题里会标出这次结果来自哪个通道（Gitee / GitHub）。

## 3. 隐私：注释与书签也一起清洗（Windows）

正文打码用的是「抹除文本层 + 贴马赛克」，碰不到 PDF 的注释（批注、便签、高亮附言）和书签标题——这两类是独立对象，内容会原样留在成品里，和 README 里「文字层一并抹除」的说法确实矛盾。现在 `redact()` 末尾会再洗一遍：

- **注释**：内容 / 标题 / 主题里出现手机号、身份证、银行卡、邮箱、座机，或本次正文已命中的姓名、地址 → 整条删除（改一半容易漏，尤其是回复串）。
- **书签**：标题按同一套规则打码（`第一章 联系人 13812346780` → `第一章 联系人 138****6780`），层级和目标页保持不变，条数不变。
- 干净的注释和书签不受影响。

安卓端本来就是按页重绘成图片再组装新 PDF，注释和书签天然不会带过去，无需改动。

## 4. 修复：跨年后身份证会漏打

身份证合理性校验里把出生年份上限写死成了 `2026`（Python 和 Kotlin 各一处）。跨年之后，当年出生的号码会被判成「不合法」而漏打。现在改成跟随系统时钟取当前年份。

## 5. 工程改动

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

**TL;DR** — this release is mostly "fix every issue that was reported". The updater no longer relaxes TLS verification and only accepts download links from the official GitHub/Gitee release hosts; users in mainland China now get the Gitee channel first, no proxy needed; redaction now also scrubs PDF annotations and bookmark titles; the hard-coded year cap that made ID numbers leak after New Year is gone. On the engineering side, the 4,000-line single file was split up and a cross-platform parity test was added so the Windows and Android rule sets can no longer drift apart.

## 1. Security: the updater refuses untrusted download URLs

- **Removed the `ssl.CERT_NONE` fallback.** The old code retried with certificate verification disabled, which is exactly what a man-in-the-middle needs to swap the "download URL" in the JSON response. Only strict verification is used now; on failure it reports the channel and the reason.
- **Download host allowlist.** GitHub assets are only accepted from `github.com`, `objects.githubusercontent.com`, `release-assets.githubusercontent.com` and `codeload.github.com`; Gitee only from `gitee.com` (and subdomains). Anything else falls back to the release page. Same rule on Android.

## 2. New: Gitee update channel

| Environment | Channel order |
| --- | --- |
| Simplified Chinese system + Chinese UI | Gitee first, then GitHub |
| Any other language | GitHub first, then Gitee |

The decision uses the system UI language (Windows: `GetUserDefaultUILanguage`; Android: `Locale`) combined with the in-app language setting — both must be Chinese to prefer Gitee. If both channels fail, the error lists the reason for each.

## 3. Privacy: annotations and bookmarks are scrubbed too (Windows)

Redaction only covered page text; annotations (comments, sticky notes, highlight notes) and bookmark titles are separate objects and used to survive untouched, contradicting the README's "text layer erased as well". `redact()` now also:

- **Deletes annotations** whose content / title / subject contains a phone number, ID number, bank card, email, landline, or a name/address already matched in the text.
- **Masks bookmark titles** with the same rules (`Contact 13812346780` → `Contact 138****6780`), keeping level, target page and count unchanged.
- Leaves clean annotations and bookmarks alone.

Android renders each page to a bitmap and assembles a new PDF, so annotations and bookmarks never make it into the output — nothing to fix there.

## 4. Fixed: ID numbers leaking after New Year

The plausibility check capped birth year at `2026` (one place in Python, one in Kotlin), so IDs of people born in the new year were rejected and therefore not masked. It now follows the system clock.

## 5. Engineering

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
