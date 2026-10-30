#!/usr/bin/env python3
"""文件卫生门禁：换行符、编码、末尾空行、行尾空白。

AGENTS.md「必须」里可机械判定的那半条：4 空格缩进 · LF · UTF-8 · 文件末尾一个空行。
本脚本只管后三项加行尾空白——**缩进不在这里查**：C/C++ 交给 clang-format（CI `lint-c`），
Python 交给 ruff/black（CI `lint-python`）。同一规则在两处实现，只会得到两套打架的答案。

用法：
    python3 scripts/ci/check_style.py          # 校验，失败 exit 1
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 已知二进制后缀：按字节比对而不是按文本解码。
# 未列出的后缀一律按文本检查——宁可让新类型文件被检查到，也不要静默跳过。
# 本仓的二进制主要是场地资产：官方地图 PGM/PCD、网格 STL/DAE、预览图 PNG，
# 以及 STEP 复核脚本导出的 gz 压缩中间件（maps/rmul_2027/step_geometry.json.gz）。
BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".pdf",
        ".pgm",
        ".pcd",
        ".stl",
        ".dae",
        ".obj",
        ".mtl",
        ".mesh",
        ".material",
        ".gz",
        ".bag",
        ".db3",
        ".mcap",
        ".so",
        ".a",
        ".o",
    }
)


def tracked_files() -> list[str]:
    """返回 `git ls-files` 的文件列表（仓根相对路径）。"""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def check_file(path: Path) -> list[str]:
    """检查单个文件，返回问题描述列表。"""
    problems: list[str] = []
    raw = path.read_bytes()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"{path}: 不是合法 UTF-8（{exc}）"]

    if b"\r\n" in raw:
        problems.append(f"{path}: 含 CRLF，本仓统一 LF")
    elif b"\r" in raw:
        problems.append(f"{path}: 含孤立 CR，本仓统一 LF")

    if b"\x00" in raw:
        problems.append(f"{path}: 含 NUL 字节，疑似二进制文件被列入文本检查")

    # 末尾必须恰好一个换行：少了是「文件末尾一个空行」不合规，
    # 多了是尾部空行堆积（git diff 噪音的主要来源之一）。
    if text and not text.endswith("\n"):
        problems.append(f"{path}: 文件末尾缺少换行")
    elif text.endswith("\n\n"):
        problems.append(f"{path}: 文件末尾有多余空行（应恰好一个换行）")

    for lineno, line in enumerate(text.splitlines(), start=1):
        if line != line.rstrip():
            problems.append(f"{path}:{lineno}: 行尾有空白字符")

    return problems


def main() -> int:
    failures: list[str] = []

    for name in tracked_files():
        path = Path(name)
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        if not path.is_file():
            continue
        failures.extend(check_file(path))

    if failures:
        for failure in failures:
            print(f"::error::{failure}")
        print(
            f"\n文件卫生校验失败：{len(failures)} 处。规则见 AGENTS.md「必须」。",
            file=sys.stderr,
        )
        return 1

    print("文件卫生校验通过（LF / UTF-8 / 末尾单空行 / 无行尾空白）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
