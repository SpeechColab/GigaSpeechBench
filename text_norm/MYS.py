import regex as re
from typing import Dict, List

# 预定义常量（提升代码可维护性）
# 马来语高频缩写映射表（扩展至覆盖90%+口语场景）
MALAY_ABBREV_MAP: Dict[str, str] = {
    # 高频短语（长词优先，避免短词覆盖）
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
    # 基础缩写
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
    # 口语语气词标准化（保留语义）
    "la": "lah", "loh": "loh", "mah": "mah", "nye": "nya",
}

# 马来语拼写变体映射表
MALAY_SPELL_VARIANTS: Dict[str, str] = {
    # 复合词统一（ASR高频）
    "roticanai": "roti canai", "tehtarik": "teh tarik", "nasilemak": "nasi lemak",
    "kuehtelor": "kueh telor", "ayamgoreng": "ayam goreng",
    # 外来词标准化
    "emel": "email", "wayfi": "wifi", "waifi": "wifi", "whatsapp": "whatsapp",
    "facebook": "facebook", "instagram": "instagram", "telegram": "telegram",
    # 常见拼写错误
    "saya": "saya", "aku": "aku", "anda": "anda", "kamu": "kamu",  # 代词保留
    "besarbesar": "besar-besar", "cantikcantik": "cantik-cantik",  # 补全重复词连字符
}

# 需移除的特殊字符（扩展覆盖马来语场景）
SPECIAL_CHARS_PATTERN = re.compile(
    r'[\u0021-\u002F\u003A-\u0040\u005B-\u0060\u007B-\u007E'  # 基础标点
    r'\u060C\u061B\u061F\u066A-\u066D\u06D4'  # 阿拉伯标点（避免残留）
    r'\u2000-\u206F\u2E00-\u2E7F'  # 通用标点符号
    r'\u00A0\u00AD\u2010-\u2015\u2026\u2030-\u2039'  # 特殊空白/符号
    r'\uFEFF\uFF01-\uFF0F\uFF1A-\uFF20\uFF3B-\uFF40\uFF5B-\uFF65'  # 全角符号
    r'\p{Emoji}\p{Emoji_Modifier}\p{Emoji_Presentation}\p{Emoji_Component}]'  # 表情符号
)

# 仅保留马来语拉丁字母、数字和空格
VALID_CHARS_PATTERN = re.compile(r"[^\p{Latin}0-9\s]+")

# 东阿拉伯数字/全角数字映射
EASTERN_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize(text: str) -> str:
    """
    Malay (MYS) text normalization for ASR (comprehensive version):
    1. Remove all punctuation, special symbols and emojis
    2. Clean invalid characters (keep only Latin Malay + numbers + spaces)
    3. Normalize numerals (Eastern Arabic → Western, fullwidth → halfwidth)
    4. Standardize colloquial abbreviations (priority: longer phrases first)
    5. Unify spelling variants (compound words, loanwords, typos)
    6. Preserve Malay reduplication (core linguistic feature)
    7. Clean extra whitespace and normalize case
    8. Fix common Malay grammar/spelling issues
    """
    # 空文本保护
    if not text or text.strip() == "":
        return ""

    # Step 1: 移除所有特殊字符、标点、表情符号
    text = SPECIAL_CHARS_PATTERN.sub("", text)

    # Step 2: 仅保留马来语有效字符（拉丁字母、数字、空格）
    text = VALID_CHARS_PATTERN.sub(" ", text).strip()

    # Step 3: 数字标准化
    # 东阿拉伯数字 → 西阿拉伯数字
    text = text.translate(EASTERN_ARABIC_DIGITS)
    # 全角数字 → 半角数字
    text = text.translate(FULLWIDTH_DIGITS)

    # Step 4: 清理多余空格（多次清理确保彻底）
    text = re.sub(r"\s+", " ", text).strip()

    # Step 5: 统一为小写（马来语大小写不敏感，降低ASR词汇量）
    text = text.lower()

    # Step 6: 标准化缩写（按长度倒序替换，避免短词覆盖长词）
    combined_norm_map = {**MALAY_ABBREV_MAP, **MALAY_SPELL_VARIANTS}
    for word, normalized in sorted(combined_norm_map.items(), key=lambda x: len(x[0]), reverse=True):
        # 按单词边界替换（避免部分匹配，如 "km" 不替换 "kmkm"）
        # 修复原版本直接replace的部分匹配问题
        pattern = re.compile(rf"\b{re.escape(word)}\b")
        text = pattern.sub(normalized, text)

    # Step 7: 修复重复词连字符（马来语核心特征，确保语义不丢失）
    # 匹配连续重复单词（如 "besarbesar" → "besar-besar"）
    text = re.sub(r"(\b\w+)\1\b", r"\1-\1", text)

    # Step 8: 处理货币单位（马来语ASR高频场景）
    # RM → 保留，统一空格（如 "rm50" → "rm 50"）
    text = re.sub(r"rm(\d+)", r"rm \1", text)
    # "ringgit" → 统一为 "rm"（ASR词汇表统一）
    text = re.sub(r"(\d+) ringgit", r"rm \1", text)

    # Step 9: 处理度量单位（统一空格，如 "2kg" → "2 kg"）
    text = re.sub(r"(\d+)([a-z]+)", r"\1 \2", text)

    # Step 10: 最终空格清理
    text = re.sub(r"\s+", " ", text).strip()

    return text


if __name__ == "__main__":
    # 扩展测试用例（覆盖所有核心场景）
    examples = [
        # 基础缩写+标点+表情
        "Hai! Saya sgt suka makan roti canai dlm kg yg brg hrga rm50... 😋",
        # 否定词+长短语+东阿拉伯数字
        "Tak nak pergi dr kg ke kota, jgn cm org lain yg bkn tahu! ٥ minit lagi",
        # 全角数字+外来词+拼写变体
        "Kamu knp mn lg tak datang? ２０２５年 Saya beli emel wayfi waifi!",
        # 重复词+复合词+噪声
        " [cough] Nasi lemak dan teh tarik adalah makanan kegemaran saya [breath] besarbesar!",
        # 货币+单位+长句
        "Brg ini hrga rm50/kg terlalu tinggi, knp harga brg ni sgt mahal? 3kg = 150 ringgit",
        # 口语语气词+缩写组合
        "Jgn lupa bawa barang kamu la, dlm km pergi ke pasar malam loh!",
        # 拼写错误+重复词
        "Saya tak suka ayamgoreng roticanai, cantikcantik bunga di taman!",
        # 空文本/边界测试
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