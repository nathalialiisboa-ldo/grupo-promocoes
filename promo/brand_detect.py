from pathlib import Path

import yaml

BRANDS_PATH = Path(__file__).resolve().parent.parent / "data" / "known_brands.yaml"


def _load_brands() -> list:
    with open(BRANDS_PATH, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}
    return config.get("brands", [])


def detect_brand(name: str) -> str:
    """Procura, na lista editável de data/known_brands.yaml, uma marca que
    apareça dentro do nome do produto. Retorna a marca (com a grafia que
    está no arquivo) ou None se nenhuma bater.

    Só reconhece marcas que já estiverem na lista - nunca inventa uma marca
    que não esteja explicitamente cadastrada.
    """
    if not name:
        return None
    normalized_name = name.lower()
    for brand in _load_brands():
        if brand.lower() in normalized_name:
            return brand
    return None
