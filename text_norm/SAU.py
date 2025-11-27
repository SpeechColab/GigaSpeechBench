import regex as re

# -----------------------------
# saudi normalization
# -----------------------------
def normalize(text: str) -> str:
    if text is None:
        return ""

    # Remove punctuation
    text = re.sub(r"[\p{P}\p{S}]", "", text)

    # Remove diacritics
    text = re.sub(r"[\u064b-\u0652]", "", text)

    # Normalize similar chars
    text = re.sub(r"[إأآٱ]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"ؤ", "و", text)
    text = re.sub(r"ئ]", "ي", text)

    # Remove tatweel
    text = re.sub(r"ـ", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text

if __name__ == "__main__":
    examples = [
        "اللهم صلِّ وسلمْ على سيدِنا محمد، أهلاً وسهلاً",
        "اللهم صلي وسلم على سيدنا مُحَمَّدٌ",
        "أأأ التدريب باحتراف",
        "إإنَّهُ لاعبٌ رائعٌ",
        "آآآه هذا التأثير كبيرٌ",
        "ٱلسَّلام عليكم ورحمة الله",
        "خليك جــاهــز ــــ اطلب وجبتك",
        "مبـــروووكـــ يــا شباااب",
        "رؤساء الأندية كثيرين",
        "مسؤولين في النادي الهلال",
        "أهـــلاً وسهـلاً     بالجميـــع",
        "تتضـيـعُ الإنفـرادةُ بسببِ الـتـشكيـل",
        "هذا سوءُ الحظّ فعلاً!",
        "مباراة مؤجَّلة بين الهلالِ والنصرِ",
        "يا أخي عندَك أفضل لاعبٍ في آسيا سالم الدوسري",
        "الغائب جزئياً من بعد بيرسـبوليس",
        "أأأ يعني هذي مشكلة لياقـيّة",
        "وإن شاءَ الله يجيبوا كأسَ العالم",
        "عبدالله الشِّيحَان، لاعبٌ طيّب",
        "بيريرا من ويست بروميتش",
    ]
    
    print("原始 → 标准化后\n")
    for ex in examples:
        print(f"{ex}")
        print(f"{normalize(ex)}\n")