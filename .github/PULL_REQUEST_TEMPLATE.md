<!--
  一个 PR 只做一件事。真要顺手清理无关代码，请单独提一个 PR。
  下面几项填完再提交，比事后补充省时间。
-->

## 改了什么

<!-- 一两句话。比如「地址识别支持『XX 区 XX 街道』这种不带门牌号的写法」 -->

## 为什么改

<!-- 解决什么麻烦、对应哪个 issue（写 #编号）。没有 issue 的话，说明你是怎么发现这个问题的。 -->

## 怎么验证的

<!--
  贴结果，别只说「测过了」。改代码基本都要跑这个：

      python dev/selfcheck.py

  最后一行应该是「自检结论: 全部通过」。
-->

```
（把 selfcheck 的结尾几行贴这里）
```

## 影响哪一端

- [ ] Windows
- [ ] 安卓
- [ ] 两端（规则改了通常都是两端）

## 提交前自查

- [ ] 跑过 `python dev/selfcheck.py`，全部通过
- [ ] 改的是识别规则 → 跑过 `python dev/test_no_false_positive.py`，误报没变多
- [ ] 改的是更新检查 / 版本解析 → 跑过 `dev/test_source_pick.py` 与 `dev/test_release_digest.py`，且 Python 与 Kotlin 两份实现已同步
- [ ] 改的是安卓 → 跑过 `gradle testReleaseUnitTest`
- [ ] 界面文案改了 → 中文和英文都改了，`README.md` / `docs/` 的同一处说法也跟着改了
- [ ] 加了依赖 → 更新过 `requirements.txt`（或 `build.gradle.kts`）与 `NOTICE.md`，并确认许可兼容
- [ ] 没有提交 `dist/`、`build/`、`release/`、签名文件、本机路径配置
- [ ] 没有改版本号（版本号统一在发版时改）

## 截图 / 效果对比（界面改动建议附上）

<!-- 打码效果改动请附上「改之前 / 改之后」两段文字打码后的样子，最好带上为什么这样更合理 -->
