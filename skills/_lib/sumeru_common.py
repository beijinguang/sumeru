#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sumeru 各 Skill 脚本的公共工具（唯一实现，禁止在脚本内复制）。

使用方式（脚本顶部）：
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # skills/
    from _lib.sumeru_common import count_words, ...

仅依赖标准库。
"""

import re

# 「第X章 + 标题」标题行（analyze-book / check-derivative 等共用）
CHAPTER_TITLE = re.compile(r"^\s*(第[0-9零〇一二三四五六七八九十百千万两]+章[^\n]{0,40})$")
# 行首的「第X章」前缀（不计入正文字数）
TITLE_PREFIX = re.compile(r"^\s*第\s*\d+\s*章")
# 模板占位符（check-chapters / build 共用）
PLACEHOLDER = re.compile(r"(TODO|待补充|待完善|XXX|\[占位\])")


def count_words(text):
    """中文按字、英文按词；标点不计入（全项目统一口径）"""
    hanzi = len(re.findall(r"[\u4e00-\u9fa5]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return hanzi + english


def strip_title_line(text):
    """去掉文件内自带的「第X章 …」标题行（含前导空行），返回正文。

    统一字数口径：各工具统计正文字数前必须先经过本函数，
    保证 check-chapters / chapter-word-counter / build 给出一致字数。
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and TITLE_PREFIX.match(lines[0]):
        lines.pop(0)
    return "\n".join(lines)


def parse_int_range(value):
    """解析 '3000-4000' / 3000 / (3000,4000) 形式的字数建议，返回 (min, max) 或 None"""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return min(value), max(value)
    if isinstance(value, int):
        return value, value
    if not isinstance(value, str):
        return None
    nums = [int(n) for n in re.findall(r"\d+", value)]
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[:2]), max(nums[:2])
