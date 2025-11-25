import regex as re

def normalize(text: str) -> str:
    """
    输入：原始文本
    输出：text_norm 后的文本
    """
    text = re.sub(r"[\p{p}\p{s}]", "", text)

    diacritics = r"[\u064b-\u0652]"

    text = re.sub(diacritics, "", text)

    text = re.sub("پ", "ب", text)
    text = re.sub("ڤ", "ف", text)

    text = re.sub(r"[آ]", "ا", text)
    text = re.sub(r"[أإ]", "ا", text)
    text = re.sub(r"[ؤ]", "و", text)
    text = re.sub(r"[ئ]", "ي", text)
    text = re.sub(r"[ء]", "", text)

    text = text.replace("ى", "ي")

    text = text.replace("اً", "ا")

    text = re.sub(r"ه\b", "ة", text)

    western_to_eastern = {
        "0": "٠",
        "1": "١",
        "2": "٢",
        "3": "٣",
        "4": "٤",
        "5": "٥",
        "6": "٦",
        "7": "٧",
        "8": "٨",
        "9": "٩",
    }
    for en, ar in western_to_eastern.items():
        text = text.replace(en, ar)

    text = re.sub(r"\u0640", "", text)

    text = re.sub(r"\s\s+", " ", text)

    return text.strip()
