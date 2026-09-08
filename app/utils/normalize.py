import re
import unicodedata

# Apostrophes are dropped outright (Domino's -> dominos) rather than turned
# into a space like other punctuation, so they match the un-punctuated spelling.
_APOSTROPHE_RE = re.compile(r"['‘’`]")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Lowercase, strip accents/punctuation and collapse whitespace so that
    minor spelling variations ("Domino's" / "Dominos" / "Domino's") map to
    the same key.
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = _APOSTROPHE_RE.sub("", text)
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)
    return text.strip()
