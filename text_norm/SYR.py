"""
Syrian Arabic dialect text normalization (Syrian Arabic / Levantine Arabic)

Syrian dialect characteristics:
  - Belongs to Levantine Arabic（Levantine Arabic）家族
  - 使用标准阿拉伯语书写系统，但口语中有独特的语音特征
  - 常见的犹豫/填充词：أأأ (elongated hamza)
  - 音标标注极少（仅极少量 Tashkeel）
  - 文本中包含大量副语言标签 [breath], # أأأ 等
  
与其他阿拉伯方言 normalizer 的区别：
  - 保留 Teh Marbuta (ة) 与 Heh (ه) 的区分（Syria方言中两者发音不同）
  - 保留 Alef Maksura (ى)，不映射为 Yeh (ي)
    （Syria方言中 ى 和 ي 在词尾有语音区分）
  - Hamza normalization更保守：只统一 أ/إ/آ → ا，
    保留 ؤ 和 ئ（Syria方言中 ؤ/ئ 的发音不同于 و/ي）
  - 移除独立 Hamza (ء)（Syria口语中通常省略 glottal stop）
"""

import regex as re

from text_norm._common import remove_paralinguistic_tags

# ── Eastern Arabic → Western Arabic numeral mapping ──
_EASTERN_TO_WESTERN = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)

# ── Tashkeel (diacritical marks) ──
_RE_TASHKEEL = re.compile(r"[\u0617-\u061A\u064B-\u0652]")

# ── Punctuation & symbols (Unicode categories P and S) ──
_RE_PUNCT = re.compile(r"[\p{P}\p{S}]")

# ── Tatweel / Kashida ──
_RE_TATWEEL = re.compile(r"\u0640")

# ── Zero-Width characters (ZWNJ, ZWJ, etc.) ──
_RE_ZERO_WIDTH = re.compile(r"[\u200B-\u200F\u202A-\u202E\uFEFF]")

# ── Elongated Alef hesitation: ااا+ ──
_RE_ALEF_HESITATION = re.compile(r"ااا+")

# ── Multiple spaces ──
_RE_MULTI_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """
    Syrian Arabic dialect text normalization。

    处理步骤：
      1. remove副语言标签 ([breath], # أأأ 等)
      2. 移除 Tashkeel（发音符号）
      3. 波斯语字母映射（پ→ب, ڤ→ف, چ→ج, گ→ك）
      4. Hamza 归一化（أ/إ/آ → ا）
      5. 移除独立 Hamza (ء)
      6. 移除 Tatweel 和零宽字符
      7. 移除犹豫词（أأأ → 空）
      8. 东方阿拉伯数字 → 西方阿拉伯数字
      9. Remove punctuation
      10. 空格归一化
    """
    # 1. remove paralinguistic tags and filler words
    text = remove_paralinguistic_tags(text)

    # 2. remove Tashkeel (发音符号)
    text = _RE_TASHKEEL.sub("", text)

    # 3. 波斯语/非标准字母映射
    text = text.replace("پ", "ب")   # Persian Pe → Ba
    text = text.replace("ڤ", "ف")   # Persian Ve → Fa
    text = text.replace("چ", "ج")   # Persian Che → Jim
    text = text.replace("گ", "ك")   # Persian Gaf → Kaf

    # 4. Hamza normalize（保守策略）
    #    أ (Alef with Hamza above) → ا
    #    إ (Alef with Hamza below) → ا
    #    آ (Alef with Madda) → ا
    #    注意：保留 ؤ 和 ئ
    text = re.sub(r"[أإآ]", "ا", text)

    # 5. remove独立 Hamza (ء)
    #    Syria口语中 glottal stop 通常省略
    text = text.replace("ء", "")

    # 6. remove Tatweel 和零宽字符
    text = _RE_TATWEEL.sub("", text)
    text = _RE_ZERO_WIDTH.sub("", text)

    # 7. remove犹豫/思考词（ااا 或更长的连续 Alef）
    text = _RE_ALEF_HESITATION.sub("", text)

    # 8. 东方阿拉伯numbers → 西方阿拉伯numbers
    text = text.translate(_EASTERN_TO_WESTERN)

    # 9. removepunctuation符号
    text = _RE_PUNCT.sub("", text)

    # 10. 空格normalize
    text = _RE_MULTI_SPACE.sub(" ", text)

    return text.strip()
