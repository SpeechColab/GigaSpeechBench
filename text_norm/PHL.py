import re
import unicodedata
from typing import List

from text_norm._common import remove_paralinguistic_tags

def normalize(text: str) -> str:
    """
    Filipino normalization (final stable version)
    
    Flow:
    1. Protect URL/email
    2. Remove accents
    3. Remove repeated characters
    4. Expand contractions
    5. Standardize spelling
    6. Clean up
    7. Remove punctuation (key: before restoring)
    8. Restore URL/email
    9. Uppercase
    
    Features:
    - Does not break URL / email
    - Suitable for ASR WER/CER
    """

    if not text or not text.strip():
        return text

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    protected_spans = []
    text = protect_special_content(text, protected_spans)

    # ===== Core normalization =====
    text = remove_accents(text)
    text = reduce_repeated_characters(text)
    text = expand_contractions(text)
    text = standardize_spelling(text)

    # ===== Post-processing =====
    text = clean_text(text)

    text = remove_punctuation(text)   # 👈 key: before restore

    text = restore_protected_content(text, protected_spans)

    text = text.upper()

    return text


# =========================
# Protect / restore
# =========================

def protect_special_content(text: str, protected_spans: List) -> str:
    """Protect URL and email"""
    patterns = [
        r'https?://\S+',
        r'\b[\w.-]+@[\w.-]+\.\w+\b'
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            idx = len(protected_spans)
            protected_spans.append(match.group())

            text = (
                text[:match.start()]
                + f" PROTECTED_{idx} "
                + text[match.end():]
            )
    return text


def restore_protected_content(text: str, protected_spans: List) -> str:
    """Restore URL / email"""
    for i, content in enumerate(protected_spans):
        text = text.replace(f"PROTECTED_{i}", content)
    return text


# =========================
# Normalization steps
# =========================

def remove_accents(text: str) -> str:
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')


def reduce_repeated_characters(text: str) -> str:
    return re.sub(r'([a-zA-Z])\1+', r'\1', text)


def expand_contractions(text: str) -> str:
    CONTRACTIONS = {
        r"'yung\b": "ang",
        r"'yng\b": "ang",
        r"'ung\b": "ang",
        r"d'yan\b": "diyan",
        r"n'ung\b": "ng",

        r"'y\b": "ang",
        r"'t\b": "at",
        r"'n\b": "ng",
        r"'di\b": "hindi",
        r"'pag\b": "kapag",
    }

    for pattern, replacement in CONTRACTIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text


def standardize_spelling(text: str) -> str:
    SPELLING_VARIANTS = {
        'azucar': 'asukal',
        'kompyuter': 'komputer',
        'nang': 'ng',
    }

    words = text.split()
    out = []

    for word in words:
        word_lower = remove_accents(word.lower())
        stem = re.sub(r'[^\w]', '', word_lower)

        if stem in SPELLING_VARIANTS:
            new = adjust_case(word, SPELLING_VARIANTS[stem])
            punctuation = re.sub(r'[\w]', '', word)
            out.append(new + punctuation)
        else:
            out.append(word)

    return ' '.join(out)


def adjust_case(original: str, replacement: str) -> str:
    if original.isupper():
        return replacement.upper()
    elif original.istitle():
        return replacement.capitalize()
    return replacement.lower()


# =========================
# Post-processing
# =========================

def clean_text(text: str) -> str:
    text = re.sub(r'([.,!?])\1+', r'\1', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_punctuation(text: str) -> str:
    """
    Remove all punctuation (ASR-friendly version)
    Keep: letters + digits + spaces
    """
    return re.sub(r'[^a-zA-Z0-9\s]', '', text)


# =========================
# API
# =========================

def get_normalizer(language_code: str):
    if language_code.upper() in ('FIL', 'PHL'):
        return normalize
    raise ValueError(f"Unsupported language: {language_code}")