import regex as re

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    """
    Normalize Arabic text (UAE dialect):
    - Remove Tashkeel (diacritics)。
    - Normalize various Hamza forms (أ, إ, آ, ؤ, ئ) to simple Alif (ا)。
    - 过滤重复的 Alif（如 "أأأ" 或 "ااا" 等犹豫/思考词）。
    - normalization Alef Maksura (ى) 为 Yeh (ي)。
    - 处理波斯语字母（پ, ڤ）。
    - 移除 Tatweel (ـ)。
    - 移除零宽不连接符 (ZWNJ)。
    - 移除 <> 及其内部的字符（标签）。
    - Remove punctuation。
    - 东方阿拉伯数字转换为西方阿拉伯数字。
    - normalization空格。
    
    Args:
        text: 要normalization的阿拉伯语文本
        
    Returns:
        normalization后的文本
    """
    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Remove Tashkeel (发音符号)
    # Unicode 范围 U+0617–U+061A (Quranic annotation), U+064B–U+0652 (Standard Tashkeel)
    patt_tashkeel = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = re.sub(patt_tashkeel, '', text)

    # normalization波斯语字母
    text = re.sub('پ', 'ب', text)  # Persian Pe to Arabic Ba
    text = re.sub('ڤ', 'ف', text)  # Persian Ve to Arabic Fa

    # Normalize various Hamza forms为 Alif
    text = re.sub(r'[أإآ]', 'ا', text)  # Hamza on Alif variants
    text = re.sub(r'[ؤ]', 'و', text)    # Hamza on Waw
    text = re.sub(r'[ئ]', 'ي', text)    # Hamza on Yeh

    # 过滤犹豫/思考词（如 "ااا" 或 "أأأ" 等，已统一为 "ا"）
    text = re.sub(r'ااا+', '', text)

    # normalization Alef Maksura (ى) 为 Yeh (ي)
    text = re.sub(r'ى', 'ي', text)

    # Remove Tatweel (ـ)
    text = re.sub(r'ـ', '', text)

    # Remove零宽不连接符 (ZWNJ)
    text = re.sub(r'\u200c', '', text)

    # Remove <> 、[]及其内部的字符（标签）
    # <[^>]*> 匹配 < 和 > 之间的任何内容（不包括 >）
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)
    
    # Remove所有punctuation符号（Unicode 类别 P）和符号（Unicode 类别 S）
    # \p{P} 匹配所有punctuation符号
    # \p{S} 匹配所有符号
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # 东方阿拉伯numbersconvert为西方阿拉伯numbers
    eastern_to_western_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', 
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for eastern, western in eastern_to_western_numerals.items():
        text = text.replace(eastern, western)

    # normalization空格（多个空格replace为单个空格，并去除首尾空格）
    text = re.sub(r'\s+', ' ', text).strip()

    return text


if __name__ == "__main__":
    text = "الله يسلمك، وكذلك ما أنسى # أأأ أشكر # أأأ حسن الرئيسي."
    print(normalize(text))