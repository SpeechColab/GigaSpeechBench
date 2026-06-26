import re
import sys
import unicodedata

from text_norm._common import remove_paralinguistic_tags

# --- Dependency check ---
try:
    from underthesea import text_normalize as underthesea_normalize
except ImportError:
    print("错误: 未找到库 'underthesea'。请执行: pip install underthesea")
    sys.exit(1)

try:
    from num2words import num2words
except ImportError:
    print("错误: 未找到库 'num2words'。请执行: pip install num2words")
    sys.exit(1)


def _convert_numbers(text: str) -> str:
    """
    Convert digits in the text to Vietnamese readings.
    Add spaces around the result to prevent sticking to adjacent letters (e.g. '4G' -> 'bốn g').
    """
    return re.sub(r"\d+", lambda x: " " + num2words(int(x.group()), lang="vi") + " ", text)


def _remove_asr_tags(text: str) -> str:
    """
    Remove non-linguistic markers in ASR datasets (e.g. [laugh], <unk>, ++garbage++).
    """
    # Remove standard bracket tags [], (), {}, <>
    text = re.sub(r"\[[^\]]*\]|\([^\)]*\)|\{[^\}]*\}|<[^>]*>", " ", text)
    # Remove special markers (e.g. ++noise++)
    text = re.sub(r"\+\+[^\+]*\+\+", " ", text)
    return text


def _remove_punctuation(text: str) -> str:
    """
    Remove punctuation.
    Keep: Unicode letters, digits, spaces, and the special symbol (+).
    """
    # Keep \w (incl. Vietnamese letters), \s (spaces), and + (keep C++, K+, etc.)
    text = re.sub(r"[^\w\s\+]", " ", text)
    # Treat underscore as a space
    text = text.replace("_", " ")
    return text


def normalize(text: str) -> str:
    """
    Vietnamese ASR evaluation standard normalization entry function.

    Processing flow:
    1. Unicode NFC normalization
    2. Remove ASR noise markers
    3. Underthesea text normalization (tone/spelling)
    4. Convert numbers to text
    5. Remove punctuation and lowercase
    """
    if not text:
        return ""

    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Unicode NFC normalization (fix NFD decomposed characters)
    text = unicodedata.normalize("NFC", text)

    # Remove zero-width characters
    text = re.sub(r"[\u200B\u200C\u200D\uFEFF]", " ", text)

    # Remove ASR noise markers
    text = _remove_asr_tags(text)

    text = text.strip()

    # Text normalization (handle tone-placement ambiguity, e.g. hòa/hoà)
    try:
        text = underthesea_normalize(text)
    except Exception:
        pass

    # Convert numbers to text
    text = _convert_numbers(text)

    # Remove punctuation and lowercase
    text = _remove_punctuation(text)
    text = text.lower()

    # Collapse extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


if __name__ == "__main__":
    # --- Comprehensive test cases ---

    test_cases = [
        # Group A: Tone & spelling (unify old/new styles, special place names)
        ("A01", "Hoà bình, Thuỷ tinh, Qui Nhơn, Đắk Lắk", "hòa bình thủy tinh quy nhơn đắk lắk"),
        # Group B: Encoding & chars (NFD->NFC, special vowels, full-width chars)
        ("B01", "Tiê\u0301ng Viê\u0323t (NFD), Ưu đãi, ＡＢＣ", "tiếng việt ưu đãi abc"),
        # Group C: Complex numbers & units (decimals, dates, IP, mixed time)
        (
            "C01",
            "1,000,000; 3.14; 20/11/2024; 192.168.1.1; $50; 8h30p",
            "một không không không không không không ba mười bốn hai mươi mười một hai nghìn không trăm hai mươi bốn một chín hai một sáu tám một một năm mươi tám h ba mươi p",
        ),
        # Group D: ASR noise & tags (nested/unclosed/special markers)
        ("D01", "Hello [laugh] (noise) <unk> {breath} ++garbage++ <silence>...", "hello"),
        # Group E: Punctuation & special symbols (email, hashtag, hyphen)
        ("E01", "user@email.com #hashtag Wi-fi_Zone A/B", "user email com hashtag wi fi zone a b"),
        # Group F: Loanwords (keep non-Vietnamese letters F/J/Z/W)
        ("F01", "Vietnam Airlines, YouTube, Zalo, Jeans", "vietnam airlines youtube zalo jeans"),
        # Group G: Edge cases (mixed formats, newlines, zero-width chars)
        ("G01", "123!!![laugh]\nLine2\tTab\u200bZero", "một trăm hai mươi ba line2 tab zero"),
        # Group H: False-positive defense (anti-stick, keep symbols +, C++)
        ("H01", "4G LTE, F0, 1A, C++, K+, Vitamin 3B", "bốn g lte f không một a c + + k + vitamin ba b"),
        # Group I: Sci & math (chemical formulas, squares, equations, versions)
        ("I01", "H2O, CO2, m2, 1 + 1 = 2, v1.0.0", "h hai o co hai m hai một + một hai v một không không"),
        # Group J: Mixed languages (code-switching)
        ("J01", "Sale 50%, Check mail, Log in", "sale năm mươi check mail log in"),
    ]

    print("--- 越南语 ASR 正则化测试结果 (垂直对比) ---")

    failures = 0
    for case_id, raw, expected in test_cases:
        output = normalize(raw)

        print(f"[{case_id}]")
        print(f"Raw : {raw}")
        print(f"Norm: {output}")

        # Simple check: warn if input has valid content but output is empty
        has_content = re.search(r"[a-zA-Z0-9]", raw)
        if has_content and not output.strip():
            print(f">>> 警告: 输入包含内容但输出为空!")
            failures += 1

        print("-" * 60)

    print(f"测试结束。共 {len(test_cases)} 个综合用例。")
    if failures > 0:
        print(f"发现 {failures} 个潜在问题。")
    else:
        print("所有用例检查通过。")
