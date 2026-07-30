import logging
import os
import time
from pathlib import Path

import yaml

from . import db
from .brand_detect import detect_brand
from .categorize import categorize_product
from .shopee_client import (
    ShopeeAPIError,
    generate_short_link,
    search_product_offers,
    search_shop_offers,
)
from .text_utils import clean_repeated_phrases, format_currency_2_decimals

CATEGORIES_PATH = Path(__file__).resolve().parent.parent / "data" / "categories.yaml"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "shopee_sync.log"

DEFAULT_RATE_LIMIT_SECONDS = 2
DEFAULT_RESULTS_PER_CATEGORY = 5
DEFAULT_FETCH_BATCH_SIZE = 30
DEFAULT_MIN_RATING = 4.5
DEFAULT_MIN_SALES = 20

# Tipos de loja considerados confiáveis (ver campo `shopType` da
# documentação da Shopee): loja oficial, vendedor preferencial, e
# preferencial plus.
TRUSTED_SHOP_TYPES = {1, 2, 4}

logger = logging.getLogger("shopee_sync")
logger.setLevel(logging.INFO)
if not logger.handlers:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())


def _load_search_terms() -> dict:
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    return config.get("shopee_search_terms", {})


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("false", "0", "nao", "não")


def _passes_quality_filter(node: dict, min_rating: float, min_sales: int, require_trusted_shop: bool) -> bool:
    """Filtro de qualidade aplicado antes de importar uma oferta: exige foto,
    nota mínima e vendas mínimas, e (por padrão) loja oficial/preferencial -
    tudo configurável no .env. O objetivo é evitar anúncios de baixa
    qualidade (sem foto, sem avaliação, lojas novas sem histórico)."""
    if not node.get("imageUrl"):
        return False

    rating = node.get("ratingStar")
    try:
        if rating is None or float(rating) < min_rating:
            return False
    except (TypeError, ValueError):
        return False

    sales = node.get("sales")
    if sales is None or sales < min_sales:
        return False

    if require_trusted_shop:
        shop_types = set(node.get("shopType") or [])
        if not shop_types & TRUSTED_SHOP_TYPES:
            return False

    return True


def _format_commission_rate(raw_rate) -> str:
    """A Shopee devolve a taxa de comissão como fração (ex: "0.25" = 25%),
    conforme a documentação oficial (campo `commissionRate` da
    ProductOfferV2). Converte para uma porcentagem legível."""
    if raw_rate is None:
        return None
    try:
        percentage = float(raw_rate) * 100
    except (TypeError, ValueError):
        return str(raw_rate)
    if percentage == int(percentage):
        return f"{int(percentage)}%"
    return f"{percentage:.2f}%".replace(".", ",")


def _map_node_to_product(node: dict) -> dict:
    name = clean_repeated_phrases(node.get("productName") or "")
    price = node.get("priceMin")
    if price is None:
        price = node.get("priceMax")

    link = node.get("offerLink")
    if not link and node.get("productLink"):
        try:
            link = generate_short_link(node["productLink"])
        except ShopeeAPIError as exc:
            logger.warning("Falha ao gerar link curto para '%s': %s", name, exc)
            link = node.get("productLink")

    commission_rate = _format_commission_rate(node.get("commissionRate"))

    return {
        "external_id": str(node["itemId"]) if node.get("itemId") is not None else None,
        "name": name,
        "category": categorize_product(name),
        "platform": "Shopee",
        "store_name": node.get("shopName"),
        "shop_id": node.get("shopId"),
        "original_price": None,
        "promo_price": float(price) if price is not None else None,
        "commission_rate": commission_rate,
        "commission": format_currency_2_decimals(node.get("commission")),
        "link": link,
        "coupon": None,
        "extra_details": None,
        "status": "pendente",
        "brand": detect_brand(name),
        "image_url": node.get("imageUrl"),
    }


def _import_nodes(nodes: list, summary: dict) -> None:
    for node in nodes:
        product = _map_node_to_product(node)
        if not product["name"] or product["promo_price"] is None or not product["link"]:
            continue

        summary["encontrados"] += 1
        is_new = db.upsert_shopee_product(product)
        if is_new:
            summary["novos"] += 1
        else:
            summary["atualizados"] += 1


def run_sync(rate_limit_seconds: int = None, results_per_category: int = None) -> dict:
    """Busca ofertas na Shopee, uma busca por categoria (via termos em
    data/categories.yaml), e insere/atualiza os produtos no banco local.

    Busca um lote maior de candidatos por chamada (SHOPEE_FETCH_BATCH_SIZE)
    e filtra por qualidade (foto, nota mínima, vendas mínimas e, por padrão,
    loja oficial/preferencial) antes de manter só as `results_per_category`
    melhores ofertas de cada busca.

    Produtos já existentes (mesmo `external_id`) têm preço, comissão e link
    atualizados, mas mantêm a categoria e o status que você já tiver
    ajustado manualmente. Retorna um resumo com contagens e eventuais erros;
    nunca lança exceção para fora (erros de rede/API viram entradas em
    summary["erros"] e ficam registrados em data/shopee_sync.log).
    """
    if rate_limit_seconds is None:
        rate_limit_seconds = int(os.environ.get("SHOPEE_RATE_LIMIT_SECONDS", DEFAULT_RATE_LIMIT_SECONDS))
    if results_per_category is None:
        results_per_category = int(
            os.environ.get("SHOPEE_RESULTS_PER_CATEGORY", DEFAULT_RESULTS_PER_CATEGORY)
        )
    fetch_batch_size = int(os.environ.get("SHOPEE_FETCH_BATCH_SIZE", DEFAULT_FETCH_BATCH_SIZE))
    min_rating = float(os.environ.get("SHOPEE_MIN_RATING", DEFAULT_MIN_RATING))
    min_sales = int(os.environ.get("SHOPEE_MIN_SALES", DEFAULT_MIN_SALES))
    require_trusted_shop = _env_bool("SHOPEE_REQUIRE_TRUSTED_SHOP", True)

    def _good_offers(nodes: list) -> list:
        good = [
            node for node in nodes
            if _passes_quality_filter(node, min_rating, min_sales, require_trusted_shop)
        ]
        return good[:results_per_category]

    search_terms = _load_search_terms()
    summary = {"encontrados": 0, "novos": 0, "atualizados": 0, "erros": []}

    logger.info("Iniciando sincronização com a Shopee Affiliate Open API")

    for category, terms in search_terms.items():
        for term in terms:
            try:
                nodes = search_product_offers(term, limit=fetch_batch_size)
            except ShopeeAPIError as exc:
                msg = f'Categoria "{category}" (termo "{term}"): {exc}'
                logger.error(msg)
                summary["erros"].append(msg)
                time.sleep(rate_limit_seconds)
                continue

            good_nodes = _good_offers(nodes)
            _import_nodes(good_nodes, summary)

            logger.info(
                'Categoria "%s", termo "%s": %d de %d oferta(s) passaram no filtro de qualidade',
                category, term, len(good_nodes), len(nodes),
            )
            time.sleep(rate_limit_seconds)

    for shop_id in db.get_liked_shopee_shop_ids():
        try:
            nodes = search_shop_offers(int(shop_id), limit=fetch_batch_size)
        except ShopeeAPIError as exc:
            msg = f'Loja preferida (shop_id {shop_id}): {exc}'
            logger.error(msg)
            summary["erros"].append(msg)
            time.sleep(rate_limit_seconds)
            continue

        good_nodes = _good_offers(nodes)
        _import_nodes(good_nodes, summary)

        logger.info(
            "Loja preferida (shop_id %s): %d de %d oferta(s) passaram no filtro de qualidade",
            shop_id, len(good_nodes), len(nodes),
        )
        time.sleep(rate_limit_seconds)

    logger.info(
        "Sincronização concluída: %d encontrados, %d novos, %d atualizados, %d erro(s)",
        summary["encontrados"], summary["novos"], summary["atualizados"], len(summary["erros"]),
    )
    return summary
