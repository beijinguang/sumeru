#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全书批量替换工具
功能：对 chapters/ 下所有章节执行多组替换规则，默认只预览，加 --apply 才写入
用法：
  python3 batch-replace.py --rule "张三=>李玄" --rule "李四=>王虎"            # 预览
  python3 batch-replace.py --rule "张三=>李玄" --apply                        # 执行
  python3 batch-replace.py --regex --rule "第(\d+)回=>第\1章" --apply         # 正则
  python3 batch-replace.py --rules-file rules.json --apply                    # 规则文件
规则文件格式：[{"find": "旧词", "replace": "新词", "regex": false}]
执行前自动备份：最初原稿存 .sumeru/write/original/（已存在则不覆盖），
本次修改前版本存 .sumeru/write/history/finalize-<时间戳>/；替换记录追加到 .sumeru/finalize/replace-history.json
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

CHAPTER_PATTERN = re.compile(r'^\d{3,4}-.+\.md$')
MAX_SAMPLES = 3
CONTEXT_CHARS = 10


def parse_rule(text, is_regex):
    if "=>" not in text:
        raise ValueError('规则格式错误: {}，应为 "旧词=>新词"'.format(text))
    find, replace = text.split("=>", 1)
    if not find:
        raise ValueError("规则 {} 的查找内容不能为空".format(text))
    return {"find": find, "replace": replace, "regex": is_regex}


def load_rules(args):
    rules = [parse_rule(text, args.regex) for text in args.rule]
    if args.rules_file:
        for item in json.loads(Path(args.rules_file).read_text(encoding="utf-8")):
            if not item.get("find"):
                raise ValueError("规则文件中存在缺少 find 的规则")
            rules.append({"find": item["find"], "replace": item.get("replace", ""),
                          "regex": bool(item.get("regex", False))})
    if not rules:
        raise ValueError('未提供替换规则，请使用 --rule "旧词=>新词" 或 --rules-file')
    for rule in rules:
        rule["pattern"] = re.compile(rule["find"] if rule["regex"] else re.escape(rule["find"]))
    return rules


def apply_rules(text, rules):
    """依次应用规则，返回 (新文本, 每条规则的命中信息)"""
    details = []
    for rule in rules:
        samples = []
        for match in list(rule["pattern"].finditer(text))[:MAX_SAMPLES]:
            start = max(0, match.start() - CONTEXT_CHARS)
            end = min(len(text), match.end() + CONTEXT_CHARS)
            samples.append(text[start:end].replace("\n", " "))
        if rule["regex"]:
            text, count = rule["pattern"].subn(rule["replace"], text)
        else:
            text, count = rule["pattern"].subn(lambda _match, value=rule["replace"]: value, text)
        details.append({"find": rule["find"], "replace": rule["replace"], "count": count, "samples": samples})
    return text, details


def backup(file, state_dir, stamp):
    original_dir = Path(state_dir) / "write" / "original"
    history_dir = Path(state_dir) / "write" / "history" / "finalize-{}".format(stamp)
    original_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    if not (original_dir / file.name).exists():
        shutil.copy2(str(file), str(original_dir / file.name))
    shutil.copy2(str(file), str(history_dir / file.name))


def main():
    parser = argparse.ArgumentParser(description="全书批量替换（默认预览，--apply 执行）")
    parser.add_argument("--dir", "-d", default="chapters", help="章节目录 (默认: chapters)")
    parser.add_argument("--rule", "-r", action="append", default=[], help='替换规则 "旧词=>新词"，可重复')
    parser.add_argument("--rules-file", help="JSON 规则文件")
    parser.add_argument("--regex", action="store_true", help="--rule 按正则表达式解析")
    parser.add_argument("--apply", action="store_true", help="实际写入文件（默认只预览）")
    parser.add_argument("--state-dir", default=".sumeru", help="中间数据目录 (默认: .sumeru)")
    args = parser.parse_args()

    try:
        rules = load_rules(args)
        directory = Path(args.dir)
        if not directory.is_dir():
            raise FileNotFoundError("章节目录不存在: {}".format(args.dir))
        files = sorted(f for f in directory.iterdir() if f.is_file() and CHAPTER_PATTERN.match(f.name))
        if not files:
            raise FileNotFoundError("目录 {} 中没有符合命名规范的章节文件".format(args.dir))

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        changed = []
        total = 0
        for file in files:
            text = file.read_text(encoding="utf-8")
            new_text, details = apply_rules(text, rules)
            hits = sum(item["count"] for item in details)
            if not hits:
                continue
            total += hits
            changed.append({"file": file.name, "count": hits,
                            "rules": [item for item in details if item["count"]]})
            if args.apply:
                backup(file, args.state_dir, stamp)
                file.write_text(new_text, encoding="utf-8")

        if args.apply and changed:
            log_path = Path(args.state_dir) / "finalize" / "replace-history.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            history = json.loads(log_path.read_text(encoding="utf-8")) if log_path.is_file() else []
            history.append({
                "time": stamp,
                "rules": [{"find": r["find"], "replace": r["replace"], "regex": r["regex"]} for r in rules],
                "total": total,
                "files": [{"file": item["file"], "count": item["count"]} for item in changed],
            })
            log_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, re.error) as error:
        print("执行出错: {}".format(error), file=sys.stderr)
        sys.exit(2)

    print(json.dumps({"applied": bool(args.apply), "total": total, "files": changed},
                     ensure_ascii=False, indent=2))
    if not args.apply:
        print("以上为预览，未修改任何文件；确认无误后加 --apply 执行", file=sys.stderr)


if __name__ == "__main__":
    main()
