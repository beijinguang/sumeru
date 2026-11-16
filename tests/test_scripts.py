#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具脚本测试。运行：python3 -m unittest discover -s tests"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATE = "skills/sumeru-write/scripts/validate-chapters.py"
COUNTER = "skills/sumeru-review/scripts/chapter-word-counter.py"
EXPORT = "skills/sumeru-finalize/scripts/export-platforms.py"
REPLACE = "skills/sumeru-finalize/scripts/batch-replace.py"
SCAN = "skills/sumeru-finalize/scripts/sensitive-scan.py"

CHAPTER_ONE = "# 第1章 废物觉醒\n\n张三站在演武场上。\n\n“你就是**张三**？”李四冷笑。\n\n---\n\n夜色渐深。\n"
CHAPTER_TWO = "张三打开系统面板。\n"


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        self.chapters = self.work / "chapters"
        self.chapters.mkdir()
        (self.chapters / "001-废物觉醒.md").write_text(CHAPTER_ONE, encoding="utf-8")
        (self.chapters / "002-系统签到.md").write_text(CHAPTER_TWO, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, script, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / script)] + list(args), cwd=str(self.work),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


class ValidateChaptersTest(ScriptTestCase):
    def test_valid_chapters_pass(self):
        result = self.run_script(VALIDATE, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_invalid_name_and_missing_chapter(self):
        (self.chapters / "第3章-错误命名.md").write_text("内容", encoding="utf-8")
        outline = self.work / "outline.json"
        outline.write_text(json.dumps({"chapters": [{"chapterNumber": n} for n in (1, 2, 3)]}), encoding="utf-8")
        result = self.run_script(VALIDATE, "--json", "--outline", str(outline))
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["invalid_names"], ["第3章-错误命名.md"])
        self.assertEqual(data["missing_chapters"], [3])

    def test_progress_file_is_ignored(self):
        (self.chapters / "WRITE_PROGRESS.md").write_text("进度", encoding="utf-8")
        self.assertEqual(self.run_script(VALIDATE).returncode, 0)

    def test_missing_directory_reports_error(self):
        result = self.run_script(VALIDATE, "--dir", "not-exists")
        self.assertEqual(result.returncode, 2)
        self.assertIn("章节目录不存在", result.stderr)


class WordCounterTest(ScriptTestCase):
    def test_chapter_number_comes_from_file_name(self):
        (self.chapters / "010-跳号章节.md").write_text("正文内容", encoding="utf-8")
        result = self.run_script(COUNTER, "--dir", "chapters", "--output", "out")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.work / "out" / "word-count.json").read_text(encoding="utf-8"))
        self.assertEqual([c["chapter_num"] for c in data["chapters"]], [1, 2, 10])
        self.assertEqual(data["chapters"][2]["total_words"], 4)


class ExportPlatformsTest(ScriptTestCase):
    def test_qidian_format(self):
        result = self.run_script(EXPORT, "--platform", "起点")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.work / "publish" / "qidian" / "001-废物觉醒.txt").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("第1章 废物觉醒\n\n"))
        self.assertIn("\u3000\u3000张三站在演武场上。\n\n", text)
        self.assertNotIn("**", text)
        self.assertNotIn("#", text)
        self.assertIn("\n* * *\n", text)
        self.assertTrue((self.work / "publish" / "qidian" / "全文.txt").is_file())

    def test_fanqie_keeps_bold_without_indent(self):
        self.run_script(EXPORT, "--platform", "fanqie")
        text = (self.work / "publish" / "fanqie" / "001-废物觉醒.txt").read_text(encoding="utf-8")
        self.assertIn("**张三**", text)
        self.assertIn("\n张三站在演武场上。", text)

    def test_all_platforms_and_word_warnings(self):
        result = self.run_script(EXPORT)
        self.assertEqual(result.returncode, 0, result.stderr)
        exported = sorted(p.name for p in (self.work / "publish").iterdir())
        self.assertEqual(exported, ["17k", "fanqie", "jjwxc", "qidian", "zongheng"])
        report = json.loads((self.work / "publish" / "qidian" / "export-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["chapters"], 2)
        self.assertEqual(len(report["word_count_warnings"]), 2)

    def test_unknown_platform_reports_error(self):
        result = self.run_script(EXPORT, "--platform", "不存在的平台")
        self.assertEqual(result.returncode, 2)
        self.assertIn("不支持的平台", result.stderr)


class BatchReplaceTest(ScriptTestCase):
    def test_preview_does_not_modify(self):
        result = self.run_script(REPLACE, "--rule", "张三=>李玄")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["applied"])
        self.assertEqual(data["total"], 3)
        self.assertEqual((self.chapters / "001-废物觉醒.md").read_text(encoding="utf-8"), CHAPTER_ONE)

    def test_apply_replaces_and_backs_up(self):
        result = self.run_script(REPLACE, "--rule", "张三=>李玄", "--rule", "李四=>王虎", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.chapters / "001-废物觉醒.md").read_text(encoding="utf-8")
        self.assertNotIn("张三", text)
        self.assertIn("王虎冷笑", text)
        original = self.work / ".sumeru" / "write" / "original" / "001-废物觉醒.md"
        self.assertEqual(original.read_text(encoding="utf-8"), CHAPTER_ONE)
        self.run_script(REPLACE, "--rule", "李玄=>赵无极", "--apply")
        self.assertEqual(original.read_text(encoding="utf-8"), CHAPTER_ONE)
        history = json.loads(
            (self.work / ".sumeru" / "finalize" / "replace-history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(history), 2)

    def test_regex_rule(self):
        self.run_script(REPLACE, "--regex", "--rule", r"第(\d+)章=>卷一·第\1章", "--apply")
        text = (self.chapters / "001-废物觉醒.md").read_text(encoding="utf-8")
        self.assertIn("卷一·第1章", text)

    def test_missing_rule_reports_error(self):
        result = self.run_script(REPLACE)
        self.assertEqual(result.returncode, 2)
        self.assertIn("未提供替换规则", result.stderr)


class SensitiveScanTest(ScriptTestCase):
    def test_hits_are_reported_with_location(self):
        wordlist = self.work / "words.txt"
        wordlist.write_text("# 注释\n2|演武场|改为练武场\n1|不存在的词\n", encoding="utf-8")
        result = self.run_script(SCAN, "--wordlist", str(wordlist))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(
            (self.work / ".sumeru" / "finalize" / "sensitive-hits.json").read_text(encoding="utf-8"))
        self.assertEqual(data["total_hits"], 1)
        self.assertEqual(data["hits"][0]["file"], "001-废物觉醒.md")
        self.assertEqual(data["hits"][0]["line"], 3)
        self.assertEqual(data["hits"][0]["suggestion"], "改为练武场")

    def test_default_wordlist_is_empty_template(self):
        result = self.run_script(SCAN)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("词表为空", result.stdout)

    def test_bad_wordlist_line_reports_error(self):
        wordlist = self.work / "words.txt"
        wordlist.write_text("没有级别的词\n", encoding="utf-8")
        result = self.run_script(SCAN, "--wordlist", str(wordlist))
        self.assertEqual(result.returncode, 2)
        self.assertIn("格式错误", result.stderr)


if __name__ == "__main__":
    unittest.main()
