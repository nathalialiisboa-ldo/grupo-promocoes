import hashlib
import json
import os
import time

import requests

DEFAULT_API_URL = "https://open-api.affiliate.shopee.com.br/graphql"

# Query "productOfferV2": busca ofertas de produtos por palavra-chave na
# Shopee Affiliate Open API. Se a documentação que a Shopee te passou usar
# nomes de campo diferentes destes, ajuste a query e o mapeamento em
# `promo/shopee_sync.py` (_map_node_to_product) - são os dois únicos lugares
# que conhecem o formato da resposta.
PRODUCT_OFFER_QUERY = """
query ProductOffer($keyword: String, $page: Int, $limit: Int) {
  productOfferV2(keyword: $keyword, page: $page, limit: $limit) {
    nodes {
      itemId
      productName
      priceMin
      priceMax
      commissionRate
      commission
      sales
      productLink
      offerLink
      shopName
    }
    pageInfo {
      page
      limit
      hasNextPage
    }
  }
}
"""

# Mutation usada como reserva para gerar um link curto de afiliada quando a
# busca de ofertas não devolve um `offerLink` pronto.
GENERATE_SHORT_LINK_MUTATION = """
mutation GenerateShortLink($originUrl: String!) {
  generateShortLink(originUrl: $originUrl) {
    shortLink
  }
}
"""


class ShopeeAPIError(Exception):
    pass


def _sign_request(app_id: str, secret: str, payload: str, timestamp: int) -> str:
    """Assinatura da Shopee Affiliate Open API.

    Segue o formato documentado pela Shopee: SHA256 do texto
    "{AppId}{Timestamp}{Payload}{Secret}" concatenado, sem separadores. Se a
    documentação que você recebeu da Shopee mostrar uma fórmula diferente
    (por exemplo, um HMAC "de verdade" usando a lib `hmac` do Python com o
    Secret como chave), esta é a única função que precisa mudar - o resto do
    código não depende de como a assinatura é calculada.
    """
    raw = f"{app_id}{timestamp}{payload}{secret}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _request(query: str, variables: dict) -> dict:
    app_id = os.environ.get("SHOPEE_APP_ID")
    secret = os.environ.get("SHOPEE_APP_SECRET")
    api_url = os.environ.get("SHOPEE_API_URL", DEFAULT_API_URL)

    if not app_id or not secret:
        raise ShopeeAPIError(
            "SHOPEE_APP_ID / SHOPEE_APP_SECRET não configurados. "
            "Copie .env.example para .env e preencha suas credenciais."
        )

    body = {"query": query, "variables": variables}
    payload = json.dumps(body, separators=(",", ":"))
    timestamp = int(time.time())
    signature = _sign_request(app_id, secret, payload, timestamp)

    headers = {
        "Content-Type": "application/json",
        "Authorization": (
            f"SHA256 Credential={app_id}, Timestamp={timestamp}, Signature={signature}"
        ),
    }

    try:
        response = requests.post(api_url, data=payload, headers=headers, timeout=20)
    except requests.RequestException as exc:
        raise ShopeeAPIError(f"Falha de conexão com a API da Shopee: {exc}") from exc

    if response.status_code == 429:
        raise ShopeeAPIError("Limite de taxa (rate limit) da API da Shopee atingido.")

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise ShopeeAPIError(f"Erro HTTP {response.status_code} da API da Shopee: {exc}") from exc

    data = response.json()
    if data.get("errors"):
        raise ShopeeAPIError(str(data["errors"]))

    return data.get("data", {})


def search_product_offers(keyword: str, limit: int = 20, page: int = 1) -> list:
    """Busca ofertas de produtos por palavra-chave.

    Retorna uma lista de dicts no formato bruto devolvido pela API (nodes).
    """
    data = _request(PRODUCT_OFFER_QUERY, {"keyword": keyword, "page": page, "limit": limit})
    return data.get("productOfferV2", {}).get("nodes", []) or []


def generate_short_link(origin_url: str) -> str:
    """Gera um link curto de afiliada para uma URL de produto.

    Usado como reserva caso a busca de ofertas não tenha devolvido um
    `offerLink` pronto para o item.
    """
    data = _request(GENERATE_SHORT_LINK_MUTATION, {"originUrl": origin_url})
    return data.get("generateShortLink", {}).get("shortLink") or origin_url
