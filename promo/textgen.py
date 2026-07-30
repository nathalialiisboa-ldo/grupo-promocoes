from pathlib import Path

import yaml

from .categorize import detect_kit_quantity

TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "data" / "templates.yaml"


def _load_templates():
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _format_price_simple(value: float) -> str:
    """19.9 -> '19,90' (formato brasileiro)."""
    return f"{value:.2f}".replace(".", ",")


def build_price_line(original_price, promo_price) -> str:
    if original_price and original_price > promo_price:
        pct = round((1 - (promo_price / original_price)) * 100)
        return (
            f"de R$ {_format_price_simple(original_price)} por "
            f"R$ {_format_price_simple(promo_price)} ({pct}% OFF)"
        )
    return f"por apenas R$ {_format_price_simple(promo_price)}"


def build_kit_line(name: str, promo_price: float, unidade_label: str) -> str:
    qty = detect_kit_quantity(name)
    if not qty:
        return ""
    unit_price = promo_price / qty
    return f"💰 Sai por R$ {_format_price_simple(unit_price)} cada {unidade_label}!"


def build_display_name(name: str, brand: str) -> str:
    """Inclui a marca no nome exibido, exceto se ela já aparecer no nome
    (ex: nome já é "Secador Philips Modelo X")."""
    if brand and brand.lower() not in (name or "").lower():
        return f"{name} ({brand})"
    return name


def _pick_variant(variants: list, product_id) -> dict:
    """Escolhe uma variação de texto de forma estável para o mesmo produto,
    mas variando entre produtos diferentes (evita textos idênticos quando
    vários produtos parecidos aparecem seguidos)."""
    index = (product_id or 0) % len(variants)
    return variants[index]


def generate_text(product) -> str:
    """product: dict-like (sqlite3.Row funciona) com as colunas da tabela products."""
    templates = _load_templates()
    category = product["category"]
    config = templates.get(category) or templates["Fora do escopo"]
    variant = _pick_variant(config["variants"], product["id"])

    name = build_display_name(product["name"], product["brand"] if "brand" in product.keys() else None)
    original_price = product["original_price"]
    promo_price = product["promo_price"]
    link = product["link"]
    coupon = product["coupon"]
    extra_details = product["extra_details"]

    preco_linha = build_price_line(original_price, promo_price)
    kit_linha = build_kit_line(product["name"], promo_price, config.get("unidade_kit", "unidade"))

    lines = [
        variant["intro"],
        f"{name}, {preco_linha}",
    ]
    if kit_linha:
        lines.append(kit_linha)
    lines.append(variant["urgencia"])
    if coupon:
        lines.append(f"🎟️ Use o cupom {coupon} no checkout")
    if extra_details:
        lines.append(extra_details)
    lines.append(f"👉 {link}")

    return "\n".join(lines)
