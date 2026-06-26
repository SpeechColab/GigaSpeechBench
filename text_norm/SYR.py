"""
Syrian Arabic dialect text normalization (Syrian Arabic / Levantine Arabic)

Characteristics of the Syrian dialect:
  - Belongs to the Levantine Arabic family
  - Uses the standard Arabic writing system, but has unique phonetic features in speech
  - Common hesitation/filler word: أأأ (elongated hamza)
  - Very few phonetic marks (only a tiny amount of Tashkeel)
  - Text contains many paralinguistic tags such as [breath], # أأأ
  
Differences from other Arabic-dialect normalizers:
  - Keep the distinction between Teh Marbuta (ة) and Heh (ه) (pronounced differently in Syrian)
  - Keep Alef Maksura (ى); do not map it to Yeh (ي)
    (ى and ي have a phonetic distinction at word endings in Syrian)
  - More conservative Hamza normalization: only unify أ/إ/آ → ا,
    keep ؤ and ئ (ؤ/ئ are pronounced differently from و/ي in Syrian)
  - Remove standalone Hamza (ء) (the glottal stop is usually dropped in Syrian speech)
"""

import regex as re

from text_norm._common import remove_paralinguistic_tags

# ── Eastern Arabic numerals → Western Arabic numerals mapping ──
_EASTERN_TO_WESTERN = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)

# ── Tashkeel (diacritics) ──
_RE_TASHKEEL = re.compile(r"[\u0617-\u061A\u064B-\u0652]")

# ── Punctuation and symbols (Unicode categories P and S) ──
_RE_PUNCT = re.compile(r"[\p{P}\p{S}]")

# ── Tatweel / Kashida (joiner) ──
_RE_TATWEEL = re.compile(r"\u0640")

# ── Zero-width characters (ZWNJ, ZWJ, etc.) ──
_RE_ZERO_WIDTH = re.compile(r"[\u200B-\u200F\u202A-\u202E\uFEFF]")

# ── Elongated Alef hesitation word: ااا+ ──
_RE_ALEF_HESITATION = re.compile(r"ااا+")

# ── Multiple spaces ──
_RE_MULTI_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """
    Syrian Arabic dialect text normalization.

    Processing steps:
      1. Remove paralinguistic tags ([breath], # أأأ, etc.)
      2. Remove Tashkeel (diacritics)
      3. Persian letter mapping (پ→ب, ڤ→ف, چ→ج, گ→ك)
      4. Hamza normalization (أ/إ/آ → ا)
      5. Remove standalone Hamza (ء)
      6. Remove Tatweel and zero-width characters
      7. Remove hesitation words (أأأ → empty)
      8. Eastern Arabic numerals → Western Arabic numerals
      9. Remove punctuation
      10. Normalize whitespace
    """
    # 1. Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # 2. Remove Tashkeel (diacritics)
    text = _RE_TASHKEEL.sub("", text)

    # 3. Persian/non-standard letter mapping
    text = text.replace("پ", "ب")   # Persian Pe → Ba
    text = text.replace("ڤ", "ف")   # Persian Ve → Fa
    text = text.replace("چ", "ج")   # Persian Che → Jim
    text = text.replace("گ", "ك")   # Persian Gaf → Kaf

    # 4. Hamza normalization (conservative strategy)
    #    أ (Alef with Hamza above) → ا
    #    إ (Alef with Hamza below) → ا
    #    آ (Alef with Madda) → ا
    #    Note: keep ؤ and ئ
    text = re.sub(r"[أإآ]", "ا", text)

    # 5. Remove standalone Hamza (ء)
    #    The glottal stop is usually dropped in Syrian speech
    text = text.replace("ء", "")

    # 6. Remove Tatweel and zero-width characters
    text = _RE_TATWEEL.sub("", text)
    text = _RE_ZERO_WIDTH.sub("", text)

    # 7. Remove hesitation/thinking words (ااا or longer runs of Alef)
    text = _RE_ALEF_HESITATION.sub("", text)

    # 8. Eastern Arabic numerals → Western Arabic numerals
    text = text.translate(_EASTERN_TO_WESTERN)

    # 9. Remove punctuation
    text = _RE_PUNCT.sub("", text)

    # 10. Normalize whitespace
    text = _RE_MULTI_SPACE.sub(" ", text)

    return text.strip()
