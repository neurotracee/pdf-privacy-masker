# STATE.md — 当前事实快照

> **自动生成，勿手改**：`python dev/agent_state.py`（2026-11-28 15:13）。
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
1df5c85  2026-11-28  docs(agent): 去掉 A/B 双线设定——所有工作都是同一个 Agent（当前对话）负责
52b77ed  2026-11-28  chore(agent): 刷新 STATE 快照
73d3ffe  2026-11-28  docs(agent): 修正分工表述——两条线并行，README/Release 有明确负责人
19eeca7  2026-11-28  chore(agent): 刷新 STATE 快照（工作区干净）
09afbdc  2026-11-28  docs(agent): 建立跨会话/跨平台交接层（AGENTS.md + .agent/ 三件套 + 快照脚本）
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
