import regex as re

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    """
    通用阿拉伯语文本规范化（Modern Standard Arabic + 方言通用）：
    - 移除 Tashkeel / 发音符号 (harakat)
    - 规范化 Hamza 变体 (أ إ آ → ا, ؤ → و, ئ → ي)
    - 规范化 Alef Maksura (ى → ي)
    - 规范化 Teh Marbuta (ة → ه)
    - 处理波斯语/外来字母 (پ → ب, ڤ → ف, گ → ك, چ → ج)
    - 移除 Tatweel (ـ)
    - 移除零宽字符 (ZWNJ, ZWJ)
    - 移除标签 (<...>, [...])
    - 移除标点和符号
    - 东方阿拉伯数字 → 西方数字
    - 规范化空格
    """
    text = remove_paralinguistic_tags(text)

    # 移除 Tashkeel (发音符号)
    # U+0610-U+061A (Quranic marks), U+064B-U+065F (Standard harakat), U+0670 (superscript alef)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670]', '', text)

    # 波斯语/外来字母规范化
    text = re.sub('پ', 'ب', text)
    text = re.sub('ڤ', 'ف', text)
    text = re.sub('گ', 'ك', text)
    text = re.sub('چ', 'ج', text)

    # Hamza 规范化
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

    # 移除标签
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)

    # 移除标点和符号
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # 东方阿拉伯数字 → 西方
    _EASTERN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    text = text.translate(_EASTERN)

    # 规范化空格
    text = re.sub(r'\s+', ' ', text).strip()

    return text
