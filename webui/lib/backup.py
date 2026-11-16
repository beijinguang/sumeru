#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""webui 章节保存自动备份（与 AGENTS.md 全局备份规则对齐）。

规则：
  - original/ 只保存每章的最初原稿：已存在同名文件时不再覆盖
  - 每次修改前的当前版本另存到 history/save-{时间戳}/，可逐级回滚
"""

import shutil
from datetime import datetime
from pathlib import Path

ORIGINAL_DIR = "original"
HISTORY_PREFIX = "save-"


def backup_before_write(chapters_dir, filename, dot_sumeru=None):
    """按规则备份 chapters_dir/filename。

    dot_sumeru: .sumeru 目录路径（默认 chapters_dir 所在目录/.sumeru）。
    返回 {"original": str|None, "history": str|None}。
    """
    src = Path(chapters_dir) / filename
    if not src.is_file():
        return {"original": None, "history": None}

    write_root = (Path(dot_sumeru) if dot_sumeru else src.parent.parent / ".sumeru") / "write"
    original_dir = write_root / ORIGINAL_DIR
    history_dir = write_root / f"{HISTORY_PREFIX}{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"

    result = {"original": None, "history": None}
    original_target = original_dir / filename
    if original_target.exists():
        # original 只保存最初原稿：已存在则不覆盖，仅回指既有文件
        result["original"] = str(original_target)
    else:
        original_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, original_target)
        result["original"] = str(original_target)

    history_dir.mkdir(parents=True, exist_ok=True)
    history_target = history_dir / filename
    shutil.copy2(src, history_target)
    result["history"] = str(history_target)
    return result
