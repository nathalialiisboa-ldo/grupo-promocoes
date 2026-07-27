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


def generate_text(product) -> str:
    """product: dict-like (sqlite3.Row funciona) com as colunas da tabela products."""
    templates = _load_templates()
    category = product["category"]
    template = templates.get(category, templates["Fora do escopo"])

    name = product["name"]
    original_price = product["original_price"]
    promo_price = product["promo_price"]
    link = product["link"]
    coupon = product["coupon"]
    extra_details = product["extra_details"]

    preco_linha = build_price_line(original_price, promo_price)
    kit_linha = build_kit_line(name, promo_price, template.get("unidade_kit", "unidade"))

    lines = [
        template["intro"],
        f"{name}, {preco_linha}",
    ]
    if kit_linha:
        lines.append(kit_linha)
    lines.append(template["urgencia"])
    if coupon:
        lines.append(f"🎟️ Use o cupom {coupon} no checkout")
    if extra_details:
        lines.append(extra_details)
    lines.append(f"👉 {link}")

    return "\n".join(lines)
