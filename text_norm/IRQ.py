import regex as re

from text_norm._common import remove_paralinguistic_tags

def normalize(text: str) -> str:
    """
    Arabic text normalization:
    1. Remove punctuation
    2. Remove diacritics
    3. Convert Eastern Arabic numerals to Western Arabic numerals

    Parameters
    ---------
    text: str
        The text to normalize
    Returns
    ---------
    The normalized text
    """
    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Remove punctuation
    text = re.sub(r"[\p{p}\p{s}]", "", text)

    # Remove diacritics
    diacritics = r'[\u064B-\u0652]'  # Arabic diacritics (Fatha, Damma, etc.)
    text = re.sub(diacritics, '', text)
    
    # Normalize Hamza and Madda
    text = re.sub('پ', 'ب', text)
    text = re.sub('ڤ', 'ف', text)
    text = re.sub(r'[آ]', 'ا', text)
    text = re.sub(r'[أإ]', 'ا', text)
    text = re.sub(r'[ؤ]', 'و', text)
    text = re.sub(r'[ئ]', 'ي', text)
    text = re.sub(r'[ء]', '', text)   

    # Transliterate Eastern Arabic numerals to Western Arabic numerals
    eastern_to_western_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', 
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for eastern, western in eastern_to_western_numerals.items():
        text = text.replace(eastern, western)

    # Remove tatweel (kashida, U+0640)
    text = re.sub(r"\u0640", "", text)
    
    # Remove hesitation words like hmm/uhm
    text = re.sub(r"اا+", "", text)
    
    # Collapse multiple whitespace characters into a single space
    text = re.sub(r'\s\s+', ' ', text)

    return text.strip()
