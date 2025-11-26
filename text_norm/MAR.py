import regex as re


def normalize(text: str) -> str:
    """
    https://github.com/Natural-Language-Processing-Elm/open_universal_arabic_asr_leaderboard/blob/main/eval.py

    Arabic text normalization:
    1. Remove punctuation
    2. Remove diacritics
    3. Eastern Arabic numerals to Western Arabic numerals
    """
    # Remove punctuation
    # punctuation = r'[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~،؛؟]'
    # text = re.sub(punctuation, "", text)

    text = re.sub(r'[\u060C\u061B\u061F\u066A-\u066D\u06D4\.\,\!\?\:\;\-\_\(\)\[\]\"\'\/\\،؛؟…“”«»]', '', text)

    # Remove diacritics
    diacritics = r"[\u064B-\u0652]"  # Arabic diacritical marks (Fatha, Damma, etc.)
    text = re.sub(diacritics, "", text)

    # allow only arabics & numbers
    text = re.sub(r"[^\p{Arabic}0-9]+", " ", text).strip()

    # Normalize multiple whitespace characters into a single space
    text = re.sub(r"\s\s+", " ", text)

    # Remove punctuation and symbols
    text = re.sub(r"[\p{P}\p{S}]", "", text)

    """
    Normalize Hamzas and Maddas
    afraid of it imfluencing the meaning of sentences, 
    we only adopt it in evaluation,
    instead of training text
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
    \u0640: tatweel
    \u0651: consonant emphasis
    \u0653: Maddah Above (vowels, combination)
    \u0654: Hamza Above (vowels, combination)
    \u061C: direction indicator
    \u0655: Hamza Below (vowel, combination)
    \u066B: Arabic Decimal Separator
    \u066C: Arabic Thousands Separator
    \u0671: Alif Wasla (used in Quran)
    """    

    #    摩洛哥方言常见变体统一（持续补充中，越常用越靠前）
    #    这些替换顺序很重要，先处理长的再处理短的
    norm_map = {
        # 经典阿拉伯语 → 摩洛哥口语常见变形
        "إن شاء الله": "انشاءالله",
        "إن شاءالله": "انشاءالله",
        "ما شاء الله": "ماشاءالله",
        
        # 常见缩写/连音
        "والله": "واللاه", "ولا": "ولاه", "بالله": "بلااه",
        "علاش": "علاه",   # 很多转写系统写成 علاش
        "علاش": "علىاش",  # 另一种常见写法也统一
        
        # 疑问词统一
        "اشمن": "شنو", "أشمن": "شنو", "اش": "شنو",
        "اشناهو": "شنو", "اشنو": "شنو",
        "علاش": "علاه", "علا ش": "علاه",
        "فين": "فين",   # 本身就统一
        "كيفاش": "كيفاه", "كيفاش": "كيفاه",
        "كيف": "كيفاه",
        
        # 常见动词/助动词
        "غادي": "غادي",  # 保持
        "بغيت": "بغيت", "بغا": "بغى",
        "كنت": "كنت", "كان": "كان",
        
        # 人称代词后缀统一（非常常见）
        "ني": "نى", "ني ": "نى ",   # -ni → نى
        "ك": "ك",                   # -k 保持
        "ه": "ه", "ها": "ها",       # -ha
        "نا": "نا",                 # -na
        
        # 常见词变形统一（根据实际语料库频率可继续加）
        "هاد": "هاد", "هادي": "هادي",
        "دابا": "دابا", "دبا": "دابا",
        "بزاف": "بزاف", "بزاف": "بزّاف",
        "شوية": "شوية", "شويّة": "شوية",
        "واخا": "واخا", "واخا": "واخّا",
        "صافي": "صافي",
        "لالّاه": "لا",   # “لا والله” 常被写成 لالاه
        "سمح": "سمحلي", "سمحلي": "سمحلي",
        

        # ق often written as گ (Moroccan)
        "گ": "ق",

        # ڭ → ق (Moroccan letter for /g/)
        "ڭ": "ق",

        # چ → ش or ك depending on region; 常统一为 ش
        "چ": "ش",

        # ّ (shadda) often removed
        "ّ": "",

        # Normalize Alef forms
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",

        # taa marbuta → ha
        "ة": "ه",

        # yaa variations
        "ى": "ي",

        # Common Darija particles
        "ماغاديش": "ما غاديش",
        "غادي": "غادي",
        "بزاف": "بزاف",  # keep
        "شحال": "شحال",
        "علاش": "علاش",
        "فين": "فين",
        "عافاك": "عافاك",
    }
    
    # 按键长度倒序替换（避免短词先替换导致长词出错）
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