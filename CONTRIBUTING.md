# 参与改进

先说结论：**不用问、不用等批准，直接 fork 就行。** 这个项目是个人在业余时间维护的，
与其让你在门口等回复，不如你先把东西做出来。

这份文件只讲三件事：代码在哪、怎么跑起来、提交前必须过哪些检查。

- 许可是 **GNU AGPL-3.0-or-later**，另有 [ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md) 里的三条附加要求
  （保留署名、程序里标注原项目地址、改过的版本要说明改过）。改动前请先看一眼，尤其如果你打算商用。
- 报缺陷、提建议、问用法 → 用 [Issues](https://github.com/neurotracee/pdf-privacy-masker/issues/new/choose)，
  有模板，照着填最快。Gitee 那边也开着：[Gitee Issues](https://gitee.com/bio234/pdf-privacy-masker/issues)。
- 想改代码 → 本文往下看。

---

## 1. 仓库长什么样

根目录这一层是 **Windows 端**，`android/` 是**安卓端**。两端共用同一套识别规则，但**版本号各自独立**（见第 4 节）。

| 路径 | 是什么 |
| --- | --- |
| `pdfmask.py` | Windows 端主程序：识别规则、打码、HTTP 服务、命令行模式 |
| `pdfmask_ocr.py` | 本地 OCR（扫描件 / 图片型 PDF）：模型加载、文字检测、识别、逐字框换算 |
| `assets/ocr/` | OCR 模型与字典、许可原文、出处与 SHA-256（安卓端直接引用这一份，不另外存） |
| `pdfmask_webui.py` | 首页界面（一整页 HTML + CSS + JS，字符串形式） |
| `pdfmask_update.py` | 检查更新：Gitee / GitHub 双通道、发布正文解析 |
| `thanks_asset.py` | 赞赏码图片（base64 内嵌，单文件打包不丢） |
| `version_info.txt` | exe 的文件属性（版本号写在这里） |
| `android/` | 安卓工程（Kotlin + Compose，Gradle 工程完整可构建） |
| `dev/` | 开发与回归测试脚本，**不参与打包** |
| `test/` | 测试用 PDF 样本与规则金标准（`rules_golden.json`） |
| `docs/` | 详细说明，按编号读；`DOCS.md` 是索引 |

文档地图在 [DOCS.md](DOCS.md)，功能说明在 [README.md](README.md)，改了什么在 [CHANGELOG.md](CHANGELOG.md)。

---

## 2. 本地跑起来

### Windows 端

需要 **Python 3.11+**（Pillow 13 要求 ≥3.11；numpy 在 3.12+ 装 2.5.x，3.11 自动装 2.4.x）。

```bash
pip install -r requirements.txt
python pdfmask.py            # 启动界面（会自己在浏览器打开）
python pdfmask.py --cli 输入.pdf 输出.pdf    # 命令行批处理
```

依赖在 `requirements.txt` 里：`PyMuPDF`（读写 PDF、拿文字坐标）、`Pillow`（拼图与马赛克）、`numpy` 与 `onnxruntime`（仅本地 OCR 用，缺了程序会自动退回手动框选）。`PyInstaller` 只在打包 exe 时需要，`打包.bat` 会自己装，没写进 `requirements.txt`。

打包成单文件 exe 用 `打包.bat`（PyInstaller），细节见 [docs/05-构建与发布.md](docs/05-构建与发布.md)。

### 安卓端

需要 **JDK 17 + Android SDK 34 + Gradle**。

```bash
cd android
gradle assembleRelease     # 产物在 app/build/outputs/apk/release/
gradle testReleaseUnitTest # 单元测试
```

签名用的是本机的 `android/keystore.properties`（**不在仓库里**，自己打包时自建一份，
没签名的产物装不上，但能装上你自己签的那份，日常调试够了）。

---

## 3. 提交前必须过的检查

改动之后，**至少跑一次**这个：

```bash
python dev/selfcheck.py
```

它会端到端跑一遍：造样本 → 识别 → 打码 → 核对每一类的召回、文字层有没有剩、马赛克能不能被反推、版面有没有位移、原文件有没有被改。最后一项是扫描件（无文字层 PDF）的专项端到端。
最后一行是 `自检结论: 全部通过` 才算过。

改到这些地方时，额外要求：

| 你改了什么 | 还要做什么 |
| --- | --- |
| **识别规则**（手机号、身份证、姓名、地址……的判定） | 跑 `python dev/test_no_false_positive.py` 确认误报没变多；规则表有变动就重新生成 `test/rules_golden.json`（`python dev/gen_rules_golden.py`），否则金标准测试会失败 |
| **更新检查 / 版本号解析** | 跑 `python dev/test_source_pick.py`（默认源规则）和 `python dev/test_release_digest.py`（发布正文拆分）；两端逻辑是两份实现（Python + Kotlin），**改一端必须同步另一端** |
| **安卓端** | 跑 `gradle testReleaseUnitTest`；规则相关的逻辑要与 Windows 端对齐（已有对照测试盯着这件事） |
| **OCR / 扫描件识别** | 跑 `python dev/test_ocr_redact.py`（造无文字层表单 → 识别 → 打码 → 再 OCR 复核读不出）；两端实现同构，**改一端必须同步另一端**；换了模型要么改，要么把 `assets/ocr/README.md` 里的 SHA-256 一起更新 |
| **刁难文档 4.0（8 页扫描件）** | 跑 `python dev/test_hard4.py`；三项必须同时为真：漏检 0、泄漏 0、误伤 0。只盯「泄漏」会被整页涂黑骗过，只盯「漏检」则测不出有没有真抹掉 |
| **界面文案 / 帮助文字** | 中英文都要改，`README.md` 与 `docs/` 里同一处说法要跟着变 |
| **新增依赖** | 更新 `requirements.txt`（或 `build.gradle.kts`）与 `NOTICE.md`，并确认许可兼容（AGPL-3.0 能用的库才能进） |

CI 会在提交到 GitHub 后自动跑其中一部分（见 `.github/workflows/ci.yml`）。CI 绿了不代表一定没问题，
但它能拦住「连导入都失败」「单测挂了」这种低级错误。

---

## 4. 版本号规则

版本号统一四段：**`主.次.修订.小版本`**，发布标签前面加小写 `v`，例如 `v1.4.6.1`。

规律只有一条：**越靠右的位越细，动得越勤**。日常工作发的是**第四位**；
第三位留给成组的「大版本」；第二位是多项大改合在一起的「超大版本」；
第一位要等前面几位累计到一定程度、整代翻新才动。

| 位 | 叫法 | 什么时候 +1 | 例子 |
| --- | --- | --- | --- |
| 第 1 位 | 主版本 | 整代翻新：识别内核或文件格式换代、旧配置与旧工作流不再兼容 | `2.0.0.0` |
| 第 2 位 | 超大版本 | 多个方向同时大改、合起来一次发布（例如识别能力 + 界面 + 分发方式一起换） | `1.5.0.0` |
| 第 3 位 | 大版本 | 一次成体系的新能力上线（例如 v1.4.6 的扫描件 OCR） | `1.4.7.0` |
| 第 4 位 | 小版本 | **日常发版**：修缺陷、改文案、调性能、补文档、加一条提示 | `1.4.6.1` |

三条既定做法：

- **两端版本号各自独立，允许不一样。** Windows 看 `pdfmask.VERSION`，安卓看
  `appVersionName`。只改了一端就只升那一端，另一端原地不动——「Windows 1.4.6 + 安卓 1.4.7」
  是完全正常的状态。判断要不要更新时，各端只比自己安装包文件名里的版本号，
  所以只发一端的版本不会去打扰另一端（只改了安卓的文案，就没必要为 Windows 重打 73MB 的 exe）。
- **改第四位时，前三位一个都不动。** 例如在 1.4.6 之后修了一批扫描件缺陷，发的是
  `1.4.6.1`，不是 `1.4.7.0`——`1.4.7.0` 的意思是「又有新的大能力」。
- **老的三段写法**（`1.4.6`）一律视同 `1.4.6.0`，历史 Release 不用回头改，也不会互相提示更新。
- **比较方式是「补齐四段后逐段比、缺段当 0」**，所以 `1.4.6` 与 `1.4.6.0` 是同一版，
  `1.4.6.2` 明确比 `1.4.6.1` 新。

一次发版**只改要发的那一端**：

- **Windows**：`pdfmask.VERSION` 和 `version_info.txt`（exe 属性）两处，必须一致；
- **安卓**：`android/app/build.gradle.kts` 的 `appVersionName`。`versionCode` 由它自动算出来
  （主×1000000 + 次×10000 + 修订×100 + 小版本），**不要手填**。

两端都要发，就两处一起动；只发一端时，另一端一个字都别改——改了就等于逼着用户
下载一个内容没变的包。

---

## 5. 提交与 PR

- **一个 PR 只做一件事。** 顺手重排整个文件、改一堆引号风格这类改动会让 review 变成体力活，请单独提。
- **提交信息**：一句话说清做了什么，正文说为什么。中文、英文都行，我看得懂。
- **PR 描述里请写**：改了什么、为什么改、怎么验证的（贴 `selfcheck` 的结果）、影响哪一端（Windows / 安卓 / 两端）。
- **不要提交**：`dist/`、`build/`、`release/`、`.gradle/`、签名文件（`.jks` / `keystore.properties`）、
  你自己机器上的路径配置。这些都在 `.gitignore` 里，别加 `-f` 强推。
- **不要自己改版本号。** 版本号由发版统一改（规则见第 4 节：`pdfmask.VERSION`、`version_info.txt`、
  `build.gradle.kts` 的 `appVersionName` 三处），混在功能 PR 里会导致发版时对不上。

不着急、也不催：**提了就会看到，没回不代表被否掉。** 如果一件事你已经在 fork 里做完了，
不必等合并——写清改动、按上面的检查走一遍，别人能直接用。

---

## 6. 报告问题时的注意事项

- **不要贴真实的身份证号、银行卡号、手机号、住址。** 需要给样本就用假的，或者自己造一份
  （`python dev/make_test_pdf.py` 可以生成带假数据的测试文档）。
- **说清三件事**：版本号（设置里能看到）、什么系统（Windows 还是安卓几）、怎么复现。
  有截图最好，截图里也请把真实号码盖掉。
- **安全漏洞**（比如能让别人读到你的文件、能绕过打码把内容还原）：**不要开公开 issue**，
  用 GitHub 的 [私密漏洞上报](https://github.com/neurotracee/pdf-privacy-masker/security/advisories/new)，
  或者先在 issue 里说「有个安全问题，想私下说」，我会给联系方式。

---

## 7. 这个项目不接受什么

- **把打码改成「看起来盖住了、其实还能选中文字」的实现。** 文字层必须真的删掉，这是整个项目的底线。
- **为了多认几个而把误报推高的规则。** 打错一个会议日期，比漏掉一个号码更让人不敢用。
- **没跑过自检就提交的规则改动。** 规则之间会互相影响，改一处经常连带另一处，光看代码看不出来。
- **换掉 PyMuPDF 的重写。** 有更好的方案可以提 issue 讨论，但整体重写不是 PR 能承载的事。
