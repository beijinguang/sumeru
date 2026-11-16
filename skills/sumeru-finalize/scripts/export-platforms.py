#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多平台格式导出工具
功能：按 references/platforms.json 中的平台规则，把 chapters/ 下的章节导出为各平台发布格式
用法：python3 export-platforms.py [--dir chapters] [--out publish] [--platform all|起点|fanqie,jjwxc]
输出：<out>/<平台>/<章节号>-<标题>.txt、<out>/<平台>/全文.txt、<out>/<平台>/export-report.json
说明：平台规则全部来自配置文件，新增或调整平台只需修改 platforms.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHAPTER_PATTERN = re.compile(r'^(\d{3,4})-(.+)\.md$')
SCENE_BREAK_PATTERN = re.compile(r'^(-{3,}|\*{3,}|_{3,})$')
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "references" / "platforms.json"


def load_platforms(config_path):
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError("平台配置不存在: {}".format(config_path))
    return json.loads(path.read_text(encoding="utf-8"))["platforms"]


def resolve_platforms(platforms, requested):
    """把用户输入的平台名（键名/中文名/别名，可逗号分隔）解析为配置键列表"""
    if requested in ("all", "全平台"):
        return list(platforms.keys())
    keys = []
    for name in re.split(r'[,，、\s]+', requested):
        if not name:
            continue
        found = None
        for key, conf in platforms.items():
            if name.lower() == key.lower() or name == conf.get("name") or name in conf.get("aliases", []):
                found = key
                break
        if found is None:
            raise ValueError("不支持的平台: {}。可用平台: {}；新增平台请编辑 platforms.json".format(
                name, "、".join(platforms.keys())))
        if found not in keys:
            keys.append(found)
    if not keys:
        raise ValueError("未指定导出平台")
    return keys


def count_words(text):
    """与 chapter-word-counter.py 一致：汉字算1字，英文单词算1字，标点不计"""
    return len(re.findall(r'[\u4e00-\u9fa5]', text)) + len(re.findall(r'[a-zA-Z]+', text))


def to_paragraphs(text, keep_bold):
    """把 Markdown 章节拆成段落列表；None 表示场景分隔"""
    paragraphs = []
    first = True
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if first and stripped.startswith("#"):
            first = False
            continue
        first = False
        if SCENE_BREAK_PATTERN.match(stripped):
            paragraphs.append(None)
            continue
        stripped = re.sub(r'^#{1,6}\s*', '', stripped)
        if not keep_bold:
            stripped = stripped.replace("**", "")
        paragraphs.append(stripped)
    return paragraphs


def render(number, title, paragraphs, conf):
    heading = conf.get("title_template", "第{n}章 {title}").format(n=number, title=title)
    indent = conf.get("indent", "")
    separator = "\n\n" if conf.get("blank_line_between_paragraphs", True) else "\n"
    scene_break = conf.get("scene_break", "* * *")
    body = [scene_break if p is None else indent + p for p in paragraphs]
    return heading + "\n\n" + separator.join(body) + "\n"


def collect_chapters(chapters_dir):
    directory = Path(chapters_dir)
    if not directory.is_dir():
        raise FileNotFoundError("章节目录不存在: {}".format(chapters_dir))
    chapters = []
    for file in directory.iterdir():
        match = CHAPTER_PATTERN.match(file.name) if file.is_file() else None
        if match:
            chapters.append((int(match.group(1)), match.group(1), match.group(2), file))
    if not chapters:
        raise FileNotFoundError("目录 {} 中没有符合命名规范（001-标题.md）的章节文件".format(chapters_dir))
    chapters.sort(key=lambda item: item[0])
    return chapters


def export_platform(key, conf, chapters, out_dir):
    target = Path(out_dir) / key
    target.mkdir(parents=True, exist_ok=True)
    low, high = conf.get("recommended_words", [0, 0])
    full_text = []
    warnings = []
    total_words = 0
    for number, padded, title, file in chapters:
        paragraphs = to_paragraphs(file.read_text(encoding="utf-8"), conf.get("keep_bold", False))
        rendered = render(number, title, paragraphs, conf)
        (target / "{}-{}.txt".format(padded, title)).write_text(rendered, encoding="utf-8")
        full_text.append(rendered)
        words = count_words("".join(p for p in paragraphs if p))
        total_words += words
        if high and (words < low or words > high):
            warnings.append({"chapter": number, "words": words, "recommended": [low, high]})
    (target / "全文.txt").write_text("\n\n".join(full_text), encoding="utf-8")
    report = {
        "platform": key,
        "name": conf.get("name", key),
        "chapters": len(chapters),
        "total_words": total_words,
        "word_count_warnings": warnings,
    }
    (target / "export-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="多平台发布格式导出")
    parser.add_argument("--dir", "-d", default="chapters", help="章节目录 (默认: chapters)")
    parser.add_argument("--out", "-o", default="publish", help="导出目录 (默认: publish)")
    parser.add_argument("--platform", "-p", default="all", help="平台键名/中文名，可逗号分隔，或 all (默认)")
    parser.add_argument("--config", "-c", default=str(DEFAULT_CONFIG), help="平台配置文件路径")
    args = parser.parse_args()

    try:
        platforms = load_platforms(args.config)
        keys = resolve_platforms(platforms, args.platform)
        chapters = collect_chapters(args.dir)
        reports = [export_platform(key, platforms[key], chapters, args.out) for key in keys]
    except (OSError, ValueError, KeyError) as error:
        print("执行出错: {}".format(error), file=sys.stderr)
        sys.exit(2)

    for report in reports:
        print("已导出 {}（{}）: {} 章，{} 字，{} 章字数超出该平台建议范围".format(
            report["name"], report["platform"], report["chapters"],
            report["total_words"], len(report["word_count_warnings"])))
    print("导出目录: {}".format(args.out))


if __name__ == "__main__":
    main()
