import re
import unicodedata

from text_norm._common import remove_paralinguistic_tags

def normalize(text: str) -> str:
    """
    Most complete Thai normalization for CER:
    - Unicode NFC normalization (critical for Thai tone/vowel combining order)
    - Remove bracketed content [laugh], (noise)
    - Remove zero-width characters
    - Remove only '#' symbol (not following content)
    - Remove punctuation
    - Convert English digits to Thai digits
    - Remove English/Chinese punctuations
    - Remove spaces (Thai doesn't use them for CER)
    - Keep only Thai characters + Thai digits

    Returns:
        normalize
    """
    # English digits -> Thai digits mapping
    EN2TH_DIGITS = str.maketrans({
        "0": "๐",
        "1": "๑",
        "2": "๒",
        "3": "๓",
        "4": "๔",
        "5": "๕",
        "6": "๖",
        "7": "๗",
        "8": "๘",
        "9": "๙",
    })

    # Zero width characters
    ZERO_WIDTH_CHARS = r"\u200B\u200C\u200D\uFEFF"

    # Bracket labels: [laugh], (noise), {breath}
    BRACKET_PATTERN = r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}"

    # 1. Unicode NFC normalization (VERY IMPORTANT)
    text = unicodedata.normalize("NFC", text)

    # 1.5. remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # 2. Remove annotation inside [], (), {}
    text = re.sub(BRACKET_PATTERN, "", text)

    # 3. Remove '#' only
    text = text.replace("#", "")

    # 4. Remove zero-width characters
    text = re.sub(f"[{ZERO_WIDTH_CHARS}]", "", text)

    # 5. Convert English digits → Thai digits
    text = text.translate(EN2TH_DIGITS)

    # 6. Remove punctuation (use a wide punctuation scope)
    #    Fairseq uses a long list; we simplify: remove all non-Thai and non-Thai-digits
    text = re.sub(r"[^\u0E00-\u0E7F]", "", text)

    # 7. Final NFC again (to ensure stability)
    text = unicodedata.normalize("NFC", text)

    return text


if __name__ == "__main__":
    for item in [
        "ไม่ ไม่ [laugh] ไม่ หนูไม่ได้ตั้งใจ",
        "(เสียงหัวเราะ) ก็แบบว่า หนูตกใจมาก",
        r"พี่เค้าพูดว่า {breath} เดี๋ยวมาแป๊บนึงนะ",
        "พอดีอยู่ข้างพี่แอฟ # อ่า ต้องรีบไป",
        "วันนี้หนูตื่นตอน 7 โมง",
        "พี่คะ [laugh] หนูถึงบ้านแล้วค่าาา~ 555 😂😂",
        "โอเคค่ะ 100%",
        "เก๋"
    ]:
        print(f"{item}\n{normalize(item)}\n------")