import regex as re


def normalize(text: str) -> str:
    """
    规范化阿拉伯语文本（阿联酋方言）：
    - 移除 Tashkeel (发音符号)。
    - 规范化 Hamza 的各种形式 (أ, إ, آ, ؤ, ئ) 为简单的 Alif (ا)。
    - 过滤重复的 Alif（如 "أأأ" 或 "ااا" 等犹豫/思考词）。
    - 规范化 Alef Maksura (ى) 为 Yeh (ي)。
    - 处理波斯语字母（پ, ڤ）。
    - 移除 Tatweel (ـ)。
    - 移除零宽不连接符 (ZWNJ)。
    - 移除 <> 及其内部的字符（标签）。
    - 移除标点符号。
    - 东方阿拉伯数字转换为西方阿拉伯数字。
    - 规范化空格。
    
    Args:
        text: 要规范化的阿拉伯语文本
        
    Returns:
        规范化后的文本
    """
    # 移除 Tashkeel (发音符号)
    # Unicode 范围 U+0617–U+061A (Quranic annotation), U+064B–U+0652 (Standard Tashkeel)
    patt_tashkeel = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = re.sub(patt_tashkeel, '', text)

    # 规范化波斯语字母
    text = re.sub('پ', 'ب', text)  # Persian Pe to Arabic Ba
    text = re.sub('ڤ', 'ف', text)  # Persian Ve to Arabic Fa

    # 规范化 Hamza 的各种形式为 Alif
    text = re.sub(r'[أإآ]', 'ا', text)  # Hamza on Alif variants
    text = re.sub(r'[ؤ]', 'و', text)    # Hamza on Waw
    text = re.sub(r'[ئ]', 'ي', text)    # Hamza on Yeh

    # 过滤犹豫/思考词（如 "ااا" 或 "أأأ" 等，已统一为 "ا"）
    text = re.sub(r'ااا+', '', text)

    # 规范化 Alef Maksura (ى) 为 Yeh (ي)
    text = re.sub(r'ى', 'ي', text)

    # 移除 Tatweel (ـ)
    text = re.sub(r'ـ', '', text)

    # 移除零宽不连接符 (ZWNJ)
    text = re.sub(r'\u200c', '', text)

    # 移除 <> 、[]及其内部的字符（标签）
    # <[^>]*> 匹配 < 和 > 之间的任何内容（不包括 >）
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)
    
    # 移除所有标点符号（Unicode 类别 P）和符号（Unicode 类别 S）
    # \p{P} 匹配所有标点符号
    # \p{S} 匹配所有符号
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # 东方阿拉伯数字转换为西方阿拉伯数字
    eastern_to_western_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', 
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for eastern, western in eastern_to_western_numerals.items():
        text = text.replace(eastern, western)

    # 规范化空格（多个空格替换为单个空格，并去除首尾空格）
    text = re.sub(r'\s+', ' ', text).strip()

    return text


if __name__ == "__main__":
    text = "الله يسلمك، وكذلك ما أنسى # أأأ أشكر # أأأ حسن الرئيسي."
    print(normalize(text))