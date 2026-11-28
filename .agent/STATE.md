# STATE.md — 当前事实快照

> **自动生成，勿手改**：`python dev/agent_state.py`（2026-11-28 14:59）。
> 想要长期有效的信息写 `.agent/CONTEXT.md`，一次性的经过写 `.agent/HANDOVER.md`。

## 版本

| 位置 | 值 |
| --- | --- |
| `pdfmask.py` VERSION | `1.4.10.0` |
| 安卓 `appVersionName` | `1.4.10.0` |
| `version_info.txt` FileVersion | `1.4.10.0` |
| `version_info.txt` filevers | `(1,4,10,0)` |

**三处是否对齐**：✅ 一致

## 仓库

- 分支：`main`　工作区：5 个未提交改动
- 最新 tag：`v1.4.10.0`

## 最近 5 次提交

```
19eeca7  2026-11-28  chore(agent): 刷新 STATE 快照（工作区干净）
09afbdc  2026-11-28  docs(agent): 建立跨会话/跨平台交接层（AGENTS.md + .agent/ 三件套 + 快照脚本）
b05b137  2026-11-28  docs(shots): 每张配图压一行小字，讲清截图/代码合成/AI 辅助，并注明以实际为准
b3e0963  2026-11-28  docs(shots): Windows 截图外框改为浏览器窗口，README 讲清是 127.0.0.1 本地页面
fa73deb  2026-11-28  fix(version): version_info 固定版本号改为 1.4.10.0，与 VERSION/安卓一致
```

## CI

- `.github/workflows/ci.yml`
- `.github/workflows/linux-appimage.yml`

## 规模

- Python 文件 61 个（Windows + Linux 同一套代码）
- Kotlin 文件 58 个（安卓原生实现）
- `docs/` 文档 6 篇

---

下一步该看什么：`.agent/HANDOVER.md` 最近 3 条 → `.agent/CONTEXT.md` → 命中文件。
