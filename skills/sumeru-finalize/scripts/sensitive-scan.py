#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
敏感词词表扫描工具
功能：按词表对 chapters/ 做精确匹配，输出命中位置与上下文
用法：python3 sensitive-scan.py [--dir chapters] [--wordlist references/sensitive-words.txt]
词表格式：每行 "级别|词语|修改建议"（建议可省略），级别为 1/2/3，# 开头为注释
输出：.sumeru/finalize/sensitive-hits.json
注意：词表匹配只是第一遍筛查，情节与描写层面的敏感内容仍需按 SKILL.md 的「敏感词检测标准」做语义检查
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHAPTER_PATTERN = re.compile(r'^\d{3,4}-.+\.md$')
DEFAULT_WORDLIST = Path(__file__).resolve().parent.parent / "references" / "sensitive-words.txt"
CONTEXT_CHARS = 12


def load_wordlist(path):
    wordlist = Path(path)
    if not wordlist.is_file():
        raise FileNotFoundError("词表不存在: {}".format(path))
    entries = []
    for line_number, raw in enumerate(wordlist.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2 or parts[0] not in ("1", "2", "3") or not parts[1]:
            raise ValueError('词表第 {} 行格式错误: {}，应为 "级别|词语|修改建议"'.format(line_number, raw))
        entries.append({"level": int(parts[0]), "word": parts[1],
                        "suggestion": parts[2] if len(parts) > 2 else ""})
    return entries


def scan(chapters_dir, entries):
    directory = Path(chapters_dir)
    if not directory.is_dir():
        raise FileNotFoundError("章节目录不存在: {}".format(chapters_dir))
    hits = []
    files = sorted(f for f in directory.iterdir() if f.is_file() and CHAPTER_PATTERN.match(f.name))
    for file in files:
        for line_number, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
            for entry in entries:
                start = line.find(entry["word"])
                while start != -1:
                    end = start + len(entry["word"])
                    hits.append({
                        "file": file.name,
                        "line": line_number,
                        "level": entry["level"],
                        "word": entry["word"],
                        "suggestion": entry["suggestion"],
                        "context": line[max(0, start - CONTEXT_CHARS):end + CONTEXT_CHARS],
                    })
                    start = line.find(entry["word"], end)
    hits.sort(key=lambda item: (item["level"], item["file"], item["line"]))
    return len(files), hits


def main():
    parser = argparse.ArgumentParser(description="敏感词词表扫描")
    parser.add_argument("--dir", "-d", default="chapters", help="章节目录 (默认: chapters)")
    parser.add_argument("--wordlist", "-w", default=str(DEFAULT_WORDLIST), help="词表文件路径")
    parser.add_argument("--out", "-o", default=".sumeru/finalize/sensitive-hits.json", help="结果输出路径")
    args = parser.parse_args()

    try:
        entries = load_wordlist(args.wordlist)
        file_count, hits = scan(args.dir, entries)
        summary = {
            "wordlist_entries": len(entries),
            "files_scanned": file_count,
            "total_hits": len(hits),
            "by_level": {str(level): sum(1 for h in hits if h["level"] == level) for level in (1, 2, 3)},
            "hits": hits,
        }
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError) as error:
        print("执行出错: {}".format(error), file=sys.stderr)
        sys.exit(2)

    if not entries:
        print("词表为空，未做任何匹配。请先在词表中按目标平台要求添加词条: {}".format(args.wordlist))
    print("扫描 {} 个章节，命中 {} 处（一级 {} / 二级 {} / 三级 {}），结果: {}".format(
        file_count, len(hits), summary["by_level"]["1"], summary["by_level"]["2"],
        summary["by_level"]["3"], args.out))


if __name__ == "__main__":
    main()
