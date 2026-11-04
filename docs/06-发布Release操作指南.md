# 发布 Release 操作指南（网页点击版，不用命令行）

> 这份文件只解决一件事：**把 v1.4.2 放到 GitHub 的 Releases 页面上，并保证两端「检查更新」能读到。**
> 写这份的时候线上只有 `v1.3.0` 一个 Release，附件叫 `PDF.exe`（旧命名，没有版本号、也不是 apk）；1.4.0 / 1.4.1 都没单独发过。如果你已经把 1.4.1 发出去了，那下面流程一样，只是线上从 1.4.1 升到 1.4.2。
>
> **这一版有个新东西要先知道**：程序启动会自动检查更新，提醒力度（建议 / 强烈建议）由发布正文第一行的标记决定，两档都能关掉（见第二节「第 4 步 前半」与第八节）。

你已经备好的东西在 `release/v1.4.2/`：

| 文件 | 用途 | 大小 |
| --- | --- | --- |
| `PDFPrivacyMasker-1.4.2.exe` | Windows 安装包，**上传** | 34.08 MB |
| `PDFPrivacyMasker-1.4.2-arm64.apk` | 安卓安装包，**上传** | 14.14 MB |
| `RELEASE-NOTES.md` | Release 正文，**复制粘贴** | — |
| `SHA256SUMS.txt` | 校验和，**可选上传**，给愿意核对的人用 | — |

`RELEASE-NOTES.md` 不要上传，它是给你复制正文用的。

**已代你核对过的**：exe 的文件属性版本是 `1.4.2.0`、产品版本 `1.4.2`；两个包的 SHA256 与 `SHA256SUMS.txt` 完全一致；拿真实文件名试跑版本解析，`PDFPrivacyMasker-1.4.2.exe` 与 `PDFPrivacyMasker-1.4.2-arm64.apk` 都正确读出 `1.4.2`，而旧的 `PDF.exe` 读不出任何版本（所以它不会干扰新版本判断）。

---

## 一、先记住顺序：源码在前，Release 在后

Release 的 tag 会指向仓库当时的代码。如果先发 Release、后传源码，`v1.4.2` 这个 tag 指向的还是旧代码，AGPL 要求的"提供能构建出该安装包的完整源码"就不成立。

**这一版必须先传代码**：上一版代码已经在仓库里，但 1.4.2 又改了若干源码与文档（清单见第六节）。如果先发 Release、后传代码，`v1.4.2` 这个 tag 指向的还是旧代码，AGPL 要求的"提供能构建出该安装包的完整源码"就不成立。

判断源码是否到位：打开根目录的 `pdfmask.py`，搜 `VERSION = "1.4.2"`；再打开 `android/app/build.gradle.kts`，应该看到 `versionName = "1.4.2"`。

---

## 二、建 Release（6 步）

全部在浏览器里点。

### 第 1 步 打开新建页

两种入口，效果一样：

- 直接打开：`https://github.com/neurotracee/pdf-privacy-masker/releases/new`
- 或从仓库首页右侧点「Releases」→ 右上角「Draft a new release」

### 第 2 步 填 tag

看到「Choose a tag」按钮，点它，在输入框里敲：

```
v1.4.2
```

下方会出现一条 **「Create new tag: v1.4.2 on publish」**，点它选中。
右边「Target」保持 `main` 不动。

> 为什么强调 `v`：程序优先从附件文件名读版本，读不到才退回 tag。tag 写成 `1.4.2` 也能认，但仓库里已有 `v1.3.0`，统一带 `v` 更省事。

### 第 3 步 填标题

「Release title」里填：

```
v1.4.2 修复赞赏码保存 · 双端同版本
```

### 第 4 步 粘贴正文（第一行决定「建议更新」还是「强烈建议更新」）

用记事本或任意编辑器打开 `release/v1.4.2/RELEASE-NOTES.md`，**全选复制**，粘到「Describe this release」大框里。
表格、列表、锚点链接都能正常显示，不用改。

> 正文是**中英双语**：中文在前，第二行是 `**中文** ｜ [English ↓](#english)`。
> 英文版在 `## English` 标题下面，`English ↓` 是页内锚点，点了会直接跳到英文段；英文段顶部的 `[中文 ↑](#中文版)` 跳回中文。
> **一整份一起粘**，不要只粘中文——少了下半段，`English ↓` 就成了死链。

**正文第一行是给程序读的标记：**

```
更新级别：建议
```

- 保持「建议」→ 蓝色提醒，用户点「暂不更新」先被劝一句，再点一次就放行；
- 改成 `更新级别：强烈建议` → 橙红提醒、话更重，挽留也更强，但**照样能关**；
- 整行删掉 → 按「建议」处理。

两档都不拦路：窗口右上角一直有 ×，挽留只有一次，第二次点就一定关得掉。

这一行**必须自己单独占一行、顶格写**。写在表格里、句子中间、或者用代码块包起来都不算——这是故意的，免得正文里举例说明时把所有人误判。

> RELEASE-NOTES 底部有一小段「不要粘」的提示，那一段自己会写明怎么改，粘的时候别把它一起框进去（多粘了也不影响，只是难看）。

### 第 5 步 传附件（最容易出错的一步）

找到「Attach binaries by dropping them here or selecting them」那块区域：

1. 打开文件夹 `C:\Users\YB\PDF隐私打码工具-开源包\release\v1.4.2\`
2. 选中 `PDFPrivacyMasker-1.4.2.exe` 和 `PDFPrivacyMasker-1.4.2-arm64.apk` 两个文件
3. 直接拖进那块区域（或点「selecting them」选这两个文件）
4. 等进度条走完，两个文件名出现在下方列表里

传完必须**逐字核对文件名**，这三个特征一个都不能少：

| 必须有 | 为什么 |
| --- | --- |
| 前缀 `PDFPrivacyMasker-` | 程序靠这个前缀 + 后缀来认定"这是本平台的包" |
| 中间 `1.4.2` | **版本号就是从这里读的**，没有它就会退回读 tag |
| exe 结尾 `.exe`、apk 结尾 `-arm64.apk` | Windows 只认 `.exe`，安卓只认 `.apk` |

**不要**用中文名（`PDF隐私打码工具.exe`）、不要带空格、不要改名成 `PDFPrivacyMasker-1.4.exe`（少一位，版本会被读成 1.4.2 但显示不严谨）。

`SHA256SUMS.txt` 想传就一起传，不传不影响任何功能。

### 第 6 步 检查两个勾选框，然后发布

页面底部有两个勾：

- **「Set as a pre-release」** —— **不要勾**
- **「Set as the latest release」** —— 保持默认（勾着就对）
- 「Save as draft」不要点

然后点绿色 **「Publish release」**。

> 为什么不能勾 pre-release：程序的检查更新会跳过草稿、但**不跳过**预发布；可「打开下载页」用的是 `/releases/latest`，GitHub 不把 pre-release 算作 latest，会把用户送到 v1.3.0 去。结果就是"提示有新版本，点开却下到旧版"。所以别勾。

---

## 三、发完当场自检（3 分钟）

### 检查 1：看接口里有没有 1.4.2 的两个包

浏览器打开：

```
https://api.github.com/repos/neurotracee/pdf-privacy-masker/releases
```

在最上面那一坨里找 `"tag_name": "v1.4.2"`，然后往下找 `"name":`，应该出现：

```
"name": "PDFPrivacyMasker-1.4.2.exe"
"name": "PDFPrivacyMasker-1.4.2-arm64.apk"
```

两个都在，且 `"draft": false`、`"prerelease": false`，就对了。

### 检查 2：下载页要落在 1.4.2

打开 `https://github.com/neurotracee/pdf-privacy-masker/releases/latest`，地址栏应该自动变成 `.../releases/tag/v1.4.2`。
如果还停在 `v1.3.0`，说明第 6 步勾了 pre-release，回去编辑取消。

### 检查 3：两端真点一次「检查更新」

- Windows：打开新 exe → 右上角「设置」→「版本与更新」→「检查更新」。当前版本 1.4.2，应该显示"已是最新版本"。
- 安卓：装 1.4.2 → 设置 →「版本与更新」→「检查更新」，同样显示已是最新。

这一步的真正意义是**反向验证命名对不对**：如果 Windows 报"仓库里还没有适用于本平台的安装包"，就是 exe 名字里没有被认出的版本；如果显示"发现新版本 1.3.0"，就是附件名解析乱了。

---

## 四、发布后想改什么，怎么改

| 想改 | 怎么做 |
| --- | --- |
| 正文写错了 | Releases 页面右上「编辑」铅笔图标 → 改正文 → 「Update release」。不用重新传包 |
| 附件传错了 / 想换 | 编辑页面附件右上角有删除（垃圾桶）图标，删掉再拖新的进去。**删了旧附件，旧直链会 404**，但检查更新走接口、不受影响 |
| 忘了传 apk | 编辑页面同一处继续上传即可，不用重新发版 |
| tag 写成了 `v1.4` | 只能删掉整个 Release 重建（tag 会跟着删）。所以第 2 步慢一点 |
| 想撤回整版 | 编辑页面底部「Delete this release」。tag 会留着，需要另外去 Tags 里删 |

---

## 五、老 v1.3.0 那个 `PDF.exe` 要不要改名

**结论：不用改，也别改。**

理由：

1. 程序读版本时按"文件名里有没有版本号"过滤，`PDF.exe` 里读不出 `x.y.z`，会被直接跳过，不会盖住 1.4.2。
2. 那个文件名是当初分享出去的，可能已经有人在用直链下载；改名会让旧链接 404。
3. 它在页面上留着反而是历史记录，v1.3.0 的正文里也写着这个文件名。

以后每一版都按 `PDFPrivacyMasker-<版本>.exe` / `PDFPrivacyMasker-<版本>-arm64.apk` 命名就不会再出现这个问题。规则已写进 `docs/05-构建与发布.md` 第 4.1 节。

---

## 六、本次（1.4.2）要传的源码与文档清单

发 Release 时附件只认安装包，但 **tag 会指向当时的代码**，所以这一版必须先把下面的改动传上去，再发 Release。共 18 个文件：1 个新增、17 个覆盖。

### 新增（网页上「Add file → Create new file」，文件名框带斜杠会自动建目录）

| 文件 | 说明 |
| --- | --- |
| `android/app/src/main/java/com/neurotracee/pdfmask/ui/AutoUpdate.kt` | 启动自动检查更新的窗口与流程（检查中 / 超时 / 有新版三态） |

### 覆盖（「打开文件 → 右上铅笔 → 全选删掉 → 粘贴本地全文 → Commit changes」）

**Windows 端**

| 文件 | 改了什么 |
| --- | --- |
| `pdfmask.py` | VERSION 1.4.2；更新级别解析（`_update_strong`，行首标记）；`_parse_releases`/`check_update` 返回 `strong`；启动自动检查窗口（含一次性挽留）；关于窗加 Star 卡片与国内赞赏说明 |
| `version_info.txt` | exe 文件属性 1.4.2.0 / 1.4.2 |

**安卓端**

| 文件 | 改了什么 |
| --- | --- |
| `android/app/build.gradle.kts` | versionCode 9 / versionName 1.4.2 |
| `android/app/src/main/java/com/neurotracee/pdfmask/App.kt` | 启动时挂上 `AutoUpdateGate()` |
| `android/app/src/main/java/com/neurotracee/pdfmask/Updater.kt` | `Result.strong`、`isStrongUpdate()`（行首标记 + 多行模式） |
| `android/app/src/main/java/com/neurotracee/pdfmask/ui/AppInfoDialog.kt` | 关于页加 Star 卡片、国内赞赏说明、保存赞赏码按钮；隐私说明改为「启动一次 + 手动一次」 |
| `android/app/src/main/java/com/neurotracee/pdfmask/ui/SettingsDialog.kt` | 「启动时会自动查一次」提示 |
| `android/app/src/test/java/com/neurotracee/pdfmask/UpdaterTest.kt` | 更新级别标记 3 例（识别 / 不误判 / 跟随最新版本） |

**文档**

| 文件 | 改了什么 |
| --- | --- |
| `CHANGELOG.md` | 顶部新增 v1.4.2 一节 |
| `README.md` | 自动检查说明、权限与隐私口径、Star 引导 |
| `DOCS.md` | 版本号与索引 |
| `使用说明.txt` | 第四节日志、Star / 赞赏说明 |
| `docs/01-使用说明-Windows.md` | 第 4 节改为「自动检查 + 手动检查」 |
| `docs/02-使用说明-安卓.md` | 6.1 改为「打开就自动查」 |
| `docs/04-常见问题.md` | 新增 5 条自动更新问答 |
| `docs/05-构建与发布.md` | 版本号示例 |
| `docs/06-发布Release操作指南.md` | 本文件 |

**千万别传**：`release/`、`dist/`、`build/`、`test/`、`android/app/build/`、`android/keystore.properties`、`*.jks`、`local.properties`、`dev/_ui/`。

---

## 七、仓库里多出来的三个目录（建议清掉）

你之前用网页上传时，`.gitignore` 是拦不住网页上传的，所以线上多了三个本来不该进仓库的目录：

| 目录 | 是什么 | 建议 |
| --- | --- | --- |
| `test/` | 6 个测试用 PDF，其中有个叫 `测试文档_含隐私.pdf` | **建议删**。不是源码必需，名字还容易被误读成"仓库里有真实隐私样本" |
| `build/pdfsink/` | PyInstaller 打包的中间文件，约 1.5 MB、9 个文件 | 可删可不删，不影响功能 |
| `__pycache__/` | Python 编译缓存 | 可删可不删 |

删法：打开目录 → 点进文件 → 右上垃圾桶图标 → 「Commit changes」，一个文件一次。**麻烦且容易漏，所以不着急**；等下次有大改动要提交时一起处理更省事。真正要紧的是别再往上拖 `build/`、`test/`、`release/`、`keystore.properties`。

---

## 八、下次发版（1.4.3 之类）只要三步

1. 改三处版本号：`pdfmask.py` 的 `VERSION`、`version_info.txt` 两处、`android/app/build.gradle.kts` 的 `versionCode` 和 `versionName`。
2. 打包，把产物按 `PDFPrivacyMasker-<新版本>.exe`、`PDFPrivacyMasker-<新版本>-arm64.apk` 命名，放到 `release/<新版本>/`。
3. 回到本文第二节，把 `v1.4.2` 全部替换成新版本号，正文换成 `CHANGELOG.md` 新增的那一节——**别忘了第一行那句「更新级别：建议」**，删掉它等于按建议处理；想让提醒更重就写成 `更新级别：强烈建议`，但两档都关得掉。

> 小抄：想让某一版提醒更重，就把正文第一行改成 `更新级别：强烈建议`，别的话照常写。发完拿旧版打开一次：徽标是橙红色、标题是「强烈建议更新到 vX」，点「暂不更新」会多问一句——就是读到了；如果还是普通蓝标，说明那一行没顶格或被包进了代码块。

`CHANGELOG.md` 只往后加新节，**不要改旧节**——旧节对应的是别人已经下载过的版本，改了就对不上了。
