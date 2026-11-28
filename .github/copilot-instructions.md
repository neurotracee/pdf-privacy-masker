# Copilot 指路

接手约定写在仓库根目录 **[AGENTS.md](../AGENTS.md)**，请以它为准（约 5 分钟读完）。

顺序：`.agent/STATE.md`（自动生成的事实快照）→ `.agent/HANDOVER.md`（最近 3 条交接）
→ `.agent/CONTEXT.md`（背景、架构、已知坑），之后只打开本次任务相关文件。

分工：**没有分工**。功能、bug、README / 配图、Release 与发版都由同一个 Agent 负责，
不存在"另一条会话管这块"。`.agent/` 只是给新会话缩短理解路径。唯一的边界是：一次任务
只做被要求的那件事，别顺手扩范围。
