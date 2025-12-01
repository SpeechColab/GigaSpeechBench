import re
import unicodedata


def normalize(text: str) -> str:
    # Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Remove annotation inside [], (), {}
    text = re.sub(r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}", "", text)

    # Arabic digits mapping
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
        r"\u3040-\u309F"  # 平假名
        r"\u30A0-\u30FF"  # 片假名
        r"\u31F0-\u31FF"  # 片假名扩展
        r"\uFF65-\uFF9F"  # 半角片假名
        r"\u4E00-\u9FFF"  # CJK 基本区
        r"\u3400-\u4DBF"  # CJK 扩展 A
        r"\U00020000-\U0002A6DF"  # CJK 扩展 B
        r"\U0002A700-\U0002B73F"  # CJK 扩展 C
        r"\U0002B740-\U0002B81F"  # CJK 扩展 D
        r"\U0002B820-\U0002CEAF"  # CJK 扩展 E
        r"\U0002CEB0-\U0002EBEF"  # CJK 扩展 F
        r"\U00030000-\U0003134F"  # CJK 扩展 G
        r"\U00031350-\U000323AF"  # CJK 扩展 H
        r"\uF900-\uFAFF"  # CJK 兼容汉字
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
