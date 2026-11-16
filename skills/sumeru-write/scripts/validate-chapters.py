#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节文件校验工具
功能：校验 chapters/ 下章节文件的命名规范、编号重复与缺失，并可与章节细纲核对
用法：python3 validate-chapters.py [--dir chapters] [--outline .sumeru/outline/chapter-outlines.json] [--json]
退出码：0 = 全部通过；1 = 存在问题；2 = 参数或环境错误
"""

import argparse
import json
import re
import sys
from pathlib import Path

NAME_PATTERN = re.compile(r'^(\d{3,4})-([^\\/:*?"<>|]+)\.md$')
IGNORED_FILES = {"WRITE_PROGRESS.md", "README.md"}


def load_outline_numbers(outline_path):
    """读取章节细纲中的章节号列表"""
    data = json.loads(Path(outline_path).read_text(encoding="utf-8"))
    numbers = set()
    for chapter in data.get("chapters", []):
        number = chapter.get("chapterNumber")
        if isinstance(number, int):
            numbers.add(number)
    return sorted(numbers)


def validate(chapters_dir, outline_path=None):
    directory = Path(chapters_dir)
    if not directory.is_dir():
        raise FileNotFoundError(
            "章节目录不存在: {}。请先运行 sumeru-write 生成章节，或用 --dir 指定目录".format(chapters_dir))

    result = {
        "directory": str(directory),
        "valid_files": 0,
        "invalid_names": [],
        "empty_files": [],
        "duplicate_numbers": [],
        "mixed_width": False,
        "missing_chapters": [],
        "extra_chapters": [],
        "outline_checked": False,
    }
    seen = {}
    widths = set()

    for file in sorted(directory.iterdir()):
        if not file.is_file() or file.name.startswith(".") or file.name in IGNORED_FILES:
            continue
        match = NAME_PATTERN.match(file.name)
        if not match:
            result["invalid_names"].append(file.name)
            continue
        number = int(match.group(1))
        widths.add(len(match.group(1)))
        seen.setdefault(number, []).append(file.name)
        result["valid_files"] += 1
        if not file.read_text(encoding="utf-8").strip():
            result["empty_files"].append(file.name)

    for number, names in sorted(seen.items()):
        if len(names) > 1:
            result["duplicate_numbers"].append({"chapter": number, "files": names})
    result["mixed_width"] = len(widths) > 1

    numbers = sorted(seen.keys())
    if outline_path and Path(outline_path).is_file():
        expected = load_outline_numbers(outline_path)
        result["outline_checked"] = True
        result["missing_chapters"] = [n for n in expected if n not in seen]
        result["extra_chapters"] = [n for n in numbers if n not in expected]
    elif numbers:
        result["missing_chapters"] = [n for n in range(numbers[0], numbers[-1] + 1) if n not in seen]

    result["ok"] = not (
        result["invalid_names"] or result["empty_files"] or result["duplicate_numbers"]
        or result["mixed_width"] or result["missing_chapters"] or result["extra_chapters"])
    return result


def print_report(result):
    print("章节目录: {}，合规章节文件 {} 个".format(result["directory"], result["valid_files"]))
    if not result["outline_checked"]:
        print("提示: 未找到章节细纲，仅检查编号是否连续")
    if result["invalid_names"]:
        print("命名不合规（应为 三位或四位章节号-标题.md）: " + "、".join(result["invalid_names"]))
    if result["empty_files"]:
        print("内容为空: " + "、".join(result["empty_files"]))
    for item in result["duplicate_numbers"]:
        print("章节号重复: 第{}章 -> {}".format(item["chapter"], "、".join(item["files"])))
    if result["mixed_width"]:
        print("章节号位数不统一（三位与四位混用），请统一补零位数")
    if result["missing_chapters"]:
        print("缺失章节: " + "、".join(str(n) for n in result["missing_chapters"]))
    if result["extra_chapters"]:
        print("细纲中不存在的章节: " + "、".join(str(n) for n in result["extra_chapters"]))
    print("校验通过" if result["ok"] else "校验未通过，请按以上提示处理")


def main():
    parser = argparse.ArgumentParser(description="章节文件命名与完整性校验")
    parser.add_argument("--dir", "-d", default="chapters", help="章节目录 (默认: chapters)")
    parser.add_argument("--outline", "-o", default=".sumeru/outline/chapter-outlines.json",
                        help="章节细纲路径，存在时用于核对缺失/多余章节")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args()

    try:
        result = validate(args.dir, args.outline)
    except (OSError, ValueError) as error:
        print("执行出错: {}".format(error), file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_report(result)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
