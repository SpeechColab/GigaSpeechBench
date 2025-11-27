import re
import string

PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"
    r"|[\u3000-\u303F]"
    r"|[\u2000-\u206F]"
    r"|[\uFF00-\uFFEF]"
    r"|[\uFE30-\uFE4F]"
    r"|[\u2E00-\u2E7F]"
)

digit_map_chn = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
}

DIGIT_REGEX = re.compile(r"[0-9]")

def normalize(text: str) -> str:
    text = text.strip()
    text = PUNCT_REGEX.sub("", text)

    # 阿拉伯数字 → 中文数字
    text = DIGIT_REGEX.sub(lambda m: digit_map_chn[m.group(0)], text)

    return text
