# Grupo Promoções

App local para organizar produtos em promoção (Shopee, Mercado Livre, Amazon,
Magalu, Shein) e gerar textos de divulgação prontos para colar em grupos de
WhatsApp. O envio em si continua manual: você copia o texto e cola onde
quiser.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

Abra http://127.0.0.1:5000 no navegador.

Os dados ficam salvos em `data/app.db` (SQLite), na sua máquina. Nada é
enviado para a nuvem.

## Como usar

1. **Importar CSV**: menu "Importar CSV" → escolha a plataforma → envie o
   arquivo exportado pelo programa de afiliados. O parser reconhece variações
   comuns de nome de coluna (preço, nome do produto, link etc.) e usa sempre
   o link de oferta (`Offer Link`) quando disponível, pois já vem com a tag
   de afiliada.
2. **Cadastro manual**: menu "+ Cadastrar produto" para um produto avulso.
3. Cada produto importado é **categorizado automaticamente** pelo nome
   (Roupas, Calçados, Beleza e cosméticos, Eletrônicos de beleza, Casa e
   acessórios). O que não se encaixa vira "Fora do escopo" — fica visível na
   lista para você decidir manualmente, nunca é descartado.
4. Você pode **trocar a categoria** de qualquer produto direto na lista, o
   que atualiza o texto gerado imediatamente.
5. Cada card mostra o **texto pronto pra copiar** (botão "Copiar texto") e um
   botão para marcar como **enviado/pendente**.
6. Filtros por categoria e por status ficam no topo da lista de produtos.

## Ajustando os textos e a categorização sem mexer em código

- `data/templates.yaml`: o início e a linha de urgência de cada categoria.
  Edite à vontade para ajustar o tom.
- `data/categories.yaml`: as palavras-chave usadas para categorizar produtos
  automaticamente. Adicione ou remova termos livremente.

## Regras de geração de texto

- Preço: se houver preço original E promocional, usa
  `de R$ X por R$ Y (Z% OFF)` com o desconto calculado automaticamente. Se só
  houver um preço (caso comum em exports de afiliado), usa `por apenas R$ X`.
- Kit/múltiplas unidades: se o nome indicar mais de uma unidade do mesmo item
  (ex.: "kit com 3", "2x100g", "5 unidades"), calcula o preço por unidade e
  adiciona uma linha extra.
- Cupom: se cadastrado, adiciona uma linha com o cupom antes do link.
- Detalhes extras: se preenchidos, adiciona uma linha antes do link.
- Nunca usa travessão (—); emojis com moderação (1-2 por texto).

## O que este app não faz

- Não faz scraping de Shopee, Amazon, Mercado Livre, Shein ou Magalu — a
  entrada de produtos é sempre via CSV exportado por você ou cadastro manual.
- Não envia mensagens para WhatsApp automaticamente — o envio final é manual.
- Não depende de nenhuma API externa paga.
