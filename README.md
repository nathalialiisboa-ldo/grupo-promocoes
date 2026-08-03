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

Os dados ficam salvos em `data/app.db` (SQLite). Por padrão o app roda só
na sua máquina, sem depender de nada em nuvem; veja "Hospedando na
internet" mais abaixo se quiser acessá-lo por um link, de qualquer lugar.

Por padrão a tela mostra só o fluxo de CSV/cadastro manual - os botões de
busca automática da Shopee ficam escondidos (ative com
`SHOW_SHOPEE_BUTTONS=true` no `.env` se quiser voltar a usá-los).

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
7. Filtros por categoria, status e "⭐ Só bons exemplos" ficam no topo da
   lista de produtos.
8. Marque um produto vindo da Shopee como **"⭐ Bom exemplo"** quando gostar
   dele: nas próximas sincronizações, o app passa a buscar mais produtos
   direto da mesma loja (usando o parâmetro oficial de busca por loja da
   API), além da busca normal por categoria.

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
no `.env`, padrão 2 segundos) para respeitar o limite de taxa da Shopee, mais
uma chamada extra por loja marcada como "⭐ Bom exemplo" (veja acima).
Produtos já importados antes (mesmo item da Shopee) têm preço, comissão e
link atualizados numa nova busca, mas a categoria e o status (pendente/
enviado) que você já tiver ajustado manualmente **não são sobrescritos**.

Por padrão, a busca por palavra-chave só traz ofertas de vendedores "key
seller" da Shopee (`SHOPEE_KEY_SELLER_ONLY=true` no `.env`), o que tende a
reduzir anúncios de baixa qualidade/spam de palavra-chave no título. Se isso
estiver deixando de fora ofertas boas, troque para `false`.

### Filtro de qualidade

Por padrão, a busca pede um lote maior de candidatos à API
(`SHOPEE_FETCH_BATCH_SIZE`, padrão 30) e mantém só as `SHOPEE_RESULTS_PER_CATEGORY`
melhores (padrão 5) que passarem no filtro de qualidade:

- tem foto (`imageUrl` preenchido);
- nota mínima `SHOPEE_MIN_RATING` (padrão 4,5 de 5);
- vendas mínimas `SHOPEE_MIN_SALES` (padrão 20);
- se `SHOPEE_REQUIRE_TRUSTED_SHOP=true` (padrão), só lojas oficiais ou
  preferenciais da Shopee.

Se estiver vindo pouca coisa ou nada (filtro rígido demais para o seu nicho),
diminua `SHOPEE_MIN_RATING`/`SHOPEE_MIN_SALES` ou troque
`SHOPEE_REQUIRE_TRUSTED_SHOP` para `false` no `.env`. Todas essas opções
ficam documentadas com exemplo no `.env.example`.

Por padrão a busca automática cobre só **Eletrônicos de beleza** e **Beleza
e cosméticos** (as categorias em `shopee_search_terms` no
`data/categories.yaml`) - Roupas, Calçados e Casa e acessórios continuam
funcionando normalmente via CSV ou cadastro manual, só não são buscadas
automaticamente. Adicione categorias de volta nesse arquivo quando quiser.

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

## Hospedando na internet (opcional)

Se quiser acessar o app por um link fixo, de qualquer computador/celular,
em vez de rodar `python app.py` toda vez, dá pra hospedar de graça no
PythonAnywhere. Veja o passo a passo completo na conversa com a Claude, ou
resumidamente:

1. Crie uma conta gratuita em pythonanywhere.com.
2. Configure `APP_PASSWORD` no `.env` de lá (senha de acesso) e
   `APP_SECRET_KEY` (qualquer texto longo aleatório) - sem isso, o app
   fica acessível pra qualquer um que souber o link.
3. Puxe o código do GitHub, instale as dependências, e configure a aba
   "Web" apontando pro `app.py`.
4. Toda vez que o código for atualizado no GitHub, é preciso repetir um
   `git pull` + recarregar o app na aba "Web" do PythonAnywhere (não é
   automático no plano gratuito).

## Ajustando os textos e a categorização sem mexer em código

- `data/templates.yaml`: o início e a linha de urgência de cada categoria.
  Edite à vontade para ajustar o tom.
- `data/categories.yaml`: as palavras-chave usadas para categorizar produtos
  automaticamente, e os termos de busca usados na API da Shopee
  (`shopee_search_terms`). Adicione ou remova termos livremente.
- `data/known_brands.yaml`: lista de marcas usada para tentar reconhecer a
  marca dentro do nome de produtos vindos da Shopee ou CSV (que não têm um
  campo de marca separado). Só reconhece marcas que estiverem nesta lista -
  adicione as marcas que você mais vende.

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
