import regex as re

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    """
    Common Arabic text normalization (MSA + dialect-universal):
    - Remove Tashkeel/diacritics (harakat)
    - Normalize Hamza variants (أ إ آ → ا, ؤ → و, ئ → ي)
    - normalization Alef Maksura (ى → ي)
    - normalization Teh Marbuta (ة → ه)
    - 处理波斯语/外来字母 (پ → ب, ڤ → ف, گ → ك, چ → ج)
    - 移除 Tatweel (ـ)
    - 移除零宽字符 (ZWNJ, ZWJ)
    - 移除标签 (<...>, [...])
    - 移除标点和符号
    - 东方阿拉伯数字 → 西方数字
    - normalization空格
    """
    text = remove_paralinguistic_tags(text)

    # Remove Tashkeel (发音符号)
    # U+0610-U+061A (Quranic marks), U+064B-U+065F (Standard harakat), U+0670 (superscript alef)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670]', '', text)

    # 波斯语/外来字母normalization
    text = re.sub('پ', 'ب', text)
    text = re.sub('ڤ', 'ف', text)
    text = re.sub('گ', 'ك', text)
    text = re.sub('چ', 'ج', text)

    # Hamza normalization
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ؤ', 'و', text)
    text = re.sub(r'ئ', 'ي', text)

    # 过滤犹豫词 (连续 alif: ااا+)
    text = re.sub(r'ااا+', '', text)

    # Alef Maksura → Yeh
    text = re.sub(r'ى', 'ي', text)

    # Teh Marbuta → Heh
    text = re.sub(r'ة', 'ه', text)

    # Tatweel
    text = re.sub(r'ـ', '', text)

    # 零宽字符
    text = re.sub(r'[\u200c\u200d\u200e\u200f\u00ad]', '', text)

    # Remove标签
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)

    # Removepunctuation和符号
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # 东方阿拉伯numbers → 西方
    _EASTERN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    text = text.translate(_EASTERN)

    # normalization空格
    text = re.sub(r'\s+', ' ', text).strip()

    return text
