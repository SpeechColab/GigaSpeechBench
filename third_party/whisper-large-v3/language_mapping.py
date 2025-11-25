"""
语言代码映射表 - Whisper ASR
将3字母国家代码映射到Whisper语言名称
仅包含timestamp目录中实际存在的国家
"""

# 国家代码到Whisper语言名称的映射表
COUNTRY_CODE_TO_LANGUAGE = {
    # 中东地区 - 阿拉伯语
    "ARE": "arabic",    # ARE - 阿联酋 - arabic - 阿拉伯语
    "IRQ": "arabic",    # IRQ - 伊拉克 - arabic - 阿拉伯语
    "EGY": "arabic",    # EGY - 埃及 - arabic - 阿拉伯语
    "SAU": "arabic",    # SAU - 沙特阿拉伯 - arabic - 阿拉伯语
    "DZA": "arabic",    # DZA - 阿尔及利亚 - arabic - 阿拉伯语
    "MAR": "arabic",    # MAR - 摩洛哥 - arabic - 阿拉伯语

    # 亚洲地区
    "KOR": "korean",    # KOR - 韩国 - korean - 韩语
    "JPN": "japanese",  # JPN - 日本 - japanese - 日语
    "THA": "thai",      # THA - 泰国 - thai - 泰语
    "VNM": "vietnamese", # VNM - 越南 - vietnamese - 越南语
    "IDN": "indonesian", # IDN - 印度尼西亚 - indonesian - 印尼语
    "MYS": "malay",     # MYS - 马来西亚 - malay - 马来语
    "PHL": "tagalog",   # PHL - 菲律宾 - tagalog - 塔加洛语（菲律宾语）
}

def country_code_to_language(country_code: str) -> str:
    """
    将3字母国家代码转换为Whisper语言名称

    Args:
        country_code (str): 3字母国家代码 (例如: "ARE", "KOR")

    Returns:
        str: Whisper语言名称 (例如: "arabic", "korean")

    Raises:
        ValueError: 如果不支持该国家代码
    """
    country_code = country_code.upper().strip()

    if country_code not in COUNTRY_CODE_TO_LANGUAGE:
        raise ValueError(f"不支持的国家代码: {country_code}. "
                       f"支持的国家代码: {list(COUNTRY_CODE_TO_LANGUAGE.keys())}")

    return COUNTRY_CODE_TO_LANGUAGE[country_code]

def get_supported_country_codes() -> list:
    """获取所有支持的3字母国家代码列表"""
    return list(COUNTRY_CODE_TO_LANGUAGE.keys())

def get_language_info() -> dict:
    """
    获取详细的语言信息映射表
    返回格式: {国家代码: {"国家中文名": "", "语言代码": "", "语言中文名": ""}}
    """
    language_info = {
        "ARE": {"国家中文名": "阿联酋", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "IRQ": {"国家中文名": "伊拉克", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "EGY": {"国家中文名": "埃及", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "SAU": {"国家中文名": "沙特阿拉伯", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "DZA": {"国家中文名": "阿尔及利亚", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "MAR": {"国家中文名": "摩洛哥", "语言代码": "arabic", "语言中文名": "阿拉伯语"},
        "KOR": {"国家中文名": "韩国", "语言代码": "korean", "语言中文名": "韩语"},
        "JPN": {"国家中文名": "日本", "语言代码": "japanese", "语言中文名": "日语"},
        "THA": {"国家中文名": "泰国", "语言代码": "thai", "语言中文名": "泰语"},
        "VNM": {"国家中文名": "越南", "语言代码": "vietnamese", "语言中文名": "越南语"},
        "IDN": {"国家中文名": "印度尼西亚", "语言代码": "indonesian", "语言中文名": "印尼语"},
        "MYS": {"国家中文名": "马来西亚", "语言代码": "malay", "语言中文名": "马来语"},
        "PHL": {"国家中文名": "菲律宾", "语言代码": "tagalog", "语言中文名": "塔加洛语"},
    }
    return language_info

# 测试函数
if __name__ == "__main__":
    # 测试所有支持的国家代码
    print("支持的国家代码和语言映射:")
    print("-" * 60)

    lang_info = get_language_info()
    for code in sorted(COUNTRY_CODE_TO_LANGUAGE.keys()):
        country = lang_info[code]["国家中文名"]
        lang_code = lang_info[code]["语言代码"]
        lang_name = lang_info[code]["语言中文名"]
        print(f"{code} - {country} -> {lang_code} ({lang_name})")

    print("-" * 60)
    print(f"总计支持 {len(COUNTRY_CODE_TO_LANGUAGE)} 个国家/地区")