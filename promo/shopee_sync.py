import logging
import os
import time
from pathlib import Path

import yaml

from . import db
from .categorize import categorize_product
from .shopee_client import ShopeeAPIError, generate_short_link, search_product_offers

CATEGORIES_PATH = Path(__file__).resolve().parent.parent / "data" / "categories.yaml"
LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "shopee_sync.log"

DEFAULT_RATE_LIMIT_SECONDS = 2
DEFAULT_RESULTS_PER_CATEGORY = 20

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
    name = node.get("productName") or ""
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
        "original_price": None,
        "promo_price": float(price) if price is not None else None,
        "commission_rate": commission_rate,
        "commission": node.get("commission"),
        "link": link,
        "coupon": None,
        "extra_details": None,
        "status": "pendente",
    }


def run_sync(rate_limit_seconds: int = None, results_per_category: int = None) -> dict:
    """Busca ofertas na Shopee, uma busca por categoria (via termos em
    data/categories.yaml), e insere/atualiza os produtos no banco local.

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

    search_terms = _load_search_terms()
    summary = {"encontrados": 0, "novos": 0, "atualizados": 0, "erros": []}

    logger.info("Iniciando sincronização com a Shopee Affiliate Open API")

    for category, terms in search_terms.items():
        for term in terms:
            try:
                nodes = search_product_offers(term, limit=results_per_category)
            except ShopeeAPIError as exc:
                msg = f'Categoria "{category}" (termo "{term}"): {exc}'
                logger.error(msg)
                summary["erros"].append(msg)
                time.sleep(rate_limit_seconds)
                continue

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

            logger.info(
                'Categoria "%s", termo "%s": %d oferta(s) processada(s)',
                category, term, len(nodes),
            )
            time.sleep(rate_limit_seconds)

    logger.info(
        "Sincronização concluída: %d encontrados, %d novos, %d atualizados, %d erro(s)",
        summary["encontrados"], summary["novos"], summary["atualizados"], len(summary["erros"]),
    )
    return summary
