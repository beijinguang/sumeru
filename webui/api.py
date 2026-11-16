#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""webui API 处理函数（纯函数层，不含 HTTP 细节，便于单测）。

约定：
  - 每个处理函数签名 handle_xxx(root: Path, **args) -> (status:int, payload:dict|bytes)
  - root 是小说项目根目录（server 启动 cwd），所有路径白名单限制在其内
  - 工具执行复用 skills/*/scripts/*.py，退出码与报告透传，不重写校验逻辑
"""

import json
import re
import subprocess
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]  # webui/api.py → webui → 仓库根
SKILLS_DIR = REPO_ROOT / "skills"

CHAPTER_NAME = re.compile(r"^(\d{3,4})-(.+)\.md$")
SUPPORTED_PLATFORMS = ["qidian", "fanqie", "jjwxc", "zongheng", "17k"]
SUPPORTED_FORMATS = ["md", "txt", "html", "epub"]
STAGES = ["deconstruct", "outline", "write", "review", "polish", "finalize"]

# 工具注册表：name → (脚本相对路径, 默认超时秒, 参数构造器)
TOOLS = {
    "plan": ("sumeru-outline/scripts/plan-chapters.py", 60),
    "check": ("sumeru-write/scripts/check-chapters.py", 60),
    "counter": ("sumeru-review/scripts/chapter-word-counter.py", 60),
    "timeline": ("sumeru-review/scripts/validate-timeline.py", 60),
    "analyze": ("sumeru-deconstruct/scripts/analyze-book.py", 300),
    "derivative": ("sumeru-deconstruct/scripts/check-derivative.py", 300),
    "build": ("sumeru-finalize/scripts/build.py", 300),
    "sensitive": ("sumeru-finalize/scripts/sensitive-scan.py", 60),
}

_tool_lock = threading.Lock()
_last_tool_result = {}


# ---------------------------------------------------------------- 工具函数

def _read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _safe_join(root, *parts):
    """拼路径并限制在 root 内，越界返回 None（调用方转 403）"""
    try:
        target = (Path(root).resolve() / Path(*parts)).resolve()
        target.relative_to(Path(root).resolve())
        return target
    except (ValueError, OSError):
        return None


def _stage_gate(stage, root):
    """读取某阶段的门禁状态 → {"stage", "passed", "errors", "warnings"}"""
    gate_files = {
        "deconstruct": ".sumeru/deconstruct/derivative-check.json",
        "outline": ".sumeru/outline/compliance-check.json",
        "write": ".sumeru/write/chapter-check.json",
        "review": ".sumeru/review/timeline-check.json",
        "polish": None,   # polish 无独立机器门禁（以 chapters 无占位符为准）
        "finalize": ".sumeru/finalize/stats.json",
    }
    rel = gate_files.get(stage)
    if not rel:
        return {"stage": stage, "passed": None, "detail": "无机器门禁，以人工/流程为准"}
    data = _read_json(Path(root) / rel)
    if data is None:
        return {"stage": stage, "passed": None, "detail": f"尚未运行（无 {rel}）"}
    passed = data.get("passed")
    if passed is None:
        errors = data.get("errors", [])
        passed = not errors
    return {"stage": stage, "passed": bool(passed), "detail": rel}


# ---------------------------------------------------------------- API: status

def handle_status(root):
    """仪表盘聚合数据：进度 / 字数摘要 / 六阶段门禁"""
    root = Path(root)
    chapters_dir = root / "chapters"
    chapters = []
    for f in sorted(chapters_dir.glob("*.md")) if chapters_dir.exists() else []:
        m = CHAPTER_NAME.match(f.name)
        if m:
            chapters.append({"number": int(m.group(1)), "title": m.group(2).strip()})

    plan = _read_json(root / ".sumeru/outline/chapter-plan.json")
    progress = _read_json(root / ".sumeru/session/WORLDBUILDER_PROGRESS.json")

    stats = None
    word_count = _read_json(root / ".sumeru/review/word-count.json")
    if word_count and "summary" in word_count:
        stats = word_count["summary"]

    return 200, {
        "totalChaptersPlanned": (plan or {}).get("meta", {}).get("totalChapters"),
        "volumes": (plan or {}).get("meta", {}).get("volumes", []),
        "chapterCount": len(chapters),
        "wordStats": stats,
        "progress": progress.get("stage") if isinstance(progress, dict) else None,
        "gates": [_stage_gate(s, root) for s in STAGES],
    }


# ---------------------------------------------------------------- API: chapters

def list_chapters(root):
    """章节列表 + 命名错误标记（轻量，不跑脚本；完整校验走 tools/check）"""
    root = Path(root)
    chapters, invalid = [], []
    chapters_dir = root / "chapters"
    if not chapters_dir.exists():
        return 200, {"chapters": [], "invalid": []}
    for f in sorted(chapters_dir.glob("*.md")):
        m = CHAPTER_NAME.match(f.name)
        if m:
            chapters.append({
                "number": int(m.group(1)),
                "file": f.name,
                "title": m.group(2).strip(),
            })
        elif not f.name.startswith("."):
            invalid.append(f.name)
    chapters.sort(key=lambda x: x["number"])
    return 200, {"chapters": chapters, "invalid": invalid}


def get_chapter(root, num, outline_number=None):
    """单章内容 + 细纲对照 + 备份状态"""
    root = Path(root)
    chapters_dir = root / "chapters"
    match = None
    if chapters_dir.exists():
        for f in chapters_dir.glob("*.md"):
            m = CHAPTER_NAME.match(f.name)
            if m and int(m.group(1)) == int(num):
                match = f
                break
    if match is None:
        return 404, {"error": f"章节 {num} 不存在"}

    text = match.read_text(encoding="utf-8", errors="ignore")
    has_original = (root / ".sumeru/write/original" / match.name).exists()
    payload = {
        "number": int(num),
        "file": match.name,
        "content": text,
        "hasOriginal": has_original,
    }
    if outline_number is not None:
        outline = _read_json(root / ".sumeru/outline/chapter-outlines.json")
        if outline:
            for ch in outline.get("chapters", []):
                if ch.get("chapterNumber") == int(num):
                    payload["outline"] = ch
                    break
    return 200, payload


def save_chapter(root, num, content):
    """保存章节：先按规则备份，再写回（内容里的文件名不变，标题行不动）"""
    root = Path(root)
    chapters_dir = root / "chapters"
    match = None
    if chapters_dir.exists():
        for f in chapters_dir.glob("*.md"):
            m = CHAPTER_NAME.match(f.name)
            if m and int(m.group(1)) == int(num):
                match = f
                break
    if match is None:
        return 404, {"error": f"章节 {num} 不存在"}
    if not isinstance(content, str):
        return 400, {"error": "content 必须是字符串"}

    sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
    from backup import backup_before_write
    backups = backup_before_write(chapters_dir, match.name,
                                  dot_sumeru=root / ".sumeru")
    match.write_text(content, encoding="utf-8")
    return 200, {"saved": match.name, "backups": backups}


def get_outline_chapter(root, num):
    outline = _read_json(Path(root) / ".sumeru/outline/chapter-outlines.json")
    if not outline:
        return 404, {"error": "尚无 chapter-outlines.json"}
    for ch in outline.get("chapters", []):
        if ch.get("chapterNumber") == int(num):
            return 200, ch
    return 404, {"error": f"细纲中不存在章节 {num}"}


# ---------------------------------------------------------------- API: tools

def run_tool(root, tool, args=None):
    """执行注册表中的脚本，串行 + 超时保护，结果缓存供 GET 轮询"""
    if tool not in TOOLS:
        return 404, {"error": f"未知工具 {tool}，可选：{sorted(TOOLS)}"}
    rel, timeout = TOOLS[tool]
    script = SKILLS_DIR / rel
    if not script.exists():
        return 500, {"error": f"脚本缺失：{script}"}

    argv = [sys.executable, str(script)] + [str(a) for a in (args or [])]
    if not _tool_lock.acquire(blocking=False):
        return 409, {"error": "已有工具在运行中，请稍候"}
    try:
        try:
            proc = subprocess.run(
                argv, cwd=str(root), capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace",
            )
            result = {"exitCode": proc.returncode, "stdout": proc.stdout,
                      "stderr": proc.stderr, "tool": tool}
        except subprocess.TimeoutExpired:
            result = {"exitCode": -1, "stdout": "", "stderr": "",
                      "tool": tool, "error": f"超时（>{timeout}s）被终止"}
    finally:
        _tool_lock.release()

    _last_tool_result[tool] = result
    return 200, result


def last_tool(tool):
    if tool not in TOOLS:
        return 404, {"error": f"未知工具 {tool}"}
    result = _last_tool_result.get(tool)
    if result is None:
        return 404, {"error": f"工具 {tool} 尚未运行"}
    return 200, result


# ---------------------------------------------------------------- API: reports/export

REPORT_WHITELIST = [
    ".sumeru/write/chapter-check.md", ".sumeru/write/chapter-check.json",
    ".sumeru/review/word-count.md", ".sumeru/review/word-count.json",
    ".sumeru/review/timeline-check.json",
    ".sumeru/deconstruct/derivative-check.md", ".sumeru/deconstruct/derivative-check.json",
    ".sumeru/finalize/report.md", ".sumeru/finalize/stats.json",
    ".sumeru/finalize/sensitive-hits.json",
    "完稿校验报告.md",
]


def get_report(root, name):
    """按白名单读取报告；name 支持带路径的相对形式，越界即拒"""
    if name not in REPORT_WHITELIST:
        return 403, {"error": "报告不在白名单内", "allowed": REPORT_WHITELIST}
    path = _safe_join(root, name)
    if path is None or not path.is_file():
        return 404, {"error": f"报告不存在：{name}"}
    return 200, {"name": name, "content": path.read_text(encoding="utf-8", errors="ignore")}


def get_export(root, platform, filename):
    """下载 publish/{platform}/{filename}，filename 禁止含路径分隔符。

    返回 (code, payload)；成功时 payload 为 bytes，失败为错误 dict。
    """
    if platform not in SUPPORTED_PLATFORMS:
        return 404, {"error": f"未知平台 {platform}"}
    if "/" in filename or ".." in filename or filename.startswith("."):
        return 403, {"error": "非法文件名"}
    path = _safe_join(root, "publish", platform, filename)
    if path is None or not path.is_file():
        return 404, {"error": "导出文件不存在，请先运行导出"}
    return 200, path.read_bytes()


# ---------------------------------------------------------------- API: next-step

def next_step(root):
    """按门禁状态推断下一步 /sumeru-* 指令（纯规则）"""
    root = Path(root)
    plan_exists = (root / ".sumeru/outline/chapter-outlines.json").exists()
    chapters = list_chapters(root)[1]["chapters"]
    write_gate = _stage_gate("write", root)

    if not plan_exists:
        return 200, {
            "stage": "outline",
            "reason": "尚无章节细纲",
            "command": '/sumeru-outline "<核心创意描述>"',
            "tip": "先生成大纲与完整章节细纲，再进入写作",
        }
    if not chapters:
        return 200, {
            "stage": "write",
            "reason": "细纲已就绪但还没有章节",
            "command": "/sumeru-write 全部章节",
            "tip": "从细纲批量生成章节（自动按卷分波次并行）",
        }
    if write_gate.get("passed") is False:
        return 200, {
            "stage": "write",
            "reason": "章节结构校验存在 error（缺章/命名/空章）",
            "command": "python3 skills/sumeru-write/scripts/check-chapters.py  # 查看详情，或 /sumeru-write 第X章 补写缺失章节",
            "tip": "先在工具面板跑一次 check 看 error 列表",
        }
    finalize_gate = _stage_gate("finalize", root)
    if finalize_gate.get("passed") is not True:
        return 200, {
            "stage": "review",
            "reason": "已有章节，尚未完成完稿校验",
            "command": "/sumeru-review 第1-" + str(max(c["number"] for c in chapters)) + "章",
            "tip": "先审查当前章节，再润色与完稿导出",
        }
    return 200, {
        "stage": "finalize",
        "reason": "全书门禁已通过",
        "command": "/sumeru-finalize 导出全平台格式",
        "tip": "可直接在导出中心点选平台导出",
    }
