import regex as re

from text_norm._common import remove_paralinguistic_tags


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
    # text = re.sub("پ", "ب", text)
    # text = re.sub("ڤ", "ف", text)
    # text = re.sub(r"[آ]", "ا", text)
    # text = re.sub(r"[أإ]", "ا", text)
    # text = re.sub(r"[ؤ]", "و", text)
    # text = re.sub(r"[ئ]", "ي", text)
    # text = re.sub(r"[ء]", "", text)

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

    #    Common Moroccan dialect variant unification (ongoing; more common ones first)
    #    The replacement order matters: handle longer ones before shorter ones
    norm_map = {
        # Classical Arabic → common Moroccan colloquial forms
        "إن شاء الله": "انشاءالله",
        "إن شاءالله": "انشاءالله",
        "ما شاء الله": "ماشاءالله",
        
        # Common abbreviations/contractions
        "والله": "واللاه", "ولا": "ولاه", "بالله": "بلااه",
        "علاش": "علاه",   # many transcription systems write it as علاش
        "علاش": "علىاش",  # another common spelling, also unified
        
        # Question-word unification
        "اشمن": "شنو", "أشمن": "شنو", "اش": "شنو",
        "اشناهو": "شنو", "اشنو": "شنو",
        "علاش": "علاه", "علا ش": "علاه",
        "فين": "فين",   # already unified
        "كيفاش": "كيفاه", "كيفاش": "كيفاه",
        "كيف": "كيفاه",
        
        # Common verbs/auxiliaries
        "غادي": "غادي",  # keep
        "بغيت": "بغيت", "بغا": "بغى",
        "كنت": "كنت", "كان": "كان",
        
        # Personal-pronoun suffix unification (very common)
        "ني": "نى", "ني ": "نى ",   # -ni → نى
        "ك": "ك",                   # -k keep
        "ه": "ه", "ها": "ها",       # -ha
        "نا": "نا",                 # -na
        
        # Common word-form unification (extend per corpus frequency)
        "هاد": "هاد", "هادي": "هادي",
        "دابا": "دابا", "دبا": "دابا",
        "بزاف": "بزاف", "بزاف": "بزّاف",
        "شوية": "شوية", "شويّة": "شوية",
        "واخا": "واخا", "واخا": "واخّا",
        "صافي": "صافي",
        "لالّاه": "لا",   # “لا والله” often written as لالاه
        "سمح": "سمحلي", "سمحلي": "سمحلي",
        

        # ق is often written as گ in Moroccan dialect
        "گ": "ق",

        # ڭ → ق (letter representing /g/ in Moroccan dialect)
        "ڭ": "ق",

        # چ → ش or ك (depending on region); usually unified to ش
        "چ": "ش",

        # ّ (shadda gemination mark) is usually removed
        "ّ": "",

        # Normalize the various forms of Alef
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",

        # taa marbuta (ة) → ha (ه)
        "ة": "ه",

        # yaa variants
        "ى": "ي",

        # Common Darija function words
        "ماغاديش": "ما غاديش",
        "غادي": "غادي",
        "بزاف": "بزاف",  # keep
        "شحال": "شحال",
        "علاش": "علاش",
        "فين": "فين",
        "عافاك": "عافاك",
    }
    
    # Replace by key length descending (avoid short words breaking long ones)
    for arabic_word, normalized in sorted(norm_map.items(), key=lambda x: len(x[0]), reverse=True):
        text = text.replace(arabic_word, normalized)

    return text


if __name__ == "__main__":
    examples = [
        "سلام، كيفاش داير؟ بغيت نخرج دابا... شنو غادي نديرو؟",
        "والله ما بغيتش نجي، علاش جيتي متأخر؟ ٣ ساعات وانا نستناك!",
        "Inchallah ghada nshri l-karhab 7mra, 2 litres dyal lmazot wakha?",
        "واش گتشوف!! هذا؟ Darija 2025 ??? بزّاف!",
        " [cough] ملكنا يا الحنين قهرونا المسؤولين.",
        "ان خوها اللي بغا يخرجها من الدار [breath] غادي نسمعو القصة ديالها.",
        "هادي ٢٠ درهم، بغيت جوج كيلو ديال الطماطم، ماشي غالية بزاف؟",
        "لا والله، صافي كملنا، سمحلي ولكن ما بغيتش هادشي"
    ]
    
    print("原始 → 标准化后\n")
    for ex in examples:
        print(f"{ex}")
        print(f"{normalize(ex)}\n")