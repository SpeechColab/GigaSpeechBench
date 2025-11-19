"""
Language code mapping for Whisper ASR
Maps 3-letter country codes to Whisper language names
"""

# Mapping from 3-letter country codes to Whisper language names
COUNTRY_CODE_TO_LANGUAGE = {
    # Arabic countries
    "IRQ": "arabic",    # Iraq
    "SAU": "arabic",    # Saudi Arabia
    "EGY": "arabic",    # Egypt
    "ARE": "arabic",    # UAE
    "JOR": "arabic",    # Jordan
    "SYR": "arabic",    # Syria
    "LBN": "arabic",    # Lebanon
    "DZA": "arabic",    # Algeria

    # English countries
    "USA": "english",   # United States
    "GBR": "english",   # United Kingdom
    "AUS": "english",   # Australia
    "CAN": "english",   # Canada
    "IND": "english",   # India
    "NGA": "english",   # Nigeria
    "KEN": "english",   # Kenya
    "ZAF": "english",   # South Africa

    # Chinese
    "CHN": "chinese",   # China
    "TWN": "chinese",   # Taiwan
    "HKG": "chinese",   # Hong Kong
    "SGP": "chinese",   # Singapore

    # Spanish
    "ESP": "spanish",   # Spain
    "MEX": "spanish",   # Mexico
    "ARG": "spanish",   # Argentina
    "COL": "spanish",   # Colombia
    "PER": "spanish",   # Peru
    "VEN": "spanish",   # Venezuela

    # French
    "FRA": "french",    # France
    "CAN": "french",    # Canada (French speaking)
    "BEL": "french",    # Belgium
    "CHE": "french",    # Switzerland
    "MAR": "french",    # Morocco
    "TUN": "french",    # Tunisia

    # German
    "DEU": "german",    # Germany
    "AUT": "german",    # Austria
    "CHE": "german",    # Switzerland

    # Russian
    "RUS": "russian",   # Russia
    "BLR": "russian",   # Belarus
    "KAZ": "russian",   # Kazakhstan

    # Portuguese
    "BRA": "portuguese", # Brazil
    "PRT": "portuguese", # Portugal
    "AGO": "portuguese", # Angola
    "MOZ": "portuguese", # Mozambique

    # Italian
    "ITA": "italian",   # Italy
    "CHE": "italian",   # Switzerland

    # Japanese
    "JPN": "japanese",  # Japan

    # Korean
    "KOR": "korean",    # South Korea

    # Hindi
    "IND": "hindi",     # India

    # Turkish
    "TUR": "turkish",   # Turkey

    # Dutch
    "NLD": "dutch",     # Netherlands
    "BEL": "dutch",     # Belgium

    # Swedish
    "SWE": "swedish",   # Sweden

    # Norwegian
    "NOR": "norwegian", # Norway

    # Danish
    "DNK": "danish",    # Denmark

    # Finnish
    "FIN": "finnish",   # Finland

    # Polish
    "POL": "polish",    # Poland

    # Czech
    "CZE": "czech",     # Czech Republic

    # Hungarian
    "HUN": "hungarian", # Hungary

    # Romanian
    "ROU": "romanian",  # Romania

    # Bulgarian
    "BGR": "bulgarian", # Bulgaria

    # Croatian
    "HRV": "croatian",  # Croatia

    # Serbian
    "SRB": "serbian",   # Serbia

    # Ukrainian
    "UKR": "ukrainian", # Ukraine

    # Greek
    "GRC": "greek",     # Greece

    # Hebrew
    "ISR": "hebrew",    # Israel

    # Thai
    "THA": "thai",      # Thailand

    # Vietnamese
    "VNM": "vietnamese", # Vietnam

    # Indonesian
    "IDN": "indonesian", # Indonesia

    # Malaysian
    "MYS": "malay",     # Malaysia

    # Filipino/Tagalog
    "PHL": "tagalog",   # Philippines

    # Bengali
    "BGD": "bengali",   # Bangladesh

    # Tamil
    "LKA": "tamil",     # Sri Lanka

    # Urdu
    "PAK": "urdu",      # Pakistan

    # Persian/Farsi
    "IRN": "persian",   # Iran
    "AFG": "persian",   # Afghanistan
}

def country_code_to_language(country_code: str) -> str:
    """
    Convert 3-letter country code to Whisper language name

    Args:
        country_code (str): 3-letter country code (e.g., "IRQ", "USA")

    Returns:
        str: Whisper language name (e.g., "arabic", "english")

    Raises:
        ValueError: If country code is not supported
    """
    country_code = country_code.upper().strip()

    if country_code not in COUNTRY_CODE_TO_LANGUAGE:
        # Try to guess based on common patterns
        if country_code.startswith("AR"):
            return "arabic"
        elif country_code.startswith("EN"):
            return "english"
        elif country_code.startswith("ZH"):
            return "chinese"
        elif country_code.startswith("ES"):
            return "spanish"
        elif country_code.startswith("FR"):
            return "french"
        elif country_code.startswith("DE"):
            return "german"
        elif country_code.startswith("RU"):
            return "russian"
        else:
            raise ValueError(f"Unsupported country code: {country_code}. "
                           f"Supported codes: {list(COUNTRY_CODE_TO_LANGUAGE.keys())}")

    return COUNTRY_CODE_TO_LANGUAGE[country_code]

def get_supported_country_codes() -> list:
    """Get list of all supported 3-letter country codes"""
    return list(COUNTRY_CODE_TO_LANGUAGE.keys())

# Test function
if __name__ == "__main__":
    # Test some conversions
    test_codes = ["IRQ", "USA", "CHN", "ESP", "FRA", "UNKNOWN","DZA"]

    for code in test_codes:
        try:
            language = country_code_to_language(code)
            print(f"{code} -> {language}")
        except ValueError as e:
            print(f"{code} -> ERROR: {e}")