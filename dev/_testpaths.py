# -*- coding: utf-8 -*-
"""dev/ 下脚本共用的路径约定。

`test/` 里只放**应当进仓库**的固定样本；跑测试产生的输出一律写到临时目录，
免得每次自检都往工作区里丢一堆 pdf/png，把 `git status` 弄脏。

- IN_DIR  : 仓库里的样本目录（只读）
- OUT_DIR : 输出目录。设置环境变量 PDFMASK_TEST_DIR 可指定，
            否则由调用方（selfcheck）传一个临时目录进来。
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
IN_DIR = os.path.join(ROOT, "test")
OUT_DIR = os.environ.get("PDFMASK_TEST_DIR") or IN_DIR


def inp(*names):
    """仓库内固定样本的路径"""
    return os.path.join(IN_DIR, *names)


def out(*names):
    """本次运行的输出路径（默认仍是 test/，但 selfcheck 会指到临时目录）"""
    p = os.path.join(OUT_DIR, *names)
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    return p
