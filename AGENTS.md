# AGENTS.md — 接手必读（5 分钟，别跳）

> 给**新会话 / 新平台 / 换了个 Agent** 用的入口，不是给用户的说明书。
> 目的只有一个：不靠翻 README 和工作区快照，也能马上知道「这是什么项目、现在到哪一步、
> 这次该干什么、哪些不许碰」。
>
> 适用于任何能读仓库文件的 Agent（Claude Code / Codex / Cursor / Copilot / 其它）。
> Windows、Linux、macOS 上路径与命令写法通用（命令差异另注）。

## 1. 读什么（按顺序，别整仓扫描）

| 顺序 | 文件 | 用时 | 读到什么 |
| --- | --- | --- | --- |
| 1 | `.agent/STATE.md` | 20 秒 | 版本、分支、最新 tag、最近 5 次提交、CI。**自动生成，永远是最新的** |
| 2 | `.agent/HANDOVER.md` | 1 分钟 | 最上面 3 条：上一段工作干到哪、有没有半截活 |
| 3 | `.agent/CONTEXT.md` | 2 分钟 | 产品背景、代码分层、踩过的坑、测试入口 |
| 4 | 本文件第 2、3 节 | 30 秒 | 这次的职责边界与硬约束 |
| 5 | **只打开本次任务相关的文件** | — | 用 grep 定位，不要通读整个仓库 |

`README.md` 是给用户看的宣传与使用说明，**不是交接材料**；除非任务就是改它，否则不用读。

## 2. 当前角色边界（本对话的约定）

**本角色 = 功能升级维护 + bug 修复。**

不做（除非当次消息明确要求）：

- README / 文档措辞、配图、截图脚本
- Release 正文、附件上传、版本号与发版流程
- 零散新功能、界面美化、体验优化

碰到这些范围外的事：**不要顺手做**。在 `.agent/HANDOVER.md` 记一行
`- 遗留 / 待另开：xxx（不属于本角色）`，然后交回用户决定。

边界之外还有一条：**别把「已知限制」当 bug 修**。扫描件识别精度、旋转页、表格错位、
OCR 漏认这几类，`docs/03-识别规则与已知限制.md` 里写明了边界，先看再判断。

## 3. 硬约束（违反会直接翻车）

1. **版本号三处一致**：`pdfmask.py` 的 `VERSION`、`android/app/build.gradle.kts` 的
   `appVersionName`、`version_info.txt` 的 `filevers` + `FileVersion`。改一处就要改三处。
2. **发版必须两端同时出包**（Windows + 安卓），不许只发一端；Linux AppImage 由 CI 出。
3. **识别规则改动两端一起改**，并跑 `RuleParityTest` / `dev/selfcheck.py`，基线是
   `test/rules_golden.json`（生成物，勿手改）。
4. **原 PDF 只读**：不覆盖、不改名、不删除用户文件。
5. **不引入联网依赖、不接云端模型**：离线是本产品的承诺。
6. **不擅自 Commit 到发布分支后直接发版**；提交可以，发版要用户点头。

## 4. 命令速查

| 做什么 | 命令 |
| --- | --- |
| 从源码跑 | `pip install -r requirements.txt` → `python pdfmask.py` |
| 命令行批量 | `python pdfmask.py --cli 输入.pdf 输出.pdf` |
| OCR 自检 | `python pdfmask.py --ocr-check` |
| 打包 exe | 双击 `打包.bat`，或 `pyinstaller pdfmask.spec --noconfirm` |
| Python 自检 | `python dev/selfcheck.py` |
| 安卓编译 | **在 PowerShell 里** `cd android` → `gradle assembleRelease`（无 wrapper，用系统 Gradle 8.7；Git Bash 下 AAPT2 会失败） |
| 安卓规则对齐测试 | `cd android; gradle test`（`app/src/test/.../RuleParityTest.kt`） |
| 刷新事实快照 | `python dev/agent_state.py` |

## 5. 上下文与额度成本（硬性执行，不因为任务小就跳过）

免费积分额度有限（历史上出现过月底提前耗尽），所以**读得少、说得准**本身就是交付质量的一部分。
以下规则每次都执行，哪怕这次只改一个文件、看起来用不上：

- 会话开头只读第 1 节那三份，**不通读 README、不通读 docs/**。
- 需要背景就 grep 关键词 + 定位到函数，**不要整文件 dump**。
- 同一个判断只问一次；用户已经给过的偏好、已经写在本文件里的规则，**直接照做，不重复确认**。
- 失败重试**最多 3 次**，第三次不通就停下来报原因、给替代方案，不无脑刷。
- 交接条目 ≤ 5 行，事实快照交给脚本生成，不手写、不复述 git log。

## 6. 交接怎么做（每次会话结束前 2 分钟）

1. `python dev/agent_state.py` —— 刷新 `.agent/STATE.md`（版本、tag、提交、CI 自动更新）。
2. 往 `.agent/HANDOVER.md` **最上面**加一条（模板在文件头，5 行以内）：
   做了什么 / 改了哪些文件 / 怎么验证的 / 遗留或待另开。
3. 如果某条信息**长期有效**（新踩的坑、新的硬约束、新的边界），别写在 HANDOVER 里，
   写进 `.agent/CONTEXT.md` 对应小节。
4. 到此为止。不要为了「留痕」写长篇总结——真正的过程在 `git log` 里。

## 7. 三个文件的分工（别写串）

| 文件 | 谁维护 | 会变吗 | 写什么 |
| --- | --- | --- | --- |
| `.agent/STATE.md` | 脚本 | 每次刷新 | 版本、分支、tag、提交、CI、规模 |
| `.agent/HANDOVER.md` | Agent | 每会话一条 | 一次性的经过与遗留 |
| `.agent/CONTEXT.md` | 人 | 很少 | 架构、坑、测试入口、长期边界 |
