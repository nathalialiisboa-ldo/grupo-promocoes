import hashlib
import json
import os
import time

import requests

DEFAULT_API_URL = "https://open-api.affiliate.shopee.com.br/graphql"

# Query "productOfferV2": busca ofertas de produtos por palavra-chave na
# Shopee Affiliate Open API (confirmado com a documentação oficial em
# affiliate.shopee.com.br/open_api/home -> "Get Product Offer List").
# `sortType: 1` = RELEVANCE_DESC, que a própria documentação diz ser
# obrigatório para a busca por palavra-chave realmente ordenar pela
# relevância com o termo buscado - sem isso a API pode devolver produtos
# sem relação nenhuma com a palavra-chave.
PRODUCT_OFFER_QUERY = """
query ProductOffer($keyword: String, $sortType: Int, $isKeySeller: Boolean, $page: Int, $limit: Int) {
  productOfferV2(keyword: $keyword, sortType: $sortType, isKeySeller: $isKeySeller, page: $page, limit: $limit) {
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
      shopId
      shopName
      shopType
      imageUrl
      ratingStar
    }
    pageInfo {
      page
      limit
      hasNextPage
    }
  }
}
"""

# Busca ofertas de uma loja específica (usada para trazer mais produtos de
# lojas que já renderam bons exemplos, via listType=DETAIL_SHOP + matchId).
# A documentação diz que listType/matchId não podem ser usados junto com
# keyword/sortType, por isso é uma query separada.
SHOP_OFFER_QUERY = """
query ShopOffer($listType: Int, $matchId: Int64, $page: Int, $limit: Int) {
  productOfferV2(listType: $listType, matchId: $matchId, page: $page, limit: $limit) {
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
      shopId
      shopName
      shopType
      imageUrl
      ratingStar
    }
    pageInfo {
      page
      limit
      hasNextPage
    }
  }
}
"""

SORT_RELEVANCE_DESC = 1
LIST_TYPE_DETAIL_SHOP = 5

# Mutation usada como reserva para gerar um link curto de afiliada quando a
# busca de ofertas não devolve um `offerLink` pronto (raro, já que
# productOfferV2 devolve offerLink diretamente). Diferente da query acima,
# o nome e o formato exatos desta mutation ainda não foram confirmados na
# documentação "Get Short Link" da Shopee - se ela falhar, o link do
# produto (sem tag de afiliada) é usado como reserva e o erro fica
# registrado no log, sem travar a sincronização.
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


def _key_seller_only() -> bool:
    return os.environ.get("SHOPEE_KEY_SELLER_ONLY", "true").strip().lower() not in (
        "false", "0", "nao", "não",
    )


def search_product_offers(keyword: str, limit: int = 20, page: int = 1) -> list:
    """Busca ofertas de produtos por palavra-chave, ordenadas por relevância
    com o termo buscado. Por padrão, filtra só vendedores "key seller" da
    Shopee (mais confiáveis) - desative com SHOPEE_KEY_SELLER_ONLY=false no
    .env se isso estiver deixando de fora ofertas boas.

    Retorna uma lista de dicts no formato bruto devolvido pela API (nodes).
    """
    variables = {"keyword": keyword, "sortType": SORT_RELEVANCE_DESC, "page": page, "limit": limit}
    if _key_seller_only():
        variables["isKeySeller"] = True
    data = _request(PRODUCT_OFFER_QUERY, variables)
    return data.get("productOfferV2", {}).get("nodes", []) or []


def search_shop_offers(shop_id: int, limit: int = 20, page: int = 1) -> list:
    """Busca ofertas de produtos de uma loja específica (usado para trazer
    mais produtos de lojas que você já marcou como bom exemplo).

    Retorna uma lista de dicts no formato bruto devolvido pela API (nodes).
    """
    data = _request(
        SHOP_OFFER_QUERY,
        {"listType": LIST_TYPE_DETAIL_SHOP, "matchId": shop_id, "page": page, "limit": limit},
    )
    return data.get("productOfferV2", {}).get("nodes", []) or []


def generate_short_link(origin_url: str) -> str:
    """Gera um link curto de afiliada para uma URL de produto.

    Usado como reserva caso a busca de ofertas não tenha devolvido um
    `offerLink` pronto para o item.
    """
    data = _request(GENERATE_SHORT_LINK_MUTATION, {"originUrl": origin_url})
    return data.get("generateShortLink", {}).get("shortLink") or origin_url
