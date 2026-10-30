#!/usr/bin/env python3
"""tree.md 双向一致门禁：文档结构树与实际跟踪文件互为镜像。

AI 时代文档最容易的腐坏方式不是「写错」，而是「没跟上」：
新增一个文件、删掉一个目录，代码提交了，tree.md 悄悄过期。
一份过期的结构说明比没有更危险——它会让下一个人（或下一轮对话）照着错误的地图动手。

本脚本做双向断言：
  - tree.md 列出的每个文件都必须真实存在（防虚构）
  - 每个被跟踪的源码文件都必须在 tree.md 中列出（防漏记）

目录项只做弱检查：目录下若没有任何被跟踪文件，视为产物/本地目录（如 local/、log/），
豁免存在性要求——CI checkout 后它们本来就不存在。

用法：
    python3 scripts/ci/check_tree_doc.py          # 校验，失败 exit 1
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TREE_DOC = Path("tree.md")

# 树形行：前缀由 4 字符一层的「│   」/「    」组成，末尾是「├── 」或「└── 」。
TREE_LINE_RE = re.compile(r"^((?:(?:│   |    )*)(?:├── |└── ))(.*)$")
# 目录树代码块：取 tree.md 里第一个裸 ``` 块。
FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.DOTALL | re.MULTILINE)


def tracked_files() -> list[str]:
    """返回 `git ls-files` 的文件列表。"""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def parse_tree() -> tuple[set[str], set[str]]:
    """解析 tree.md 的目录树，返回 (文件路径集合, 目录路径集合)。"""
    text = TREE_DOC.read_text(encoding="utf-8")
    fence = FENCE_RE.search(text)
    if fence is None:
        raise SystemExit(f"::error::{TREE_DOC} 中找不到目录树代码块（``` 围栏）")

    files: set[str] = set()
    directories: set[str] = set()
    stack: list[str] = []

    for raw in fence.group(1).splitlines():
        match = TREE_LINE_RE.match(raw)
        if match is None:
            continue
        depth = len(match.group(1)) // 4 - 1
        del stack[depth:]
        rest = match.group(2).strip()
        if not rest:
            continue
        # 取第一个空白分隔的 token 作为名字。本仓路径不含空格（ROS 命名惯例），
        # 因此不必依赖「名字与说明之间有多少空格」——对齐宽度可以自由调整。
        name = rest.split()[0]
        if not name:
            continue
        is_dir = name.endswith("/")
        clean = name.rstrip("/")
        path = "/".join([*stack, clean])
        if is_dir:
            directories.add(path)
            stack.append(clean)
        else:
            files.add(path)

    return files, directories


def main() -> int:
    documented_files, documented_dirs = parse_tree()
    actual = tracked_files()
    actual_set = set(actual)

    if not documented_files:
        print(f"::error::未能从 {TREE_DOC} 解析出任何文件项", file=sys.stderr)
        return 1

    failures: list[str] = []

    # 1) 文档列出但不存在：虚构或已删除未同步
    for path in sorted(documented_files - actual_set):
        failures.append(f"{TREE_DOC} 列出了不存在的文件：{path}")

    # 2) 实际存在但文档没记：新增未同步
    for path in sorted(actual_set - documented_files):
        failures.append(f"{TREE_DOC} 缺少已跟踪文件的记录：{path}")

    # 3) 目录项必须能落到真实内容上（产物目录豁免）
    covered = {path.rsplit("/", 1)[0] if "/" in path else "" for path in actual_set}
    for directory in sorted(documented_dirs):
        has_tracked = any(path.startswith(directory + "/") for path in actual_set)
        if not has_tracked and directory not in covered:
            print(
                f"::notice::{TREE_DOC} 的目录「{directory}/」下没有任何被跟踪文件，"
                "按产物目录豁免；若它应为源码目录则说明内容缺失。"
            )

    if failures:
        for failure in failures:
            print(f"::error::{failure}")
        print(
            f"\ntree.md 一致性校验失败：{len(failures)} 处。\n"
            "任何新增 / 删除 / 重命名文件，都必须在同一提交内更新 tree.md。",
            file=sys.stderr,
        )
        return 1

    print(
        f"tree.md 一致性校验通过：{len(documented_files)} 个文件、"
        f"{len(documented_dirs)} 个目录与仓库双向一致。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
