import csv
import io
import re
import unicodedata

from .categorize import categorize_product

# Aliases de cabeçalho (normalizados: sem acento, minúsculo) reconhecidos para
# cada campo lógico. Adicione variações aqui se uma nova plataforma usar
# nomes de coluna diferentes.
NAME_ALIASES = ["item name", "nome do produto", "product name", "titulo", "nome", "produto"]
PROMO_PRICE_ALIASES = ["price", "preco", "preco promocional", "preco atual", "valor", "sale price"]
ORIGINAL_PRICE_ALIASES = ["original price", "preco original", "preco antes", "preco de", "preco cheio"]
COMMISSION_RATE_ALIASES = ["commission rate", "taxa de comissao", "comissao (%)", "% comissao"]
COMMISSION_ALIASES = ["commission", "comissao", "valor da comissao", "valor comissao"]
STORE_NAME_ALIASES = ["nome da loja", "loja", "store name", "seller", "vendedor"]

# Link: prioriza o link de oferta (já com tag de afiliada); cai para o link
# de produto simples se não houver.
OFFER_LINK_ALIASES = ["offer link", "link de oferta", "affiliate link", "link de afiliado"]
PRODUCT_LINK_ALIASES = ["product link", "link do produto", "link"]


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize_header(text: str) -> str:
    text = _strip_accents(text or "").lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _find_value(row_by_normalized_header: dict, aliases: list):
    for alias in aliases:
        if alias in row_by_normalized_header:
            value = row_by_normalized_header[alias]
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    return None


def parse_price(raw_value):
    """Converte strings de preço em vários formatos (R$ 19,90 / 19.90 / 1.234,56) em float."""
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if text == "":
        return None

    text = re.sub(r"[^\d.,]", "", text)
    if text == "":
        return None

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # vírgula é o separador decimal, ponto é milhar
            text = text.replace(".", "").replace(",", ".")
        else:
            # ponto é o separador decimal, vírgula é milhar
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def parse_csv(file_stream, platform: str):
    """Lê um CSV de produtos (bytes/texto) e retorna uma lista de dicts prontos
    para inserir na tabela products (categoria já calculada).

    Colunas obrigatórias reconhecidas: nome do produto, preço e um link.
    Linhas sem nome, preço ou link válidos são ignoradas.
    """
    text = file_stream.read()
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    products = []

    for row in reader:
        if not row:
            continue
        row_by_normalized_header = {
            _normalize_header(k): v for k, v in row.items() if k is not None
        }

        name = _find_value(row_by_normalized_header, NAME_ALIASES)
        promo_price_raw = _find_value(row_by_normalized_header, PROMO_PRICE_ALIASES)
        link = _find_value(row_by_normalized_header, OFFER_LINK_ALIASES) or _find_value(
            row_by_normalized_header, PRODUCT_LINK_ALIASES
        )

        promo_price = parse_price(promo_price_raw)

        if not name or promo_price is None or not link:
            continue

        original_price = parse_price(_find_value(row_by_normalized_header, ORIGINAL_PRICE_ALIASES))
        commission_rate = _find_value(row_by_normalized_header, COMMISSION_RATE_ALIASES)
        commission = _find_value(row_by_normalized_header, COMMISSION_ALIASES)
        store_name = _find_value(row_by_normalized_header, STORE_NAME_ALIASES)

        products.append(
            {
                "name": name,
                "category": categorize_product(name),
                "platform": platform,
                "store_name": store_name,
                "original_price": original_price,
                "promo_price": promo_price,
                "commission_rate": commission_rate,
                "commission": commission,
                "link": link,
                "coupon": None,
                "extra_details": None,
                "status": "pendente",
            }
        )

    return products
