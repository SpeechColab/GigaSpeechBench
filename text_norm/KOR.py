import re
import unicodedata


def normalize(text: str) -> str:
    # Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Remove annotation inside [], (), {}
    text = re.sub(r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}", "", text)

    korean_english_only_pattern = re.compile(
        r"[^"
        r"\uAC00-\uD7A3"  # Hangul Syllables (现代音节)
        r"\u1100-\u11FF"  # Hangul Jamo (组合字母)
        r"\u3130-\u318F"  # Hangul Compatibility Jamo (兼容字母, 如 ㅋㅋ)
        r"\uA960-\uA97F"  # Hangul Jamo Extended-A
        r"\uD7B0-\uD7FF"  # Hangul Jamo Extended-B
        r"a-zA-Z"  # English Alphabets
        r"]"
    )

    text = korean_english_only_pattern.sub("", text)

    text = text.upper()

    return text


if __name__ == "__main__":
    import sys

    ori_text = sys.argv[1]
    print(normalize(ori_text))
