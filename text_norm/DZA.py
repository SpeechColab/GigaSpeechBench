import regex as re

from text_norm._common import remove_paralinguistic_tags


def arabic_text_normalize(text):
    """
    Unify variants of other Arabic dialects into the Algerian dialect variant
    """
    stop_words = {
        # ==== Hesitation / thinking ====
        'ااا', 'آآآ', 'اممم', 'إممم', 'ممم', 'أمم', 'هممم',
        'إيه', 'إي', 'إييه',

        # ==== Exclamation / reaction ====
        'آ', 'آه', 'آها', 'أوه', 'أوو', 'إيوا', 'إيوة',
        'هيه', 'ههه', 'هاه',

        # ==== Transition / continuation ====
        'طيب', 'يعني', 'بس', 'أها', 'المهم', 'خلاص', 'تمام',
        'بصراحة', 'شوف', 'والله',

        # ==== Vocative / attention-getting ====
        'يا', 'وي', 'وَيْ', 'وييي', 'ألو', 'لك',

        # ==== Dialect filler words ====
        # Levantine
        'شو', 'هيك',
        # Maghreb
        'هاك', 'باه', 'هاو', 'ياودي', 'هاديك',
        # Gulf
        'زين', 'عد', 'هاه',

        # ==== Stalling / emphasis ====
        'كذا', 'كذا يعني', 'زي', 'مثل',

        # ==== Shushing / other sounds ====
        'ششش', 'هههه', 'مممم'
    }
    
    stop_words = {
        'ااا', 'إيه', 'إممم', 'طيب', 'أمم', 'آ', 'آه', 'امم', 'ممم', 'آه', 'يا', 'أوه', 'وَيْ', 'آها', 'إي', 'ششش', 'هيه'
    }

    # stopwords = {
    #     'اا', 'ااا', 'ام', 'أمم', 'إممم', 'امم', 'ممم', 'آ', 'آه', 'آها', 'اه', 'إيه', 'إي',
    #     'طيب', 'يا', 'أوه', 'وَيْ', 'ششش', 'هيه', 'ه', 'او', 'يعني', 'حاجة', 'بص', 'شوف',
    #     'حسنا', 'اوكي', 'ماشي', 'ايوا', 'ها', 'تمام', 'خلاص', 'كويس'
    # }

    # Normalize elongated sounds and laughter
    long_aaa_re = re.compile(r'ا{3,}')         # اااا
    long_hhh_re = re.compile(r'ه{3,}')         # هههه
    long_mmm_re = re.compile(r'م{3,}')         # مممم
    long_alif_re = re.compile(r'آ{2,}')        # آآآ

    if isinstance(text, str):
        text = text.split()
    else:
        assert isinstance(text, list)

    filtered = []
    for w in text:
        # w = remove(w, punctuations=True)

        w = long_aaa_re.sub('', w)
        w = long_hhh_re.sub('', w)
        w = long_mmm_re.sub('', w)
        w = long_alif_re.sub('', w)

        if w == '' or w in stop_words:
            continue
        filtered.append(w)
    return ' '.join(filtered)


def normalize(text: str) -> str:
    """
    https://github.com/Natural-Language-Processing-Elm/open_universal_arabic_asr_leaderboard/blob/main/eval.py

    Arabic text normalization:
    1. Remove punctuation
    2. Remove diacritics
    3. Convert Eastern Arabic numerals to Western Arabic numerals
    """
    # Remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # Remove punctuation
    # punctuation = r'[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~،؛؟]'
    # text = re.sub(punctuation, "", text)

    text = re.sub(r'[\u060C\u061B\u061F\u066A-\u066D\u06D4\.\,\!\?\:\;\-\_\(\)\[\]\"\'\/\\،؛؟…“”«»]', '', text)

    # Remove diacritics
    diacritics = r"[\u064B-\u0652]"  # Arabic diacritics (Fatha, Damma, etc.)
    text = re.sub(diacritics, "", text)
    
    # Keep only Arabic letters and digits
    text = re.sub(r"[^\p{Arabic}0-9]+", " ", text).strip()

    # Collapse multiple whitespace characters into a single space
    text = re.sub(r"\s\s+", " ", text)

    # Remove punctuation and symbols
    text = re.sub(r"[\p{P}\p{S}]", "", text)

    """
    Normalize Hamza and Madda
    Because we worry it may affect sentence semantics,
    we apply this only during evaluation,
    and not for training text
    """
    text = re.sub("پ", "ب", text)
    text = re.sub("ڤ", "ف", text)
    text = re.sub(r"[آ]", "ا", text)
    text = re.sub(r"[أإ]", "ا", text)
    text = re.sub(r"[ؤ]", "و", text)
    text = re.sub(r"[ئ]", "ي", text)
    text = re.sub(r"[ء]", "", text)

    text = re.sub(r'\u0640', '', text)      # remove tatweel

    # Transliterate Eastern Arabic numerals to Western Arabic numerals
    fullwidth_digits = str.maketrans(
        "０１２３４５６７８９",
        "0123456789"
    )
    text = text.translate(fullwidth_digits)

    eastern_arabic_digits = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )
    text = text.translate(eastern_arabic_digits)

    text = re.sub(r'\u0640\u0651\u0653\u0654\u0655\u061C\u066B\u066C\u0671', '', text)  
    """
    \u0640: tatweel (joiner)
    \u0651: consonant emphasis mark (shadda)
    \u0653: Maddah above (vowel, combining mark)
    \u0654: Hamza above (vowel, combining mark)
    \u061C: directional mark
    \u0655: Hamza below (vowel, combining mark)
    \u066B: Arabic decimal separator
    \u066C: Arabic thousands separator
    \u0671: Alif Wasla (used in the Quran)
    """    
    # Remove tatweel and invisible characters

    # Normalize U+069C to U+0634 (Maghreb dialect to MSA)
    # return text.replace('ڜ', 'ش')

    return text


if __name__ == "__main__":
    examples = [
        "سلام، كيفاش داير؟ بغيت نخرج دابا... شنو غادي نديرو؟",
        "والله ما بغيتش نجي، علاش جيتي متأخر؟ ٣ ساعات وانا نستناك!",
        "Inchallah ghada nshri l-karhab 7mra, 2 litres dyal lmazot wakha?",
        "كما يمتو على عضان [laugh] أنعم إيه.",
        " [cough] ملكنا يا الحنين قهرونا المسؤولين.",
        "ان خوها اللي بغا يخرجها من الدار [breath] غادي نسمعو القصة ديالها.",
        "هادي ٢٠ درهم، بغيت جوج كيلو ديال الطماطم، ماشي غالية بزاف؟",
        "لا والله، صافي كملنا، سمحلي ولكن ما بغيتش هادشي"
    ]
    
    print("原始 → 标准化后\n")
    for ex in examples:
        print(f"{ex}")
        print(f"{normalize(ex)}\n")
