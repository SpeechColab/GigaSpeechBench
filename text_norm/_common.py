"""
Common paralinguistic tag and filler word removal module.

Paralinguistic tags (from annotation spec):
  [breath]        breath
  [chocking]      choking
  [humph]         humph
  [sigh]          sigh
  [laugh]         laugh
  [cough]         cough
  [hissing]       hissing
  [Throat clear]  throat clearing

Filler word annotation spec:
  #word  Filler words used when speaker hesitates, prefixed with #.
         e.g.: # uh, # أأأ, # eh

Other common annotations:
  <unk>           unknown segment
  (noise)         noise
  (overlap)       overlapping speech
  (~)             trailing
  (sil)           silence
"""

import re

# ──────────────────────────────────────────────
# 1. Bracket tags [breath], [laugh], ...
# ──────────────────────────────────────────────
_RE_SQUARE = re.compile(r"\[[^\]]*\]")

# ──────────────────────────────────────────────
# 2. Angle bracket tags <unk>, ...
# ──────────────────────────────────────────────
_RE_ANGLE = re.compile(r"<[^>]*>")

# ──────────────────────────────────────────────
# 3. Parentheses tags (noise), (overlap), (~), ...
# Only remove short tag-like content (<=30 chars),
# to avoid deleting real parenthetical text
# ──────────────────────────────────────────────
_RE_PAREN = re.compile(r"\([^)]{0,30}\)")
_RE_PAREN_CN = re.compile(r"（[^）]{0,30}）")

# ──────────────────────────────────────────────
# 4. Curly brace tags {breath}, ...
# ──────────────────────────────────────────────
_RE_BRACE = re.compile(r"\{[^}]*\}")

# ──────────────────────────────────────────────
# 5. Filler word markers: # word
# Match # followed by optional space and a word
# e.g.: "# uhh" "# eh," "# อ่า"
# Note: filler removal disabled to avoid
# deleting entire sentences in spaceless scripts.
# ──────────────────────────────────────────────
_RE_FILLER = re.compile(r"#\s*")

# ──────────────────────────────────────────────
# 6. Merge extra whitespace
# ──────────────────────────────────────────────
_RE_MULTI_SPACE = re.compile(r"\s+")


def remove_paralinguistic_tags(text: str) -> str:
    """
    Remove all paralinguistic tags and filler annotations, return cleaned text。

    Processing order:
      1. [...]  Bracket tags [breath], [laugh], ...
      2. <...>  尖括号标签
      3. (...)  圆括号标签（短内容）
      4. （...）全角圆括号标签（短内容）
      5. {...}  花括号标签
      6. # word 填充词
      7. 合并多余空格
    """
    text = _RE_SQUARE.sub("", text)
    text = _RE_ANGLE.sub("", text)
    text = _RE_PAREN.sub("", text)
    text = _RE_PAREN_CN.sub("", text)
    text = _RE_BRACE.sub("", text)
    text = _RE_FILLER.sub("", text)
    text = _RE_MULTI_SPACE.sub(" ", text).strip()
    return text
