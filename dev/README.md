# dev/ —— 开发与测试脚本

这些脚本不参与打包，只是用来**生成测试文档**和**跑回归测试**。放在这里是为了让识别效果可以被任何人复现和验证。

## 怎么跑

所有脚本都在仓库根目录执行：

```bash
python dev/make_hard3_pdf.py 2026      # 生成「刁难文档 3.0」：5 页纯段落、20 个人物
python dev/test_hard3.py 2026          # 校验这份文档的识别与打码结果
```

脚本用随机种子生成内容，换个数字就是另一份文档：

```bash
python dev/test_hard3.py 2026 7 88231 5150
```

## 各脚本在做什么

| 脚本 | 作用 |
| --- | --- |
| `make_test_pdf.py` | 生成基础测试文档：一张表里堆满各类隐私信息 |
| `make_hard_pdf.py` | 刁难文档 1.0：隐私信息与干扰信息混排 |
| `make_hard2_pdf.py` | 刁难文档 2.0：纯段落、零标签、虚构人物 |
| `make_hard25_pdf.py` | 刁难文档 2.5：5 页、每页多人多号码、含表格 |
| `make_hard3_pdf.py` | 刁难文档 3.0：5 页纯段落、零表格、三字名占多数 |
| `selfcheck.py` | 主自检：端到端跑一遍，核对每一类信息的召回与残留 |
| `test_hard3.py` | 刁难 3.0 验收：按人物逐条核对姓名、号码、地址是否打掉 |
| `test_hard25.py` / `test_hard2.py` | 前两版刁难文档的验收 |
| `test_no_false_positive.py` | 纯净文档误报测试：不该打的地方一个都不能打 |
| `test_fp_extra.py` | 三种文体的误报测试（说明文 / 技术规范 / 公文通知 / 新闻通报） |
| `blind_test.py` | 随机盲测：随机造名 + 随机句式，统计召回率 |
| `probe_names2.py` | 姓名识别探针：200 个两字名 + 200 个三字名 × 16 种句式 |
| `test_exe.py` / `smoke_exe.py` | 对打包后的 exe 做端到端冒烟测试 |
| `test_save_dir.py` | 保存位置相关接口：指定目录、自动建目录、写入偏好文件、同名不覆盖 |
| `test_pickdir.py` / `test_pickdir_ok.py` | 系统原生「选择文件夹」对话框：能否弹出、能否取消、能否取回路径 |
| `make_ui_preview.py` | 把界面 HTML 注入假数据生成预览页，用来截图检查弹窗与勾选框 |
| `sync_url.py` | 改仓库地址后跑一次：把 `pdfmask.py` 里的 `PROJECT_URL` 同步进所有文档与 `version_info.txt` |
| `make_icon.py` | 生成程序图标 `app.ico` |
| `_testpaths.py` | 路径约定：`test/` 里只放固定样本，跑测试的产物一律写临时目录 |
| `gen_rules_golden.py` | 生成跨端一致性基准 `test/rules_golden.json`（Python 端的识别结果） |
| `test_scrub_notes.py` | 注释与书签清洗回归：涉敏批注被删、书签标题被打码、干净的不受影响 |

**产物不会进仓库**：`test/` 里只放应当进仓库的固定样本（生成脚本产出的「刁难文档」系列也在这里）。
跑测试产生的 pdf / png 一律写到系统临时目录，跑完 `git status` 是干净的。
想指定输出位置就设环境变量 `PDFMASK_TEST_DIR`。

## 跨端一致性

Windows 端（Python）和安卓端（Kotlin）是两套手写的识别逻辑，规则容易各走各的。
`test/rules_golden.json` 存着 Python 端在 `test/测试文档_含隐私.pdf` 上的识别结果，
安卓单元测试 `RuleParityTest` 用 PDFBox 读同一份 PDF、跑 Kotlin 的 `Detector`，
逐条比对 `page / type / text`。

改了识别规则之后：

```bash
python dev/gen_rules_golden.py            # 重新生成 Python 基准
cd android && ./gradlew :app:testDebugUnitTest --tests "*RuleParityTest*"   # 看安卓端是否跟上
```

## 测试文档里的人物都是虚构的

姓名、手机号、身份证号、地址全部由脚本随机拼出来，不对应任何真实的人。身份证号满足校验位规则，银行卡号满足 Luhn 规则，但都是随机生成的测试数据。
