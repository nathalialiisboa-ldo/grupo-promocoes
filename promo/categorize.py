import re
import unicodedata
from pathlib import Path

import yaml

CATEGORIES_PATH = Path(__file__).resolve().parent.parent / "data" / "categories.yaml"


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    return _strip_accents(text or "").lower().strip()


def _load_config():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_all_categories():
    """Return the full list of categories in display order, including the fallback."""
    config = _load_config()
    return list(config["order"]) + [config["fora_do_escopo"]]


def categorize_product(name: str) -> str:
    config = _load_config()
    normalized_name = _normalize(name)

    for category in config["order"]:
        keywords = config["keywords"].get(category, [])
        for keyword in keywords:
            if _normalize(keyword) in normalized_name:
                return category

    return config["fora_do_escopo"]


# --- Detecção de kit (mais de uma unidade do mesmo item) ---

_KIT_QTY_PATTERNS = [
    re.compile(r"\bkit\s*(?:com)?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*(?:unidades|unid\.?|un\.?)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*x\s*\d+\s*(?:ml|g|kg|l)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*pe(?:c|ç)as\b", re.IGNORECASE),
    re.compile(r"\bcombo\s*(?:com)?\s*(\d+)\b", re.IGNORECASE),
    re.compile(r"\bpack\s*(?:com)?\s*(\d+)\b", re.IGNORECASE),
]


def detect_kit_quantity(name: str):
    """Try to find how many units of the same item the product name implies.

    Returns an int >= 2 when confident, otherwise None.
    """
    if not name:
        return None
    for pattern in _KIT_QTY_PATTERNS:
        match = pattern.search(name)
        if match:
            qty = int(match.group(1))
            if qty >= 2:
                return qty
    return None
