# STATE.md — 当前事实快照

> **自动生成，勿手改**：`python dev/agent_state.py`（2026-11-28 17:14）。
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

- 分支：`main`　工作区：1 个未提交改动
- 最新 tag：`v1.4.10.0`

## 最近 5 次提交

```
474f0a3  2026-11-28  chore(agent): 记录官网入口改动与快照
e0e734d  2026-11-28  feat(site): 加入官网 neurotracee.github.io/pdf-site
81cdd36  2026-11-28  docs(agent): 责任规则改为「主对话全包，其他会话一律不处理」
1df5c85  2026-11-28  docs(agent): 去掉 A/B 双线设定——所有工作都是同一个 Agent（当前对话）负责
52b77ed  2026-11-28  chore(agent): 刷新 STATE 快照
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
