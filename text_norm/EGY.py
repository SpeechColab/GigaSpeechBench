import re
from typing import Dict

from text_norm._common import remove_paralinguistic_tags

def normalize(text: str) -> str:
    """
    Egyptian Arabic text normalization function
    
    Features:
    1. Normalize the various Alef variants
    2. Uniformly handle hamza symbols
    3. Convert Western digits to Arabic-Indic digits
    4. Clean up extra spaces and punctuation
    5. Other Egyptian-dialect-specific normalization
    
    Parameters:
    text: the input Egyptian Arabic text
        
    Returns:
    the normalized Egyptian Arabic text
    
    Example:
    >>> normalize("إزيك يا جماعة ده 123")
    "ازيك يا جماعة دي ١٢٣"
    """
    if not text.strip():
        return text

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Step 1: Normalize Arabic letter variants
    
    # Map the various Alef variants to a standard Alef
    ALEF_VARIANTS = {
        'أ': 'ا',  # Alef with hamza above
        'إ': 'ا',  # Alef with hamza below
        'آ': 'ا',  # Alef with madda above
        'ٱ': 'ا',  # Alef wasla
    }
    
    # Normalize the various Hamza variants
    HAMZA_VARIANTS = {
        'ء': 'ئ',  # standalone hamza -> hamza on a letter
        'ؤ': 'و',  # hamza on waw -> plain waw
    }
    
    # Apply Alef normalization
    for variant, standard in ALEF_VARIANTS.items():
        text = text.replace(variant, standard)
    
    # Apply Hamza normalization
    for variant, standard in HAMZA_VARIANTS.items():
        text = text.replace(variant, standard)

    # Step 2: Number conversion
    
    # Western digits to Arabic-Indic digits mapping
    western_to_arabic = {
        '0': '٠',
        '1': '١',
        '2': '٢',
        '3': '٣',
        '4': '٤',
        '5': '٥',
        '6': '٦',
        '7': '٧',
        '8': '٨',
        '9': '٩'
    }
    for w_num, a_num in western_to_arabic.items():
        text = text.replace(w_num, a_num)
    
    # Step 3: Egyptian-dialect-specific processing
    
    # Normalize common Egyptian dialect words
    egyptian_specific = {
        'ده': 'دي',     # normalize a common demonstrative pronoun
        'انت': 'انتِ',  # masculine form correction
        'انتا': 'انتَ', # feminine form correction
        'ايه': 'اي',    # simplify a common question word
        'مش': 'موش',    # normalize negation word
        'عايز': 'عاوز', # normalize variants of "want"
        'عوز': 'عاوز',  # 
    }
    
    # Apply Egyptian dialect word replacement
    words = text.split()
    normalized_words = []
    for word in words:
        # Check whether it is an Egyptian dialect word
        lowered = word.lower()
        if lowered in egyptian_specific:
            normalized_words.append(egyptian_specific[lowered])
        else:
            normalized_words.append(word)
    
    text = ' '.join(normalized_words)
    
    # Step 4: Clean up the text
    
    # Remove all diacritics (except shadda)
    text = re.sub(r'[\u064B-\u065F]', '', text)  # Unicode range covers Arabic diacritics
    
    # Normalize spaces and handle special whitespace characters
    text = re.sub(r'[ ]+', ' ', text)  # collapse multiple spaces into one
    text = re.sub(r'[\u00A0\u1680\u2000-\u200F\u2028-\u202F\u205F\u3000\uFEFF]', ' ', text)  # handle various special spaces
    text = text.strip()
    
    return text


def get_normalizer(language_code: str):
    """
    Factory method to get the normalization function
    
    Parameters:
    language_code: ISO 639-3 language code (e.g. 'ARE' for Egyptian Arabic)
        
    Returns:
    the normalization function for the corresponding language
        
    Raises:
    ValueError: raised when an unsupported language code is passed
    """
    if language_code.upper() == 'EGY':
        return normalize
    else:
        raise ValueError(f"不支持的语言代码: {language_code}. 目前仅支持'EGY'(埃及语)")
