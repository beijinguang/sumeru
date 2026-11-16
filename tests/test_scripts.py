#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""二开新增/修改脚本的测试（上游脚本的用例在 test_tools.py）。运行：python3 -m unittest discover -s tests"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNTER = "skills/sumeru-review/scripts/chapter-word-counter.py"
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


class WordCounterTest(ScriptTestCase):
    def test_chapter_number_comes_from_file_name(self):
        (self.chapters / "010-跳号章节.md").write_text("正文内容", encoding="utf-8")
        result = self.run_script(COUNTER, "--dir", "chapters", "--output", "out")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.work / "out" / "word-count.json").read_text(encoding="utf-8"))
        self.assertEqual([c["chapter_num"] for c in data["chapters"]], [1, 2, 10])
        self.assertEqual(data["chapters"][2]["total_words"], 4)


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
