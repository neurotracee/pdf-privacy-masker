# HANDOVER.md — 交接记录（只追加，最新的在最上面）

> 用途：新会话 / 新平台接手时，**先看最上面 3 条**就知道「上一个人干到哪、有没有半截活」。
> 每条 5 行以内，写结果不写过程；过程在 git log 里，这里不重复。
> 只保留最近 8 条，更早的直接删掉——真正的历史看 `git log`，这里不是档案室。
> 写完记得 `python dev/agent_state.py` 刷新事实快照。

## 模板（复制这段改）

```
## YYYY-MM-DD · 主题
- 做了什么：
- 改了哪些文件：
- 怎么验证的：
- 遗留 / 待另开：
```

---

## 2026-11-28 · 文档与配图收尾（非功能）
- 做了什么：`version_info.txt` 固定版本号改齐 1.4.10.0；Windows 截图外壳从「假窗口」换成浏览器壳；26 张配图压了统一小字说明。
- 改了哪些文件：`version_info.txt`、`dev/make_readme_shots.py`、`dev/shot_note.py`（新增）、`docs/img/**`、`README.md`。
- 怎么验证的：`python dev/make_readme_shots.py --frames` 目视检查；三处版本号一致（见 STATE）。
- 遗留 / 待另开：已发布的 v1.4.10.0 exe 二进制里仍是 1.4.9.1，随下个版本自然生效，不为此重发。

## 2026-11-27 · 1.4.10.0 发版
- 做了什么：日志页重写（仿 GitHub 网络自检 APK 的日志页，卡片式、可查历史区间）、Wheel 时间选择器、`LogStore.readRange`；三端同步发版。
- 改了哪些文件：`android/.../ui/LogDialog.kt`、`LogStore.kt`、`ui/WheelTimePicker.kt`、`pdfmask.py`、`pdfmask_webui.py`、`version_info.txt`。
- 怎么验证的：真机安装试用；`dev/selfcheck.py`；两端 Release 六附件核对齐全。
- 遗留 / 待另开：AppImage 从这一版起由 `dev/fetch_appimage_accel.py` 自动搬运（Gitee 侧仍需确认是否走了自动流程）。
