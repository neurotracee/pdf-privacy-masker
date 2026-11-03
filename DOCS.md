# 文档地图 · 每个文件在哪、讲什么、怎么找

> 这份文件只干一件事：**告诉你（或者接手操作的 AI）想看的内容在哪个文件里**，以及**手上的文件该放到仓库的哪个位置**。
> 不重复任何功能细节——那是 [README.md](README.md)、[CHANGELOG.md](CHANGELOG.md)、`docs/` 的活儿。

---

## 1. 记住三个入口就够了

| 入口 | 什么时候看 | 讲什么 |
| --- | --- | --- |
| **[README.md](README.md)** | 第一次来、想知道这东西是什么、怎么最快跑起来 | 双端总览、下载与安装、能识别什么、许可与署名 |
| **[CHANGELOG.md](CHANGELOG.md)** | 想知道"这次更新了什么、修了什么" | v1.4.0 双端功能更新与已修问题清单 |
| **[DOCS.md](DOCS.md)**（本文件） | 想找具体某件事的说明、或要往仓库里放文件 | 文档索引 + 上传清单 |

其余所有细节，都在 `docs/` 目录里，按编号顺序读即可。

---

## 2. 仓库结构（一层层看）

```
pdf-privacy-masker/
│
├─ README.md                    项目总览：唯一入口，中英双语
├─ CHANGELOG.md                 版本升级说明（本版 v1.4.0，双端合一）   ← 文件一
├─ DOCS.md                      文档地图：在哪、怎么找、怎么放          ← 文件二（本文件）
│
├─ LICENSE                      GNU AGPL-3.0 全文
├─ NOTICE.md                    第三方组件与许可（Windows + 安卓合并）
├─ ADDITIONAL-TERMS.md          AGPL 第 7 条 (b) 项附加条款：署名与项目地址
├─ 使用说明.txt                  随 exe 一起发给用户的纯文本简版（不开浏览器也能看）
│
├─ docs/                        所有详细说明（按编号读）
│  ├─ 01-使用说明-Windows.md     Windows 端完整操作说明
│  ├─ 02-使用说明-安卓.md        安卓端完整操作说明
│  ├─ 03-识别规则与已知限制.md    能识别什么、按什么规则、什么认不出来
│  ├─ 04-常见问题.md             扫描件、加密、误报、漏报、跳转失败等
│  ├─ 05-构建与发布.md           自己打包、跑测试、发 Release、附件命名
│  └─ img/                      截图与赞赏码（README、docs 共用）
│
├─ android/                     安卓端源码（Kotlin + Compose，完整工程）
│  ├─ app/src/main/java/com/neurotracee/pdfmask/   …
│  ├─ app/src/test/java/…        Robolectric 界面截图测试 + 检查更新解析测试
│  ├─ build.gradle.kts           compileSdk 34 / minSdk 26 / versionName 1.4.0
│  └─ .gitignore                 已排除签名文件与构建产物
│
├─ pdfmask.py                   Windows 端主程序（单文件，含内嵌前端）
├─ pdfmask.spec / 打包.bat       Windows 端打包配置与一键打包脚本
├─ requirements.txt             Windows 端 Python 依赖
├─ version_info.txt             Windows exe 的文件属性（产品名、版本、版权）
├─ app.ico                      Windows 程序图标
│
└─ dev/                         开发与回归测试脚本（不参与打包）
```

**为什么 Windows 的文件在根目录、安卓在子目录？**
这个仓库最初是 Windows 端的仓库，所有 Release 链接、文档里的相对路径、打包脚本都指向根目录。把 Windows 端挪进 `windows/` 会连带改一堆路径，属于純搬家、收益为零的风险改动，所以保持原位；安卓端作为新增平台放进 `android/`。看目录时记住一句：**根目录这一层 = Windows 端，`android/` = 安卓端。**

**安卓端没有自己的 README。** 这是有意的：两端的能力、许可、署名完全共用一套说法，写两份必然出现"一端改了另一端忘改"。安卓的一切说明都写在 `README.md` 和 `docs/02-使用说明-安卓.md` 里。

---

## 3. 按"我想干什么"找

| 我想…… | 看这个 | 在仓库的哪个位置 |
| --- | --- | --- |
| 下载安装包、先跑起来 | [README.md](README.md) → 「下载与安装」 | 根目录 |
| 知道这次更新了什么、修了什么 | [CHANGELOG.md](CHANGELOG.md) | 根目录 |
| 学会 Windows 端怎么用 | [docs/01-使用说明-Windows.md](docs/01-使用说明-Windows.md) | `docs/` |
| 学会安卓端怎么用 | [docs/02-使用说明-安卓.md](docs/02-使用说明-安卓.md) | `docs/` |
| 搞清"到底能识别哪些信息、按什么规则" | [docs/03-识别规则与已知限制.md](docs/03-识别规则与已知限制.md) | `docs/` |
| 遇到问题：扫描件、加密、误报、跳转失败 | [docs/04-常见问题.md](docs/04-常见问题.md) | `docs/` |
| 自己打包 exe / 自己编译 apk | [docs/05-构建与发布.md](docs/05-构建与发布.md) | `docs/` |
| 发新版 Release、给安装包起名 | [docs/05-构建与发布.md](docs/05-构建与发布.md) → 「发布 Release」 | `docs/` |
| 二次开发、fork、商用要遵守什么 | [ADDITIONAL-TERMS.md](ADDITIONAL-TERMS.md) + [NOTICE.md](NOTICE.md) | 根目录 |
| 看代码从哪进 | [README.md](README.md) → 「代码结构」 | 根目录 |
| 改界面文字 / 加语言 | `android/.../ui/Lang.kt`、`pdfmask.py` 里的 `DICT` | 源码 |
| 改放大镜大小、倍数 | `android/.../ui/WorkScreen.kt` 里的 `d`、`zoom` | 源码 |

---

## 4. 按关键词找

| 关键词 | 去哪一节 |
| --- | --- |
| 放大镜、拖框、虚线框、手指挡字 | `docs/02-使用说明-安卓.md` → 第 4.2 节「手动框选 + 放大镜」；`CHANGELOG.md` → 第 2 节、第 4 节第 ③④ 行 |
| 双击、取消打码、恢复打码 | `CHANGELOG.md` → 第 1.1 节；`docs/01` 第 2.3 节、`docs/02` 第 4.3 节 |
| 检查更新、版本号、打不开浏览器、复制链接 | `CHANGELOG.md` → 第 1.3 节；`docs/04-常见问题.md` → 第四节「检查更新相关」 |
| 中英切换、语言、Language | `CHANGELOG.md` → 第 1.4 节；`docs/01` 第 5 节、`docs/02` 第 6 节 |
| 权限、联网、上传、隐私 | `README.md` →「隐私与权限」；`docs/02-使用说明-安卓.md` → 第 7 节 |
| 扫描件、图片里的字 | `docs/03-识别规则与已知限制.md` → 第 3、5 节 |
| 姓名、姓氏、疑似、橙色条目 | `docs/03-识别规则与已知限制.md` → 第 2 节「姓名怎么判断」 |
| 保存位置、不再询问、默认路径 | `docs/01` 第 3 节「打码后的文件存哪」；`docs/02` 第 5 节「生成与保存」 |
| 打包、PyInstaller、gradle、签名 | `docs/05-构建与发布.md` → 第 1、2 节 |
| 测试、回归、452 条、截图核对 | `docs/05-构建与发布.md` → 第 3 节「测试」 |
| 许可、AGPL、商用、署名、fork | `ADDITIONAL-TERMS.md`；摘要见 `README.md` →「关于署名」 |
| 第三方库、PyMuPDF、PDFBox | `NOTICE.md` |
| 赞赏、奶茶、二维码 | `README.md` →「支持」 |

---

## 5. 每个文件到底写什么

| 文件 | 给谁看 | 内容包括 | 什么时候要改 |
| --- | --- | --- | --- |
| `README.md` | 第一次来的人 | 是什么、双端下载安装、能力对照表、代码结构、隐私与权限、许可摘要、赞赏 | 新增平台、新增能力、改下载方式 |
| `CHANGELOG.md` | 老用户、升级的人 | 版本对照、新增功能（双端 + 分端）、修复清单、升级须知、验证情况、附件命名 | **每次发版都要在顶部加一节** |
| `DOCS.md` | 找文档的人 / 接手操作的 AI | 仓库结构、按需求与关键词的索引、上传清单 | 新增或挪动文档时 |
| `docs/01` | Windows 用户 | 双击运行、拖入 PDF、勾选、手动框选、双击取消、保存位置、检查更新、语言、打码原理 | Windows 端界面或流程变化时 |
| `docs/02` | 安卓用户 | 安装、选文件、预览与勾选、拖框与放大镜、双击取消、保存、检查更新、语言主题 | 安卓端界面或流程变化时 |
| `docs/03` | 想评估准不准的人 | 识别类型与规则、姓名策略、跨行/表格处理、打码不可还原的原理、不支持的情况 | 改了识别规则时 |
| `docs/04` | 遇到问题的人 | 常见问题与自助排查 | 收到重复问题就补一条 |
| `docs/05` | 想自己构建/发布的人 | Windows 打包、安卓编译与签名、测试怎么跑、Release 附件命名、`dev/` 脚本清单 | 构建流程或版本号变化时 |
| `NOTICE.md` | 合规检查 | 双端第三方组件、许可、必须保留的署名 | 增删依赖时 |
| `ADDITIONAL-TERMS.md` | 二次开发者、商用者 | AGPL 第 7 条 (b) 项的附加要求（署名、原项目地址、改动声明） | 条款变化时 |
| `使用说明.txt` | 拿到 exe 的普通用户 | 纯文本简版：上手五步、保存位置、检查更新、几条限制 | 与 `docs/01` 口径保持一致 |

---

## 6. 把文件放到仓库哪里（GitHub 网页操作清单）

下面这些路径都是**仓库根目录起算**的，在 GitHub 网页上打开对应目录 → `Add file` → `Upload files`（或 `Create new file` 后粘贴内容）即可。

### 本次要新增的文件

| 文件 | 放到 | 说明 |
| --- | --- | --- |
| `CHANGELOG.md` | 根目录 | 新建，内容即本仓库这份 |
| `DOCS.md` | 根目录 | 新建，内容即本仓库这份 |
| `docs/01-使用说明-Windows.md` | `docs/` | 新建目录与文件 |
| `docs/02-使用说明-安卓.md` | `docs/` | 同上 |
| `docs/03-识别规则与已知限制.md` | `docs/` | 同上 |
| `docs/04-常见问题.md` | `docs/` | 同上 |
| `docs/05-构建与发布.md` | `docs/` | 同上 |
| `android/`（整个目录） | 根目录 | 上传安卓工程：`app/`、`build.gradle.kts`、`settings.gradle.kts`、`gradle.properties`、`.gitignore` |

### 本次要覆盖替换的文件

| 文件 | 放到 | 为什么要换 |
| --- | --- | --- |
| `README.md` | 根目录 | 改为双端唯一入口，删掉"另有安卓版"的割裂表述 |
| `NOTICE.md` | 根目录 | 合并安卓端依赖 |
| `使用说明.txt` | 根目录 | 精简为随 exe 分发的简版，详细内容移入 `docs/01` |
| `pdfmask.py` | 根目录 | Windows 1.4.0 源码 |
| `version_info.txt` | 根目录 | 版本号 1.4.0 |
| `dev/sync_url.py` | `dev/` | 地址同步范围扩到 `docs/*.md` |

### 已经从仓库里移除的文件

| 文件 | 原因 |
| --- | --- |
| `dev/README.md` | 内容并入 `docs/05-构建与发布.md`，避免同一份脚本说明两头维护 |
| 安卓工程里的 `README.md`、`NOTICE.md`、`LICENSE` | 安卓不单独持有文档与协议，统一用根目录的 |

### 绝对不要上传的东西

- `android/app/build/`、`android/.gradle/`、根目录 `build/`、`dist/`（构建产物，体积大且无意义）
- `android/keystore.properties`、`android/pdfmask-release.jks`、`android/local.properties`（**含签名密码，泄露就等于把发布权交出去**）
- `test/`（生成的测试 PDF）
- `__pycache__/`、`dev/_ui/`、`*.log`

### 网页界面一步步怎么点

**A. 先放文档（手工新建，逐个粘贴）**

1. 打开 `https://github.com/neurotracee/pdf-privacy-masker`。
2. 右上「Add file」→「Create new file」。
3. 文件名填 `CHANGELOG.md`，正文粘贴本地 `CHANGELOG.md` 全文 → 底部「Commit changes」。
4. 同样方式新建 `DOCS.md`。
5. 建 `docs/` 下的文件时，文件名输入框直接写 `docs/01-使用说明-Windows.md`（带斜杠会自动建目录），依次建 01 ~ 05 五篇。

**B. 再放图片与替换文档（上传）**

1. 进 `docs/img/` 目录 →「Add file」→「Upload files」→ 拖入模板里的 `img` 全部图片。
2. 回仓库根目录 →「Add file」→「Upload files」→ 拖入要覆盖的 `README.md`、`NOTICE.md`、`使用说明.txt`、`pdfmask.py`、`version_info.txt`（同名即覆盖）。
3. `dev/sync_url.py` 进 `dev/` 目录同样上传覆盖。

**C. 最后放安卓工程**

1. 仓库根目录 →「Add file」→「Upload files」。
2. 把本地 `android` **整个文件夹拖进**上传区（Chrome / Edge 支持拖文件夹，会保留子目录结构）。
3. 上传前肉眼确认拖进去的内容里**没有** `build`、`.gradle`、`*.jks`、`keystore.properties`、`local.properties`。
4. 分支选 `main`，Commit message 写「add android source」，提交。

> 如果网页一次拖太多文件失败，按 `android/app/src/main/java/...`、`android/app/src/main/res/...`、`android/app/src/test/...`、根级三个 gradle 文件分四批上传，路径保持一致即可。

**D. 发 Release（安装包）**

1. 仓库右侧「Releases」→「Draft a new release」。
2. Tag 填 `v1.4.0`，标题 `v1.4.0`。
3. 说明直接从 `CHANGELOG.md` 复制这一版的内容。
4. 附件上传 `PDFPrivacyMasker-1.4.0.exe` 与 `PDFPrivacyMasker-1.4.0-arm64.apk`——**文件名一个字符都不要改**，检查更新靠它读版本号。
5. 发布后，两端各点一次「检查更新」验证。

---

## 7. 交给 AI 操作时怎么说

把这段直接给 AI，它就不会乱翻文件：

> 仓库中有三个入口文件：`README.md`（项目总览）、`CHANGELOG.md`（版本升级说明）、`DOCS.md`（文档地图）。
> 需要改功能说明时，先读 `DOCS.md` 第 3、4 节的索引定位到具体文件，再改那一个文件，不要同时改多处。
> 安卓端没有独立 README，安卓相关说明只写在 `README.md` 和 `docs/02-使用说明-安卓.md`。
> 上传文件时严格遵守 `DOCS.md` 第 6 节的路径清单，构建产物与签名文件一律不上传。

---

## 8. 以后加文档的约定

1. **一个主题一个文件**，不新建"补充说明""再说两句"这类文件，直接改对应那一篇。
2. 新增的说明性文档一律放进 `docs/`，按 `NN-标题.md` 编号，并回到本文件第 2、5 节登记一行。
3. 面向用户的步骤（怎么点、点哪里）写在 `docs/01`、`docs/02`；面向开发者的命令写在 `docs/05`；两不混。
4. 版本相关的内容只写进 `CHANGELOG.md`，其他文件里不要再写"本次更新……"。
