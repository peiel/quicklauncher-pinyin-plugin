import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


PLUGIN_DIR = Path(__file__).resolve().parents[1]
ENTRY = PLUGIN_DIR / "main.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN_DIR))
import main


class PinyinResponseTests(unittest.TestCase):
    def assert_response(self, arguments, expected):
        self.assertEqual(
            {"version": 1, "action": "copyAndShow", "text": expected},
            main.response({"version": 1, "arguments": arguments}),
        )

    def assert_error(self, request, message=None):
        result = main.response(request)
        self.assertEqual(1, result["version"])
        self.assertEqual("error", result["action"])
        self.assertLessEqual(len(result["text"]), 200)
        if message:
            self.assertIn(message, result["text"])

    def test_manifest(self):
        manifest = json.loads((PLUGIN_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("py", manifest["keyword"])
        self.assertEqual("python", manifest["runtime"])
        self.assertEqual("main.py", manifest["entry"])
        self.assertEqual("arguments", manifest["input"])
        self.assertIs(manifest["acceptsSelectedText"], True)
        self.assertFalse(manifest.get("previewOnKeyword", False))

    def test_simple_chinese_and_tones(self):
        self.assert_response("你好", "nǐ hǎo")
        self.assert_response("中国", "zhōng guó")
        self.assert_response("女儿", "nǚ ér")

    def test_phrase_pronunciations_and_traditional_chinese(self):
        self.assert_response("重庆银行音乐", "chóng qìng yín háng yīn yuè")
        self.assert_response("繁體漢語", "fán tǐ hàn yǔ")

    def test_non_chinese_and_spacing(self):
        self.assert_response("中文ABC汉字！Hello 世界", "zhōng wén ABC hàn zì！Hello shì jiè")
        self.assert_response("你好，world!", "nǐ hǎo，world!")
        self.assert_response("A中B国C", "A zhōng B guó C")
        self.assert_response("中文  英文", "zhōng wén  yīng wén")
        self.assert_response("👋你好😊", "👋nǐ hǎo😊")
        self.assert_response("cafe\u0301 中文", "cafe\u0301 zhōng wén")
        self.assert_response("𠮷野家", "𠮷 yě jiā")
        self.assert_response("ABC 123!", "ABC 123!")

    def test_missing_and_invalid_input(self):
        for request in ({"version": 1}, {"version": 1, "arguments": ""}, {"version": 1, "arguments": "   "}):
            with self.subTest(request=request):
                self.assert_error(request, "选中文字")
        for value in (None, 3, True, [], {}):
            with self.subTest(value=value):
                self.assert_error({"version": 1, "arguments": value}, "文本")

    def test_invalid_protocol(self):
        for request in (None, [], {}, {"version": 2}, {"version": "1"}, {"version": True}, {"version": 1.0}):
            with self.subTest(request=request):
                self.assert_error(request, "协议版本")

    def test_input_byte_limit_precedes_output_limit(self):
        self.assert_error({"version": 1, "arguments": "中" * 341 + "a"}, "200")
        self.assert_error({"version": 1, "arguments": "中" * 341 + "ab"}, "1024")
        self.assert_error({"version": 1, "arguments": "a" * 1024}, "200")
        self.assert_error({"version": 1, "arguments": "a" * 1025}, "1024")

    def test_output_character_boundary(self):
        self.assert_response("a" * 200, "a" * 200)
        self.assert_error({"version": 1, "arguments": "a" * 201}, "200")
        self.assert_response("你" * 50, " ".join(["nǐ"] * 50))
        self.assert_error({"version": 1, "arguments": "你" * 68}, "200")

    def test_rejects_controls_unicode_line_separators_and_surrogates(self):
        for value in ("你好\n世界", "hello\rworld", "a\tb", "a\x00b", "a\x7fb", "a\x0085b", "a\u2028b", "a\u2029b", "a\ud800b"):
            with self.subTest(value=repr(value)):
                self.assert_error({"version": 1, "arguments": value}, "无法注音")

    def test_rejects_format_characters_and_variation_selectors(self):
        for value in ("👩‍💻你好", "你好​世界", "银\U000e0100行", "字︀号", "a­b"):
            with self.subTest(value=repr(value)):
                self.assert_error({"version": 1, "arguments": value}, "无法注音")

    def test_combining_character_boundaries_get_spaces(self):
        self.assert_response("cafe\u0301中文", "cafe\u0301 zhōng wén")
        self.assert_response("中文e\u0301nd", "zhōng wén e\u0301nd")

    def test_length_uses_display_clusters_not_code_points(self):
        result = main.response({"version": 1, "arguments": "e\u0301" * 99 + "你好"})
        self.assertEqual("copyAndShow", result["action"])
        self.assertTrue(result["text"].endswith("nǐ hǎo"))
        self.assert_error({"version": 1, "arguments": "a" * 201}, "200")


class StandardIOTests(unittest.TestCase):
    def invoke(self, data, env=None):
        process = subprocess.run(
            [sys.executable, "-S", str(ENTRY)],
            input=data,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=PLUGIN_DIR,
            env=env,
            timeout=4,
            check=True,
        )
        self.assertEqual("", process.stderr)
        self.assertLessEqual(len(process.stdout.encode("utf-8")), 65536)
        lines = process.stdout.splitlines()
        self.assertEqual(1, len(lines))
        return json.loads(lines[0])

    def test_direct_arguments_and_simulated_selected_text(self):
        for value in ("你好", "重庆"):
            with self.subTest(value=value):
                result = self.invoke(json.dumps({"version": 1, "arguments": value}, ensure_ascii=False))
                self.assertEqual("copyAndShow", result["action"])
                self.assertTrue(result["text"])

    def test_bad_json_and_protocol_return_safe_error_json(self):
        for data in ("{", "", "null", '{"version":2}', '{"version":1,"arguments":"a\\ud800"}'):
            with self.subTest(data=data):
                result = self.invoke(data)
                self.assertEqual(1, result["version"])
                self.assertEqual("error", result["action"])
                self.assertTrue(result["text"])

    def test_vendor_works_without_user_site_and_phrase_setting(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = ""
        env["PYPINYIN_NO_PHRASES"] = "1"
        result = self.invoke('{"version":1,"arguments":"重庆"}', env=env)
        self.assertEqual("chóng qìng", result["text"])

    def test_host_style_launch_without_isolated_mode(self):
        process = subprocess.run(
            [sys.executable, str(ENTRY)],
            input='{"version":1,"arguments":"你好"}',
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=PLUGIN_DIR,
            timeout=4,
            check=True,
        )
        self.assertEqual("", process.stderr)
        self.assertEqual(
            {"version": 1, "action": "copyAndShow", "text": "nǐ hǎo"},
            json.loads(process.stdout),
        )


if __name__ == "__main__":
    unittest.main()
