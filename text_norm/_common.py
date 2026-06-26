"""
Common module: removes paralinguistic tags and filler words.

Paralinguistic tags (from the annotation spec):
  [breath]        breathing
  [chocking]      choking / sobbing
  [humph]         humph
  [sigh]          sigh
  [laugh]         laughter
  [cough]         cough
  [hissing]       hissing
  [Throat clear]  throat clearing

Filler-word convention:
  #word  a filler word used when the speaker hesitates or thinks,
         prefixed with #.
         Examples: # uh, # أأأ, # eh

Other common annotations:
  <unk>           unknown segment
  (noise)         noise
  (overlap)       overlapping speech
  (~)             elongation
  (sil)           silence
"""

import re

# ──────────────────────────────────────────────
# 1. Square-bracket tags  [breath], [laugh], ...
# ──────────────────────────────────────────────
_RE_SQUARE = re.compile(r"\[[^\]]*\]")

# ──────────────────────────────────────────────
# 2. Angle-bracket tags  <unk>, ...
# ──────────────────────────────────────────────
_RE_ANGLE = re.compile(r"<[^>]*>")

# ──────────────────────────────────────────────
# 3. Parenthesis tags  (noise), (overlap), (~), ...
#    Note: only remove short tag-like content (<=30 chars),
#    to avoid deleting real parenthetical text
# ──────────────────────────────────────────────
_RE_PAREN = re.compile(r"\([^)]{0,30}\)")
_RE_PAREN_CN = re.compile(r"（[^）]{0,30}）")

# ──────────────────────────────────────────────
# 4. Curly-brace tags  {breath}, ...
# ──────────────────────────────────────────────
_RE_BRACE = re.compile(r"\{[^}]*\}")

# ──────────────────────────────────────────────
# 5. Filler-word marker  # word
#    Match # followed by optional space and a word
#    Examples: "# أأأ"  "# eh,"  "# อ่า"
#    Note: to avoid deleting whole Chinese sentences (Chinese has no spaces),
#    full filler-word removal is disabled here; only the # symbol itself is removed.
# ──────────────────────────────────────────────
_RE_FILLER = re.compile(r"#\s*")

# ──────────────────────────────────────────────
# 6. Collapse extra whitespace
# ──────────────────────────────────────────────
_RE_MULTI_SPACE = re.compile(r"\s+")


def remove_paralinguistic_tags(text: str) -> str:
    """
    Remove all paralinguistic tags and filler-word annotations; return the cleaned text.

    Processing order:
      1. [...]  square-bracket tags
      2. <...>  angle-bracket tags
      3. (...)  parenthesis tags (short content only)
      4. （...）full-width parenthesis tags (short content only)
      5. {...}  curly-brace tags
      6. # word filler words
      7. collapse extra whitespace
    """
    text = _RE_SQUARE.sub("", text)
    text = _RE_ANGLE.sub("", text)
    text = _RE_PAREN.sub("", text)
    text = _RE_PAREN_CN.sub("", text)
    text = _RE_BRACE.sub("", text)
    text = _RE_FILLER.sub("", text)
    text = _RE_MULTI_SPACE.sub(" ", text).strip()
    return text
