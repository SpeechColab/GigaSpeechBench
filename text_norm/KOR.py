import re
import unicodedata

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    # 移除副语言标签和填充词
    text = remove_paralinguistic_tags(text)

    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove annotation inside [], (), {}
    text = re.sub(r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}", "", text)

    # Arabic digits mapping
    digit_map = {
        '0': '영', '1': '일', '2': '이', '3': '삼', '4': '사',
        '5': '오', '6': '육', '7': '칠', '8': '팔', '9': '구'
    }
    text = text.translate(str.maketrans(digit_map))

    korean_english_only_pattern = re.compile(
        r"[^"
        r"\uAC00-\uD7A3"  # Hangul Syllables (现代音节)
        r"\u1100-\u11FF"  # Hangul Jamo (组合字母)
        r"\u3130-\u318F"  # Hangul Compatibility Jamo (兼容字母)
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
