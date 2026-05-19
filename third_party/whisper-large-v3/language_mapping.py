"""
Language code mapping - Whisper ASR
Map 3-letter country codes to Whisper language names
Only includes countries that exist in timestamp directory
"""

# Mapping table of country codes to Whisper language names
COUNTRY_CODE_TO_LANGUAGE = {
    # Middle East region - Arabic
    "ARE": "arabic",    # ARE - UAE - arabic
    "IRQ": "arabic",    # IRQ - Iraq - arabic
    "EGY": "arabic",    # EGY - Egypt - arabic
    "SAU": "arabic",    # SAU - Saudi Arabia - arabic
    "DZA": "arabic",    # DZA - Algeria - arabic
    "MAR": "arabic",    # MAR - Morocco - arabic

    # Asia region
    "KOR": "korean",    # KOR - Korea - korean
    "JPN": "japanese",  # JPN - Japan - japanese
    "THA": "thai",      # THA - Thailand - thai
    "VNM": "vietnamese", # VNM - Vietnam - vietnamese
    "IDN": "indonesian", # IDN - Indonesia - indonesian
    "MYS": "malay",     # MYS - Malaysia - malay
    "PHL": "tagalog",   # PHL - Philippines - tagalog
}

def country_code_to_language(country_code: str) -> str:
    """
    Convert a 3-letter country code to a Whisper language name

    Args:
        country_code (str): 3-letter country code (e.g., "ARE", "KOR")

    Returns:
        str: Whisper language name (e.g., "arabic", "korean")

    Raises:
        ValueError: If the country code is not supported
    """
    country_code = country_code.upper().strip()

    if country_code not in COUNTRY_CODE_TO_LANGUAGE:
        raise ValueError(f"Unsupported country code: {country_code}. "
                       f"Supported country codes: {list(COUNTRY_CODE_TO_LANGUAGE.keys())}")

    return COUNTRY_CODE_TO_LANGUAGE[country_code]

def get_supported_country_codes() -> list:
    """Get list of all supported 3-letter country codes"""
    return list(COUNTRY_CODE_TO_LANGUAGE.keys())

def get_language_info() -> dict:
    """
    Get detailed language information mapping
    Return format: {country_code: {"country_name": "", "language_code": "", "language_name": ""}}
    """
    language_info = {
        "ARE": {"country_name": "UAE", "language_code": "arabic", "language_name": "Arabic"},
        "IRQ": {"country_name": "Iraq", "language_code": "arabic", "language_name": "Arabic"},
        "EGY": {"country_name": "Egypt", "language_code": "arabic", "language_name": "Arabic"},
        "SAU": {"country_name": "Saudi Arabia", "language_code": "arabic", "language_name": "Arabic"},
        "DZA": {"country_name": "Algeria", "language_code": "arabic", "language_name": "Arabic"},
        "MAR": {"country_name": "Morocco", "language_code": "arabic", "language_name": "Arabic"},
        "KOR": {"country_name": "Korea", "language_code": "korean", "language_name": "Korean"},
        "JPN": {"country_name": "Japan", "language_code": "japanese", "language_name": "Japanese"},
        "THA": {"country_name": "Thailand", "language_code": "thai", "language_name": "Thai"},
        "VNM": {"country_name": "Vietnam", "language_code": "vietnamese", "language_name": "Vietnamese"},
        "IDN": {"country_name": "Indonesia", "language_code": "indonesian", "language_name": "Indonesian"},
        "MYS": {"country_name": "Malaysia", "language_code": "malay", "language_name": "Malay"},
        "PHL": {"country_name": "Philippines", "language_code": "tagalog", "language_name": "Tagalog"},
    }
    return language_info

# Test function
if __name__ == "__main__":
    # Test all supported country codes
    print("Supported country codes and language mapping:")
    print("-" * 60)

    lang_info = get_language_info()
    for code in sorted(COUNTRY_CODE_TO_LANGUAGE.keys()):
        country = lang_info[code]["country_name"]
        lang_code = lang_info[code]["language_code"]
        lang_name = lang_info[code]["language_name"]
        print(f"{code} - {country} -> {lang_code} ({lang_name})")

    print("-" * 60)
    print(f"Total supported countries/regions: {len(COUNTRY_CODE_TO_LANGUAGE)}")
