import regex as re
from typing import Dict, List

from text_norm._common import remove_paralinguistic_tags

# Predefined constants (improve maintainability)
# Malay high-frequency abbreviation map (extended to cover 90%+ spoken scenarios)
MALAY_ABBREV_MAP: Dict[str, str] = {
    # High-frequency phrases (longer words first, avoid short-word override)
    "tak suka": "tidak suka",
    "tak nak": "tidak nak",
    "tak boleh": "tidak boleh",
    "tak tahu": "tidak tahu",
    "tak ada": "tidak ada",
    "sgt suka": "sangat suka",
    "sgt besar": "sangat besar",
    "sgt kecil": "sangat kecil",
    "cm mana": "seperti mana",
    "cm apa": "seperti apa",
    "dlm kg": "dalam kampung",
    "dlm rumah": "dalam rumah",
    # Basic abbreviations
    "sgt": "sangat", "cm": "seperti", "dlm": "dalam", "kg": "kampung",
    "tak": "tidak", "yg": "yang", "km": "kamu", "org": "orang",
    "hrga": "harga", "brg": "barang", "mn": "mana", "dr": "dari",
    "ke": "kepada", "pd": "pada", "jgn": "jangan", "bkn": "bukan",
    "knp": "kenapa", "klo": "kalau", "lg": "lagi", "skrg": "sekarang",
    "tpi": "tetapi", "utk": "untuk", "blm": "belum", "sudh": "sudah",
    "dlh": "dilihat", "bila": "bila", "kt": "di", "nk": "nak",
    "dgn": "dengan", "krn": "kerana", "sdh": "sudah", "blh": "boleh",
    "hri": "hari", "bln": "bulan", "thn": "tahun", "mnt": "minit",
    "jam": "jam", "kmr": "kamar", "ktm": "keretapi tanah melayu",
    # Normalize colloquial particles (preserve meaning)
    "la": "lah", "loh": "loh", "mah": "mah", "nye": "nya",
}

# Malay spelling-variant map
MALAY_SPELL_VARIANTS: Dict[str, str] = {
    # Compound-word unification (high frequency in ASR)
    "roticanai": "roti canai", "tehtarik": "teh tarik", "nasilemak": "nasi lemak",
    "kuehtelor": "kueh telor", "ayamgoreng": "ayam goreng",
    # Loanword normalization
    "emel": "email", "wayfi": "wifi", "waifi": "wifi", "whatsapp": "whatsapp",
    "facebook": "facebook", "instagram": "instagram", "telegram": "telegram",
    # Common misspellings
    "saya": "saya", "aku": "aku", "anda": "anda", "kamu": "kamu",  # keep pronouns
    "besarbesar": "besar-besar", "cantikcantik": "cantik-cantik",  # add hyphens for reduplicated words
}

# Special characters to remove (extended for Malay scenarios)
SPECIAL_CHARS_PATTERN = re.compile(
    r'[\u0021-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E'  # basic punctuation
    r'\u060C\u061B\u061F\u066A-\u066D\u06D4'  # Arabic punctuation (avoid residue)
    r'\u2000-\u206F\u2E00-\u2E7F'  # general punctuation
    r'\u00A0\u00AD\u2010-\u2015\u2026\u2030-\u2039'  # special whitespace/symbols
    r'\uFEFF\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF65'  # full-width symbols
    r'\p{Emoji}\p{Emoji_Modifier}\p{Emoji_Presentation}\p{Emoji_Component}]'  # emoji
)

# Keep only Malay Latin letters, digits, and spaces
VALID_CHARS_PATTERN = re.compile(r"[^\p{Latin}0-9\s]+")

# Eastern-Arabic/full-width digit mapping
EASTERN_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize(text: str) -> str:
    """
    Malay (MYS) ASR text normalization (full version):
    1. Remove all punctuation, special symbols, and emoji
    2. Clean invalid characters (keep only Latin Malay letters + digits + spaces)
    3. Normalize digits (Eastern Arabic → Western, full-width → half-width)
    4. Standardize colloquial abbreviations (handle longer phrases first)
    5. Unify spelling variants (compound words, loanwords, misspellings)
    6. Preserve Malay reduplication (core linguistic feature)
    7. Clean up extra whitespace and unify case
    8. Fix common Malay grammar/spelling issues
    """
    # Empty-text guard
    if not text or text.strip() == "":
        return ""

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Step 1: Remove all special chars, punctuation, emoji
    text = SPECIAL_CHARS_PATTERN.sub("", text)

    # Step 2: Keep only valid Malay characters (Latin letters, digits, spaces)
    text = VALID_CHARS_PATTERN.sub(" ", text).strip()

    # Step 3: Digit normalization
    # Eastern Arabic digits → Western Arabic digits
    text = text.translate(EASTERN_ARABIC_DIGITS)
    # Full-width digits → half-width digits
    text = text.translate(FULLWIDTH_DIGITS)

    # Step 4: Clean up extra spaces (repeat to be thorough)
    text = re.sub(r"\s+", " ", text).strip()

    # Step 5: Lowercase (Malay is case-insensitive, reduces ASR vocabulary)
    text = text.lower()

    # Step 6: Normalize abbreviations (replace longest-first to avoid short overriding long)
    combined_norm_map = {**MALAY_ABBREV_MAP, **MALAY_SPELL_VARIANTS}
    for word, normalized in sorted(combined_norm_map.items(), key=lambda x: len(x[0]), reverse=True):
        # Replace on word boundaries (avoid partial matches, e.g. "km" not replacing "kmkm")
        # Fix the partial-match bug of the original direct-replace version
        pattern = re.compile(rf"\b{re.escape(word)}\b")
        text = pattern.sub(normalized, text)

    # Step 7: Fix reduplicated-word hyphens (core Malay feature, keep meaning)
    # Match consecutive duplicated words (e.g. "besarbesar" → "besar-besar")
    text = re.sub(r"(\b\w+)\1\b", r"\1-\1", text)

    # Step 8: Handle currency units (high-frequency Malay ASR scenario)
    # RM → keep, normalize spacing (e.g. "rm50" → "rm 50")
    text = re.sub(r"rm(\d+)", r"rm \1", text)
    # "ringgit" → unify to "rm" (unify ASR vocabulary)
    text = re.sub(r"(\d+) ringgit", r"rm \1", text)

    # Step 9: Handle measurement units (normalize spacing, e.g. "2kg" → "2 kg")
    text = re.sub(r"(\d+)([a-z]+)", r"\1 \2", text)

    # Step 10: Final whitespace cleanup
    text = re.sub(r"\s+", " ", text).strip()

    return text


if __name__ == "__main__":
    # Extended test cases (cover all core scenarios)
    examples = [
        # Basic abbrev + punctuation + emoji
        "Hai! Saya sgt suka makan roti canai dlm kg yg brg hrga rm50... 😋",
        # Negation + long phrases + Eastern Arabic digits
        "Tak nak pergi dr kg ke kota, jgn cm org lain yg bkn tahu! ٥ minit lagi",
        # Full-width digits + loanwords + spelling variants
        "Kamu knp mn lg tak datang? ２０２５年 Saya beli emel wayfi waifi!",
        # Reduplication + compound words + noise
        " [cough] Nasi lemak dan teh tarik adalah makanan kegemaran saya [breath] besarbesar!",
        # Currency + units + long sentence
        "Brg ini hrga rm50/kg terlalu tinggi, knp harga brg ni sgt mahal? 3kg = 150 ringgit",
        # Colloquial particles + abbreviation combo
        "Jgn lupa bawa barang kamu la, dlm km pergi ke pasar malam loh!",
        # Spelling errors + reduplication
        "Saya tak suka ayamgoreng roticanai, cantikcantik bunga di taman!",
        # Empty text / boundary test
        "",
        "   !!!   ١٢٣  ４５６   😊😊   ",
    ]

    print("=" * 80)
    print("马来语Text Norm 测试结果（原始 → 标准化后）")
    print("=" * 80)
    for idx, ex in enumerate(examples, 1):
        normalized = normalize(ex)
        print(f"\n示例 {idx}:")
        print(f"原始: {repr(ex)}")
        print(f"标准化后: {repr(normalized)}")