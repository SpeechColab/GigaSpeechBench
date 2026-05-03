import re
import string

from text_norm._common import remove_paralinguistic_tags

# ------------------------------------------------
# Punctuation
# ------------------------------------------------

PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"
    r"|[\u3000-\u303F]"
    r"|[\u2000-\u206F]"
    r"|[\uFF00-\uFFEF]"
    r"|[\uFE30-\uFE4F]"
    r"|[\u2E00-\u2E7F]"
)

# ------------------------------------------------
# Delete parenthetical content
# ------------------------------------------------

SQUARE_REGEX = re.compile(r"\[[^\]]*\]")
ROUND_REGEX = re.compile(r"\([^)]*\)")
CN_ROUND_REGEX = re.compile(r"（[^）]*）")

# ------------------------------------------------
# Delete all whitespace
# ------------------------------------------------

SPACE_REGEX = re.compile(r"\s+")

# ------------------------------------------------
# Numbers → Chinese characters
# ------------------------------------------------

digit_map_chn = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
}

DIGIT_REGEX = re.compile(r"[0-9]")


def normalize(text: str) -> str:

    text = text.strip()

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Delete parenthetical content
    text = SQUARE_REGEX.sub("", text)
    text = ROUND_REGEX.sub("", text)
    text = CN_ROUND_REGEX.sub("", text)

    # Deletepunctuation
    text = PUNCT_REGEX.sub("", text)

    # Numbers → Chinese characters
    text = DIGIT_REGEX.sub(lambda m: digit_map_chn[m.group(0)], text)

    # Delete所有空格
    text = SPACE_REGEX.sub("", text)
    return text

if __name__ == "__main__":
    s = "自己会去处理它， (noise) 然后一步一回脚印儿继续走下它，什么也躲不过，该发生的事还是要发生的。"
    print(normalize(s))