#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""webui API 与备份模块测试（不真起端口，直接调用纯函数）"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(rel_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


api = load_module("webui/api.py", "webui_api")
sys.path.insert(0, str(ROOT / "webui/lib"))
import backup  # noqa: E402


def make_project(tmp, chapters=3):
    """构造一个最小的小说项目：chapters/ + .sumeru/ 细纲"""
    root = Path(tmp)
    chapters_dir = root / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (chapters_dir / f"{i:03d}-初见{i}.md").write_text(
            f"第{i}章 初见{i}\n\n陆照野站在临川城头。" * 20, encoding="utf-8")
    outline_dir = root / ".sumeru/outline"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "chapter-outlines.json").write_text(json.dumps({
        "chapters": [{"chapterNumber": i, "chapterTitle": f"初见{i}",
                      "suggestedWords": "3000-4000"} for i in range(1, chapters + 1)]
    }, ensure_ascii=False), encoding="utf-8")
    return root


import json  # noqa: E402


class ApiStatusTest(unittest.TestCase):
    def test_status_counts_chapters_and_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, payload = api.handle_status(root)
        self.assertEqual(code, 200)
        self.assertEqual(payload["chapterCount"], 3)
        self.assertEqual(payload["totalChaptersPlanned"], None)
        self.assertEqual(len(payload["gates"]), 6)
        # 未运行任何校验时门禁状态应为 None（未运行）
        for gate in payload["gates"]:
            self.assertIsNone(gate["passed"])

    def test_status_passed_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            stats = root / ".sumeru/write"
            stats.mkdir(parents=True)
            (stats / "chapter-check.json").write_text(
                json.dumps({"stats": {}, "errors": [], "warnings": []}),
                encoding="utf-8")
            _, payload = api.handle_status(root)
        gates = {g["stage"]: g for g in payload["gates"]}
        self.assertTrue(gates["write"]["passed"])
        self.assertIsNone(gates["finalize"]["passed"])


class ApiChaptersTest(unittest.TestCase):
    def test_list_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, listing = api.list_chapters(root)
            self.assertEqual(code, 200)
            self.assertEqual([c["number"] for c in listing["chapters"]], [1, 2, 3])

            code, chapter = api.get_chapter(root, 2, outline_number=1)
            self.assertEqual(code, 200)
            self.assertIn("第2章", chapter["content"])
            self.assertEqual(chapter["outline"]["chapterTitle"], "初见2")

    def test_get_missing_chapter_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, payload = api.get_chapter(root, 99)
        self.assertEqual(code, 404)

    def test_invalid_names_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, chapters=1)
            (root / "chapters" / "第2章-错误命名.md").write_text("x", encoding="utf-8")
            _, listing = api.list_chapters(root)
        self.assertEqual(listing["invalid"], ["第2章-错误命名.md"])

    def test_save_creates_backup_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, chapters=1)
            before = (root / "chapters/001-初见1.md").read_text(encoding="utf-8")

            code, saved = api.save_chapter(root, 1, before + "\n新内容")
            self.assertEqual(code, 200)
            original = Path(saved["backups"]["original"])
            history = Path(saved["backups"]["history"])
            # original 存的是修改前的最初原稿
            self.assertTrue(original.exists())
            self.assertEqual(original.read_text(encoding="utf-8"), before)
            self.assertTrue(history.exists())

            # 第二次保存：original 不被覆盖，history 再存一份
            code, saved2 = api.save_chapter(root, 1, before + "\n新内容v2")
            self.assertEqual(Path(saved2["backups"]["original"]).read_text(encoding="utf-8"),
                             before)
            self.assertNotEqual(str(saved2["backups"]["history"]),
                                str(saved["backups"]["history"]))

    def test_save_missing_chapter_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, _ = api.save_chapter(root, 99, "x")
        self.assertEqual(code, 404)

    def test_save_non_string_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, _ = api.save_chapter(root, 1, 12345)
        self.assertEqual(code, 400)


class PathSafetyTest(unittest.TestCase):
    def test_safe_join_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(api._safe_join(root, "..", "etc", "passwd"))
            self.assertIsNone(api._safe_join(root, "chapters", "../../x"))

    def test_report_whitelist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _ = api.get_report(root, "skills/sumeru-outline/references/ip-blocklist.md")
            self.assertEqual(code, 403)
            code, _ = api.get_report(root, ".sumeru/finalize/report.md")
            self.assertEqual(code, 404)  # 白名单内但文件未生成

    def test_export_rejects_path_tricks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _ = api.get_export(root, "qidian", "../book.epub")
            self.assertEqual(code, 403)
            code, _ = api.get_export(root, "notaplat", "full.md")
            self.assertEqual(code, 404)
            code, _ = api.get_export(root, "qidian", "sub/full.md")
            self.assertEqual(code, 403)


class ToolsTest(unittest.TestCase):
    def test_unknown_tool_404(self):
        code, _ = api.run_tool(Path("."), "nope", [])
        self.assertEqual(code, 404)

    def test_last_tool_before_run_404(self):
        code, _ = api.last_tool("check")
        self.assertEqual(code, 404)

    def test_run_counter_success(self):
        """端到端：用真脚本跑一次字数统计（chapters 目录由 tempfile 提供）"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp, chapters=1)
            code, result = api.run_tool(
                root, "counter",
                ["--dir", "chapters", "--output", str(root / ".sumeru/review")])
            self.assertEqual(code, 200)
            self.assertEqual(result["exitCode"], 0)
            self.assertIn("字数统计报告", result["stdout"])
            # 结果已缓存，可再次读取
            code, cached = api.last_tool("counter")
            self.assertEqual(code, 200)
            self.assertEqual(cached["exitCode"], 0)

    def test_run_tool_with_bad_args_returns_exit_code(self):
        """脚本退出码透传：参数错误 exit 2 不算 server 异常"""
        with tempfile.TemporaryDirectory() as tmp:
            root = make_project(tmp)
            code, result = api.run_tool(
                root, "check", ["--chapters", "nonexistent-dir"])
            self.assertEqual(code, 200)
            self.assertEqual(result["exitCode"], 2)


class BackupModuleTest(unittest.TestCase):
    def test_backup_skips_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = backup.backup_before_write(Path(tmp) / "chapters", "001-x.md",
                                                dot_sumeru=Path(tmp) / ".sumeru")
        self.assertEqual(result, {"original": None, "history": None})

    def test_original_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            chapters = Path(tmp) / "chapters"
            chapters.mkdir()
            src = chapters / "001-初见.md"
            src.write_text("v1", encoding="utf-8")
            first = backup.backup_before_write(chapters, "001-初见.md",
                                               dot_sumeru=Path(tmp) / ".sumeru")
            src.write_text("v2", encoding="utf-8")
            second = backup.backup_before_write(chapters, "001-初见.md",
                                                dot_sumeru=Path(tmp) / ".sumeru")
            original = Path(first["original"])
            self.assertEqual(original.read_text(encoding="utf-8"), "v1")
            # original 不覆盖：第二次备份的 original 是同一路径
            self.assertEqual(first["original"], second["original"])
            self.assertNotEqual(first["history"], second["history"])


if __name__ == "__main__":
    unittest.main()
