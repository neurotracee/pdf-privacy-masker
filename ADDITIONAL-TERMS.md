# 附加条款 · Additional Terms

本文件是「PDF 隐私打码工具」依据 **GNU AGPL-3.0 第 7 条 (b) 项** 制定的附加条款，
与本项目一起构成完整的授权条件。

凡复制、分发、修改、打包本项目（含编译后的 exe），即视为接受下列条款。
如果你不接受，请不要使用本项目的代码。

---

## 一、必须保留的三样东西

**1. 作者署名**
下面两句原文保留，不得删除、不得改写、不得替换成其他人的名字：

```
指导作者：项目创作时为初中生
由 腾讯 WorkBuddy × DeepSeek-V4.1-Flash 开发
```

**2. 原项目地址**
必须让程序的使用者**看得见**这个地址：

```
https://github.com/neurotracee/pdf-privacy-masker
https://gitee.com/bio234/pdf-privacy-masker      （国内镜像，两处写任一处或都写均可）
```

（具体放在哪里算数，见第二节。地址写了就行，不要求做成链接。）

**3. 修改说明**
如果你改过代码、改过界面、改过功能，必须在程序里**显著注明**：

> 本程序基于 https://github.com/neurotracee/pdf-privacy-masker
> （镜像：https://gitee.com/bio234/pdf-privacy-masker）修改，非原作者发布。

这一条是为了避免别人误以为改动后的版本是原作者做的——尤其是当你的版本有 bug、
有隐私风险、或者开始收费的时候。

---

## 二、地址放在哪里算数

以下**任何一处**做到就算合规，不用全都做：

| 位置 | 说明 |
| --- | --- |
| 程序的「关于」窗口 | 最省事。原版已经有这几行，别删就行。 |
| 首页 / 启动页的页脚 | 一行小字也可以。 |
| 菜单栏「帮助 → 关于」 | 桌面软件通用做法。 |
| 命令行 `--about` 的输出 | 如果你的版本只有命令行。 |
| 随附文档的第一屏 | 仅限没有图形界面的情况；有界面就必须放界面里。 |

**只有一处不算数**：把地址埋在 `LICENSE` 文件或几百行之外的源码注释里，
使用者正常操作时根本看不到——这不算「让使用者看得见」。

---

## 三、商业使用

**可以商用。** 本条款不禁止你卖钱、不禁止你在公司内部用、不禁止你拿它做服务收费。
这是 AGPL-3.0 本来就允许的，作者也没有加任何「禁止商用」的限制
（加了也无效，反而会让整个授权失效）。

但商用必须同时满足：

- 上面第一节的三条（署名 + 地址 + 修改说明）；
- **AGPL-3.0 第 13 条**：如果你把它改成网络服务让别人通过浏览器使用，
  必须向这些使用者提供**完整对应源代码**的获取方式；
- AGPL-3.0 第 6 条：分发 exe 时，必须一并提供可编译出该 exe 的源代码。

想闭源商用？那需要**同时**做两件事：向本项目的作者取得豁免（作者维护频率很低，
一两个月才看一次，大概率不会回应，请不要指望），以及向 PyMuPDF 的版权方 Artifex 购买商业许可
（这是硬约束，见 `NOTICE.md`）。不要试图绕过。

---

## 四、不需要做的事

- ❌ 不需要付钱给作者
- ❌ 不需要发邮件、不需要等作者批准、不需要在 issue 里报备
- ❌ 自己改着自己用、不发给别人，**不需要公开任何东西**（AGPL 只在"分发"和"提供网络服务"时才生效）
- ❌ 不需要保留作者的 bug、界面、功能——改得面目全非也行，只要署名和地址还在

---

## 五、作者的态度（说实话）

写这条不是为了找谁的麻烦，就是为了**留个名**。

作者平时没有充足的时间和精力，大约一两个月才上来看一两次，也不会去追着谁打官司——没那个功夫。

所以这条款的实际意义是：

- 给**守规矩的人**一个明确依据：照着做，你不用问任何人，也不用担心哪天被找上门；
- 给**想抹掉来源的人**一个明确态度：这件事是明确不被允许的，不是"没人管所以随便"。

法律上真正兜底的是 AGPL-3.0 本身的 copyleft 效力和著作权法，这条附加条款是在它
允许的范围内（第 7 条 b 项：要求保留合理的作者署名与法律声明）把话说明白。
如果你认为某处写法超出了 AGPL 允许的范围，以 AGPL-3.0 原文为准。

---

## 六、English Summary

This project is licensed under **AGPL-3.0-or-later**, with additional terms
under **Section 7(b)** of that license:

1. You must preserve the author attribution:
   `Advisor: was a junior high school student when this project was created` and
   `Developed by Tencent WorkBuddy × DeepSeek-V4.1-Flash`.
2. You must display the original project URL
   `https://github.com/neurotracee/pdf-privacy-masker`
   (mirror: `https://gitee.com/bio234/pdf-privacy-masker`)
   somewhere the end user can actually see it (an About dialog, footer, or `--about` output).
3. Modified versions must state clearly that they are modified, and must not
   imply endorsement by the original author.
4. The names "PDF 隐私打码工具" / "PDF Privacy Masker" and the application icon are
   **not** licensed (AGPL-3.0 Section 7(e)). Rename your fork.
5. Commercial use **is** permitted. If you run a modified version as a network
   service, AGPL-3.0 Section 13 requires you to offer the complete corresponding
   source code to its users.

These terms are additional permissions-style requirements allowed by AGPL-3.0 §7;
where this file is ambiguous, the AGPL-3.0 text prevails.
