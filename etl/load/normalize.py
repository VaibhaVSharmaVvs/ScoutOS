"""Name normalization for cross-source matching (stdlib only).

Strips accents, lowercases, drops punctuation, collapses whitespace. Used to
build the join key for entity resolution (FBref/Understat/Transfermarkt player
and club names all differ in diacritics/punctuation).
"""

from __future__ import annotations

import re
import unicodedata

_PUNCT = re.compile(r"[^a-z0-9\s]")
_WS = re.compile(r"\s+")

# Letters NFKD can't decompose to ASCII (not base+combining-mark). Common in
# Scandinavian/Polish/etc. player names — without this they'd be stripped as
# punctuation (e.g. "Højbjerg" -> "h jbjerg"), hurting exact matches.
_SPECIAL = str.maketrans({
    "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe",
    "ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ð": "d", "Ð": "d",
    "þ": "th", "Þ": "th", "ß": "ss", "ı": "i", "İ": "i",
})


def strip_accents(text: str) -> str:
    text = text.translate(_SPECIAL)
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(text: str | None) -> str:
    if not text:
        return ""
    text = strip_accents(str(text)).lower()
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()
