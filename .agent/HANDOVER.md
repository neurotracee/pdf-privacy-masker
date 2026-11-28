# HANDOVER.md — 交接记录（只追加，最新的在最上面）

> 用途：新会话 / 新平台接手时，**先看最上面 3 条**就知道「上一个人干到哪、有没有半截活」。
> 每条 5 行以内，写结果不写过程；过程在 git log 里，这里不重复。
> 只保留最近 8 条，更早的直接删掉——真正的历史看 `git log`，这里不是档案室。
> 一次任务只做被要求的事。顺手发现但没做的，记 `- 本次未做，留待下次：xxx`——不是移交，只是记账。
> 写完记得 `python dev/agent_state.py` 刷新事实快照。

## 模板（复制这段改）

```
## YYYY-MM-DD · 主题
- 做了什么：
- 改了哪些文件：
- 怎么验证的：
- 本次未做，留待下次：
```

---

## 2026-11-28 · 修正交接层的「责任人」表述
- 做了什么：删掉「A 线 / B 线分属两条会话」的错误设定。现在写明：功能、bug、README / 配图、Release 与发版**全部由同一个 Agent（当前这条对话）负责**，没有并行的第二条会话。
- 改了哪些文件：`AGENTS.md`、`.agent/CONTEXT.md`、`.agent/HANDOVER.md`、`CLAUDE.md`、`.github/copilot-instructions.md`、工作区 `AGENTS.md`、工作区 `MEMORY.md`。
- 怎么验证的：四个入口文件搜「B 线 / 移交 / 另一条会话」均已无残留（工作区文件同步改）。
- 本次未做，留待下次：无。

## 2026-11-28 · 文档与配图收尾（非功能）
- 做了什么：`version_info.txt` 固定版本号改齐 1.4.10.0；Windows 截图外壳从「假窗口」换成浏览器壳；26 张配图压了统一小字说明。
- 改了哪些文件：`version_info.txt`、`dev/make_readme_shots.py`、`dev/shot_note.py`（新增）、`docs/img/**`、`README.md`。
- 怎么验证的：`python dev/make_readme_shots.py --frames` 目视检查；三处版本号一致（见 STATE）。
- 本次未做，留待下次：已发布的 v1.4.10.0 exe 二进制里仍是 1.4.9.1，随下个版本自然生效，不为此重发。

## 2026-11-27 · 1.4.10.0 发版
- 做了什么：日志页重写（仿 GitHub 网络自检 APK 的日志页，卡片式、可查历史区间）、Wheel 时间选择器、`LogStore.readRange`；三端同步发版。
- 改了哪些文件：`android/.../ui/LogDialog.kt`、`LogStore.kt`、`ui/WheelTimePicker.kt`、`pdfmask.py`、`pdfmask_webui.py`、`version_info.txt`。
- 怎么验证的：真机安装试用；`dev/selfcheck.py`；两端 Release 六附件核对齐全。
- 本次未做，留待下次：AppImage 从这一版起由 `dev/fetch_appimage_accel.py` 自动搬运（Gitee 侧仍需确认是否走了自动流程）。
