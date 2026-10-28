"""The one blank-text predicate for analyst text (LEAD round 12 B10).

A text is blank when every character is whitespace (`str.isspace`) or a Unicode format character
(category `Cf`: U+200B, U+FEFF, U+00AD, U+2060 and the like), which `str.strip()` keeps. `""` is
blank, as `not "".strip()` is.
"""

import unicodedata


def is_blank(text: str) -> bool:
    """Whether `text` holds only whitespace and Unicode format (`Cf`) characters."""
    return all(ch.isspace() or unicodedata.category(ch) == "Cf" for ch in text)
