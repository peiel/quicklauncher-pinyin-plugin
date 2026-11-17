import json
import os
import sys
import unicodedata
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
os.environ.pop("PYPINYIN_NO_PHRASES", None)

from pypinyin import Style, pinyin


MAX_INPUT_BYTES = 1024
MAX_RESULT_CHARS = 200
# QuickLauncher rejects control and format characters in results; variation
# selectors also break pypinyin's phrase segmentation, so reject both up front.
UNSUPPORTED_CATEGORIES = {"Cc", "Cs", "Cf"}
LINE_SEPARATORS = "\u2028\u2029"
COMBINING_CATEGORIES = {"Mn", "Me", "Mc"}


def is_variation_selector(char):
    return 0xFE00 <= ord(char) <= 0xFE0F or 0xE0100 <= ord(char) <= 0xE01EF


def has_unsupported_characters(text):
    return any(
        unicodedata.category(char) in UNSUPPORTED_CATEGORIES
        or char in LINE_SEPARATORS
        or is_variation_selector(char)
        for char in text
    )


def display_length(text):
    # Approximate Swift's grapheme-cluster count: combining marks join the
    # preceding base character. This never undercounts the host's limit.
    return sum(
        1 for char in text if unicodedata.category(char) not in COMBINING_CATEGORIES
    )


def ends_with_word_character(text):
    index = len(text) - 1
    while index >= 0 and unicodedata.category(text[index]) in COMBINING_CATEGORIES:
        index -= 1
    return index >= 0 and text[index].isalnum()


def starts_with_word_character(text):
    index = 0
    while index < len(text) and unicodedata.category(text[index]) in COMBINING_CATEGORIES:
        index += 1
    return index < len(text) and text[index].isalnum()


def convert_to_pinyin(text):
    # Preserve non-Chinese characters individually so punctuation and spaces remain intact.
    syllables = pinyin(text, style=Style.TONE, errors=lambda chars: list(chars))
    if len(syllables) != len(text):
        raise ValueError("拼音转换结果与输入不匹配")

    pieces = []
    output = ""
    previous_was_pinyin = False
    for original, alternatives in zip(text, syllables):
        converted = alternatives[0]
        is_pinyin = converted != original
        if is_pinyin and pieces:
            if previous_was_pinyin or ends_with_word_character(output):
                pieces.append(" ")
                output += " "
        elif previous_was_pinyin and starts_with_word_character(converted):
            pieces.append(" ")
            output += " "
        pieces.append(converted)
        output += converted
        previous_was_pinyin = is_pinyin

    return "".join(pieces)


def response(request):
    if not isinstance(request, dict) or type(request.get("version")) is not int or request["version"] != 1:
        return error("不支持的请求格式或协议版本")

    text = request.get("arguments", "")
    if not isinstance(text, str):
        return error("输入内容必须是文本")
    if has_unsupported_characters(text):
        return error("输入包含控制、格式字符或变体选择符，无法注音，请清理后重试")
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        return error("输入过长，请使用不超过 1024 字节的文本")
    if not text.strip():
        return error("请输入 py 中文，或先选中文字再执行 py")

    result = convert_to_pinyin(text)
    if not result.strip():
        return error("没有可显示的转换结果")
    if display_length(result) > MAX_RESULT_CHARS:
        return error("拼音结果超过 200 字符，请缩短输入后重试")
    if has_unsupported_characters(result):
        return error("拼音结果包含不受支持的字符")
    return {"version": 1, "action": "copyAndShow", "text": result}


def error(text):
    return {"version": 1, "action": "error", "text": text}


def main():
    try:
        request = json.load(sys.stdin)
        result = response(request)
    except (ValueError, TypeError, UnicodeError):
        result = error("请求无效，请输入单行文本后重试")
    except Exception:
        result = error("拼音转换失败，请缩短或更换输入后重试")

    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
