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

1. **Shopee via API**: clique em "🔄 Buscar ofertas Shopee agora" (ou deixe a
   busca agendada rodar sozinha, veja a seção abaixo) para trazer ofertas
   automaticamente, já com o link de afiliada gerado.
2. **Importar CSV**: menu "Importar CSV" → escolha a plataforma → envie o
   arquivo exportado pelo programa de afiliados (Mercado Livre, Amazon,
   Magalu, Shein, ou Shopee sem API). O parser reconhece variações comuns de
   nome de coluna (preço, nome do produto, link etc.) e usa sempre o link de
   oferta (`Offer Link`) quando disponível, pois já vem com a tag de
   afiliada.
3. **Cadastro manual**: menu "+ Cadastrar produto" para um produto avulso.
4. Cada produto (de qualquer uma das três origens) é **categorizado
   automaticamente** pelo nome (Roupas, Calçados, Beleza e cosméticos,
   Eletrônicos de beleza, Casa e acessórios). O que não se encaixa vira "Fora
   do escopo" — fica visível na lista para você decidir manualmente, nunca é
   descartado.
5. Você pode **trocar a categoria** de qualquer produto direto na lista, o
   que atualiza o texto gerado imediatamente.
6. Cada card mostra o **texto pronto pra copiar** (botão "Copiar texto") e um
   botão para marcar como **enviado/pendente**.
7. Filtros por categoria e por status ficam no topo da lista de produtos.

## Configurando a API da Shopee (opcional, mas recomendado)

1. Copie o arquivo `.env.example` e renomeie a cópia para `.env` (sem
   ".example" no final).
2. Abra o `.env` com o Bloco de Notas e preencha `SHOPEE_APP_ID` e
   `SHOPEE_APP_SECRET` com as credenciais que a Shopee te deu para a
   Affiliate Open API.
3. **O arquivo `.env` nunca deve ir para o GitHub** — ele já está listado no
   `.gitignore` desde o primeiro commit deste projeto, então um `git add .`
   normal não vai incluí-lo. Ainda assim, antes de qualquer `git push`,
   confira com `git status` que `.env` não aparece na lista de arquivos a
   enviar.
4. Sem esse arquivo preenchido, o botão "Buscar ofertas Shopee agora" e o
   agendamento simplesmente registram um erro claro (no rodapé da tela e em
   `data/shopee_sync.log`) e não quebram o resto do app.

A busca faz **uma chamada à API por termo de pesquisa** (um termo por
categoria, configurável em `data/categories.yaml` na chave
`shopee_search_terms`), com uma pausa entre chamadas (`SHOPEE_RATE_LIMIT_SECONDS`
no `.env`, padrão 2 segundos) para respeitar o limite de taxa da Shopee.
Produtos já importados antes (mesmo item da Shopee) têm preço, comissão e
link atualizados numa nova busca, mas a categoria e o status (pendente/
enviado) que você já tiver ajustado manualmente **não são sobrescritos**.

## Agendamento automático da busca na Shopee (Windows)

Como a Shopee autoriza oficialmente essas chamadas (diferente de scraping),
você pode deixar o Agendador de Tarefas do Windows rodar a busca sozinho,
2x ao dia, sem precisar abrir o app:

1. Confirme que o `.env` já está configurado (seção acima) e que
   `python app.py` funciona manualmente pelo menos uma vez.
2. Abra o **Agendador de Tarefas** do Windows (pesquise "Agendador de
   Tarefas" no menu Iniciar).
3. Clique em **"Criar Tarefa Básica..."** no painel da direita.
4. Dê um nome, tipo "Buscar ofertas Shopee".
5. Em "Gatilho", escolha **"Diariamente"** e defina um horário (ex.: 9h).
   Depois de criar, edite a tarefa e adicione um segundo horário no mesmo dia
   (ex.: 18h) na aba "Disparadores" → "Novo..." para rodar 2x ao dia.
6. Em "Ação", escolha **"Iniciar um programa"** e aponte para o arquivo
   `sincronizar_shopee.bat` que vem junto com este projeto (clique em
   "Procurar..." e selecione o arquivo na pasta do app).
7. Finalize e feche o assistente.

Essa tarefa só atualiza os produtos no banco de dados (não abre o navegador
nem precisa do app aberto). Você pode conferir se rodou olhando o arquivo
`data/shopee_sync.log` (ou rodando `python fetch_shopee.py` manualmente a
qualquer momento para testar).

## Ajustando os textos e a categorização sem mexer em código

- `data/templates.yaml`: o início e a linha de urgência de cada categoria.
  Edite à vontade para ajustar o tom.
- `data/categories.yaml`: as palavras-chave usadas para categorizar produtos
  automaticamente, e os termos de busca usados na API da Shopee
  (`shopee_search_terms`). Adicione ou remova termos livremente.

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

- Não faz scraping de Amazon, Mercado Livre, Shein ou Magalu — para essas
  quatro, a entrada de produtos é sempre via CSV exportado por você ou
  cadastro manual. Só a Shopee usa API direta, por já ter dado acesso
  oficial à Affiliate Open API.
- Não envia mensagens para WhatsApp por nenhum meio, oficial ou não, e não
  cria grupos automaticamente — o envio final é sempre manual, feito por
  você copiando o texto gerado.
- Não depende de nenhuma outra API externa paga.
