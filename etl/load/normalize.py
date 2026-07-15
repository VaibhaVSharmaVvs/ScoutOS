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


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(text: str | None) -> str:
    if not text:
        return ""
    text = strip_accents(str(text)).lower()
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()
