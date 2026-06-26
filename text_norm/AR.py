import regex as re

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    """
    Generic Arabic text normalization (Modern Standard Arabic + dialect-general):
    - Remove Tashkeel / diacritics (harakat)
    - Normalize Hamza variants (أ إ آ → ا, ؤ → و, ئ → ي)
    - Normalize Alef Maksura (ى → ي)
    - Normalize Teh Marbuta (ة → ه)
    - Handle Persian/foreign letters (پ → ب, ڤ → ف, گ → ك, چ → ج)
    - Remove Tatweel (ـ)
    - Remove zero-width characters (ZWNJ, ZWJ)
    - Remove tags (<...>, [...])
    - Remove punctuation and symbols
    - Eastern Arabic numerals → Western numerals
    - Normalize whitespace
    """
    text = remove_paralinguistic_tags(text)

    # Remove Tashkeel (diacritics)
    # U+0610-U+061A (Quranic marks), U+064B-U+065F (standard harakat), U+0670 (superscript alef)
    text = re.sub(r'[\u0610-\u061A\u064B-\u065F\u0670]', '', text)

    # Persian/foreign letter normalization
    text = re.sub('پ', 'ب', text)
    text = re.sub('ڤ', 'ف', text)
    text = re.sub('گ', 'ك', text)
    text = re.sub('چ', 'ج', text)

    # Hamza normalization
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ؤ', 'و', text)
    text = re.sub(r'ئ', 'ي', text)

    # Filter hesitation words (consecutive alif: ااا+)
    text = re.sub(r'ااا+', '', text)

    # Normalize Alef Maksura to Yeh
    text = re.sub(r'ى', 'ي', text)

    # Normalize Teh Marbuta to Heh
    text = re.sub(r'ة', 'ه', text)

    # Remove Tatweel
    text = re.sub(r'ـ', '', text)

    # Zero-width characters
    text = re.sub(r'[\u200c\u200d\u200e\u200f\u00ad]', '', text)

    # Remove tags
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)

    # Remove punctuation and symbols
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # Eastern Arabic numerals → Western
    _EASTERN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    text = text.translate(_EASTERN)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text
