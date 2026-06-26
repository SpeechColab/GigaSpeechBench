import regex as re

from text_norm._common import remove_paralinguistic_tags


def normalize(text: str) -> str:
    """
    Normalize Arabic text (UAE dialect):
    - Remove Tashkeel (diacritics).
    - Normalize the various forms of Hamza (أ, إ, آ, ؤ, ئ) to a simple Alif (ا).
    - Filter repeated Alif (e.g. hesitation/thinking words like "أأأ" or "ااا").
    - Normalize Alef Maksura (ى) to Yeh (ي).
    - Handle Persian letters (پ, ڤ).
    - Remove Tatweel (ـ).
    - Remove zero-width non-joiner (ZWNJ).
    - Remove <> and the characters inside it (tags).
    - Remove punctuation.
    - Convert Eastern Arabic numerals to Western Arabic numerals.
    - Normalize whitespace.

    Parameters:
        text: the Arabic text to normalize

    Returns:
        the normalized text
    """
    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Remove Tashkeel (diacritics)
    # Unicode ranges U+0617-U+061A (Quranic marks), U+064B-U+0652 (standard Tashkeel)
    patt_tashkeel = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
    text = re.sub(patt_tashkeel, '', text)

    # Normalize Persian letters
    text = re.sub('پ', 'ب', text)  # Persian Pe -> Arabic Ba
    text = re.sub('ڤ', 'ف', text)  # Persian Ve -> Arabic Fa

    # Normalize the various forms of Hamza to Alif
    text = re.sub(r'[أإآ]', 'ا', text)  # Hamza variants above Alif
    text = re.sub(r'[ؤ]', 'و', text)    # Hamza above Waw
    text = re.sub(r'[ئ]', 'ي', text)    # Hamza above Yeh

    # Filter hesitation/thinking words (e.g. "ااا" or "أأأ", already unified to "ا")
    text = re.sub(r'ااا+', '', text)

    # Normalize Alef Maksura (ى) to Yeh (ي)
    text = re.sub(r'ى', 'ي', text)

    # Remove Tatweel (ـ)
    text = re.sub(r'ـ', '', text)

    # Remove zero-width non-joiner (ZWNJ)
    text = re.sub(r'\u200c', '', text)

    # Remove <> and [] and the characters inside them (tags)
    # <[^>]*> matches any content between < and > (excluding >)
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[[^]]*\]', '', text)
    
    # Remove all punctuation (Unicode category P) and symbols (Unicode category S)
    # \p{P} matches all punctuation
    # \p{S} matches all symbols
    text = re.sub(r'[\p{P}\p{S}]', '', text)

    # Convert Eastern Arabic numerals to Western Arabic numerals
    eastern_to_western_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', 
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for eastern, western in eastern_to_western_numerals.items():
        text = text.replace(eastern, western)

    # Normalize whitespace (collapse multiple spaces to a single one, strip leading/trailing)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


if __name__ == "__main__":
    text = "الله يسلمك، وكذلك ما أنسى # أأأ أشكر # أأأ حسن الرئيسي."
    print(normalize(text))