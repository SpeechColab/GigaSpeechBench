import importlib

def get_normalizer(lang_code: str):
    """
    Load the normalize() function from a language-specific module,
    identified by a three-letter uppercase language code.

    Example:
        normalize = get_normalizer("ARE")
        text = normalize("some text")
    """

    if not isinstance(lang_code, str):
        raise TypeError("lang_code must be a string, e.g. 'ARE'")

    if len(lang_code) != 3:
        raise ValueError("lang_code must be a 3-letter code, e.g. 'ARE'")

    # enforce uppercase module name
    lang_code = lang_code.upper()

    module = importlib.import_module(f"text_norm.{lang_code}")
    if not hasattr(module, "normalize"):
        raise AttributeError(f"{lang_code}.py must contain a normalize(text) function")

    return module.normalize
