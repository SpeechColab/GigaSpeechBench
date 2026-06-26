import re
import unicodedata

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove annotations inside [], (), {}
    text = re.sub(r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}", "", text)

    # Arabic numeral mapping
    digit_map = {
        "0": "零",
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "七",
        "8": "八",
        "9": "九",
    }
    text = text.translate(str.maketrans(digit_map))

    japanese_english_only_pattern = re.compile(
        r"[^"
        r"a-zA-Z"  # English
        r"\u3040-\u309F"  # Hiragana
        r"\u30A0-\u30FF"  # Katakana
        r"\u31F0-\u31FF"  # Katakana Phonetic Extensions
        r"\uFF65-\uFF9F"  # Halfwidth Katakana
        r"\u4E00-\u9FFF"  # CJK Unified Ideographs
        r"\u3400-\u4DBF"  # CJK Extension A
        r"\U00020000-\U0002A6DF"  # CJK Extension B
        r"\U0002A700-\U0002B73F"  # CJK Extension C
        r"\U0002B740-\U0002B81F"  # CJK Extension D
        r"\U0002B820-\U0002CEAF"  # CJK Extension E
        r"\U0002CEB0-\U0002EBEF"  # CJK Extension F
        r"\U00030000-\U0003134F"  # CJK Extension G
        r"\U00031350-\U000323AF"  # CJK Extension H
        r"\uF900-\uFAFF"  # CJK Compatibility Ideographs
        r"\u3005"  # 々
        r"\u3006"  # 〆
        r"\u3007"  # 〇
        r"]"
    )

    text = japanese_english_only_pattern.sub("", text).replace("・", "")

    text = text.upper()

    return text


if __name__ == "__main__":
    import sys

    ori_text = sys.argv[1]
    print(normalize(ori_text))
