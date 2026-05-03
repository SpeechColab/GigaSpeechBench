import importlib

from text_norm._common import remove_paralinguistic_tags  # noqa: F401

# Language code alias mapping
# Map non-standard dialect codes to existing 3-letter modules
_LANG_ALIASES = {
    # CH-EN-Dialects (Chinese dialects use CHN normalizer)
    "JIN":   "CHN",
    "MIN":   "CHN",
    "WU":    "CHN",
    "XIANG": "CHN",
    "YUE":   "CHN",
    # Vertical-Domain Chinese use CHN
    "AGR-CH": "CHN", "AIT-CH": "CHN", "ART-CH": "CHN", "BIO-CH": "CHN",
    "ECM-CH": "CHN", "EDU-CH": "CHN", "ENG-CH": "CHN", "ENT-CH": "CHN",
    "FIN-CH": "CHN", "HUM-CH": "CHN", "LAW-CH": "CHN", "MED-CH": "CHN",
    "MIL-CH": "CHN",
    # Vertical-Domain English use USA
    "AGR-EN": "USA", "AIT-EN": "USA", "ART-EN": "USA", "BIO-EN": "USA",
    "ECM-EN": "USA", "EDU-EN": "USA", "ENG-EN": "USA", "ENT-EN": "USA",
    "FIN-EN": "USA", "HUM-EN": "USA", "LAW-EN": "USA", "MED-EN": "USA",
    "MIL-EN": "USA",
    # CH-EN-Dialects English use USA
    "CHN-EN": "USA", "IDN-EN": "USA", "JPN-EN": "USA", "PHL-EN": "USA",
    "SCT-EN": "USA", "SGP-EN": "USA",
    # _hard variants
    "JPN_HARD": "JPN",
    "KOR_HARD": "KOR",
    # SYR has its own Syrian dialect normalizer
    # "SYR": "ARE",  # No longer using ARE, switched to SYR.py
}


def get_normalizer(lang_code: str):
    """
    Load the normalize() function for a language code.

    Resolution order:
      1. Check _LANG_ALIASES for a mapped 3-letter code
      2. If code is 3 letters, try importing text_norm.<CODE>
      3. If hyphenated, try the prefix (e.g. CHN-EN → CHN)
      4. If underscored, try the prefix (e.g. JPN_hard → JPN)
      5. Fall back to remove_paralinguistic_tags only
    """
    if not isinstance(lang_code, str):
        raise TypeError("lang_code must be a string, e.g. 'ARE'")

    code = lang_code.upper()

    # Try to resolve module name
    candidates = []

    # 1. Alias mapping
    if code in _LANG_ALIASES:
        candidates.append(_LANG_ALIASES[code])

    # 2. Original code (2-3 letters)
    if 2 <= len(code) <= 3:
        candidates.append(code)

    # 3. Hyphen prefix
    if "-" in code:
        prefix = code.split("-", 1)[0]
        if len(prefix) == 3:
            candidates.append(prefix)

    # 4. Underscore prefix
    if "_" in code:
        prefix = code.split("_", 1)[0]
        if len(prefix) == 3:
            candidates.append(prefix)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    for cand in unique:
        try:
            module = importlib.import_module(f"text_norm.{cand}")
            if hasattr(module, "normalize"):
                return module.normalize
        except Exception:
            continue

    # Fallback: only remove paralinguistic tags
    return remove_paralinguistic_tags
