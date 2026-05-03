import re
import string

from text_norm._common import remove_paralinguistic_tags

# Skip only if entire sentence matches these (case-insensitive)
SKIP_WORDS_STRICT = {"SIL", "MUSIC", "NOISE", "OTHER"}

# fillers
FILLERS = re.compile(
    r"\b(UH|UHH|UM|EH|MM|HM|AH|HUH|HA|ER)\b",
    re.IGNORECASE
)

# Delete angle bracket tags
ANGLE_REGEX = re.compile(r"<[^>]*>")

# Also delete [] tags
BRACKET_REGEX = re.compile(r"\[[^\]]*\]")

# Deletepunctuation
PUNCT_REGEX = re.compile(
    rf"[{re.escape(string.punctuation)}]"
    r"|[\u3000-\u303F]"
    r"|[\u2000-\u206F]"
    r"|[\uFF00-\uFFEF]"
    r"|[\uFE30-\uFE4F]"
    r"|[\u2E00-\u2E7F]"
)

# Delete COMMA / PERIOD / QUESTIONMARK / EXCLAMATIONPOINT （裸词）
REMOVE_TAG_WORDS = re.compile(
    r"\b(COMMA|PERIOD|QUESTIONMARK|EXCLAMATIONPOINT)\b",
    re.IGNORECASE
)

digit_map_en = {
    "0": "ZERO", "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR",
    "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE",
}

DIGIT_REGEX = re.compile(r"[0-9]")


def normalize(text: str):
    if not text:
        return ""

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # A）精确判断整句是否为垃圾词（严格匹配）
    t = text.strip().upper()
    if t in SKIP_WORDS_STRICT:
        return None

    # B）统一大写
    text = t

    # C）删 fillers
    text = FILLERS.sub("", text)

    # D）删 <...>
    text = ANGLE_REGEX.sub("", text)

    # E）删 [...]   ← 新增
    text = BRACKET_REGEX.sub("", text)

    # F）删 COMMA / PERIOD / QUESTIONMARK / EXCLAMATIONPOINT
    text = REMOVE_TAG_WORDS.sub("", text)

    # G）删punctuation
    text = PUNCT_REGEX.sub("", text)

    # H）numbersreplace
    text = DIGIT_REGEX.sub(lambda m: digit_map_en[m.group(0)], text)

    # I）合并空格
    text = " ".join(text.split())

    return text