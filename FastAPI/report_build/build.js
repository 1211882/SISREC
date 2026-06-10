const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, TableOfContents, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageBreak, PageNumber, Header, Footer, VerticalAlign,
} = require("docx");

const ACCENT = "2E75B6";
const CONTENT_WIDTH = 9026; // A4, 1-inch margins

// ── helpers ───────────────────────────────────────────────────────────────
const tr = (text, opts = {}) => new TextRun({ text, ...opts });

const p = (children, opts = {}) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 140, line: 276 },
    children: Array.isArray(children) ? children : [tr(children)],
    ...opts,
  });

const h1 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [tr(text)] });
const h2 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_2, children: [tr(text)] });
const h3 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_3, children: [tr(text)] });

const bullet = (children) =>
  new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 276 },
    alignment: AlignmentType.JUSTIFIED,
    children: Array.isArray(children) ? children : [tr(children)],
  });

const cell = (text, { header = false, width = 0, align = AlignmentType.LEFT } = {}) =>
  new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { fill: ACCENT, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      new Paragraph({
        alignment: align,
        spacing: { after: 0 },
        children: [tr(String(text), { bold: header, color: header ? "FFFFFF" : "000000" })],
      }),
    ],
  });

function table(headers, rows, widths) {
  const border = { style: BorderStyle.SINGLE, size: 1, color: "BFBFBF" };
  const borders = { top: border, bottom: border, left: border, right: border,
    insideHorizontal: border, insideVertical: border };
  const mkRow = (cells, header) =>
    new TableRow({
      tableHeader: header,
      children: cells.map((c, i) =>
        cell(c, { header, width: widths[i], align: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })),
    });
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: widths,
    borders,
    rows: [mkRow(headers, true), ...rows.map((r) => mkRow(r, false))],
  });
}

const spacer = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [tr("")] }));

// ── cover ───────────────────────────────────────────────────────────────
const cover = [
  ...spacer(4),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [tr("Sistemas de Recomendação — 2025/2026", { size: 24, color: "595959" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
    children: [tr("SISREC — Sistema de Recomendação Híbrido", { size: 44, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [tr("Recomendação de restaurantes sobre o Yelp Open Dataset", { size: 26, color: "595959" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 1 } }, children: [tr("")] }),
  ...spacer(6),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [tr("Relatório Final", { size: 30, bold: true, color: ACCENT })] }),
  ...spacer(4),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [tr("Turma: <Turma>      Grupo: <Grupo>", { size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
    children: [tr("Elementos do grupo: <Nome 1>, <Nome 2>, <Nome 3>", { size: 22, color: "595959" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [tr("Junho de 2026", { size: 22, color: "595959" })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── TOC ───────────────────────────────────────────────────────────────────
const toc = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [tr("Índice")] }),
  new TableOfContents("Índice", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

// ── body ────────────────────────────────────────────────────────────────
const body = [];
const S = (...els) => body.push(...els);

// 1. Introdução
S(h1("1. Introdução"));
S(p("Os Sistemas de Recomendação (SR) ajudam os utilizadores a navegar catálogos extensos, sugerindo itens relevantes a partir do seu comportamento e preferências. Este projeto desenvolve um Sistema de Recomendação Híbrido para o domínio da restauração, suportado por uma Web API e por uma aplicação web, usando o Yelp Open Dataset como fonte de dados."));
S(p("O sistema combina três famílias de abordagens — Collaborative/Social Filtering, Content-Based Filtering e conhecimento de perfil — numa estratégia híbrida ponderada (weighted). O objetivo é mitigar as limitações de cada abordagem isolada, em particular o problema do arranque a frio (cold start) de utilizadores e de itens, e melhorar a qualidade das recomendações face a uma única técnica."));
S(p([
  tr("Este relatório descreve o estado da arte, a especificação técnica (dataset, funcionalidades, arquitetura e algoritmos), as estratégias de cold start, e a experimentação que compara a solução híbrida com as abordagens individuais. Inclui ainda análise crítica, conclusões, referências e a declaração de utilização de ferramentas de IA generativa."),
]));

// 2. Estado da arte
S(h1("2. Estado da arte"));
S(p("A literatura de SR organiza-se em três grandes paradigmas. A Filtragem Colaborativa (Collaborative Filtering, CF) recomenda itens com base em padrões de avaliação de utilizadores semelhantes; as variantes baseadas em vizinhança (user-based e item-based KNN) usam medidas de similaridade como o cosseno ou Pearson (Sarwar et al., 2001; Herlocker et al., 1999). A Filtragem Baseada em Conteúdo (Content-Based, CBF) recomenda itens semelhantes aos que o utilizador apreciou, comparando descritores (no domínio da restauração, categorias e atributos). A Recomendação Baseada em Conhecimento usa regras e preferências explícitas, útil quando há poucos dados de interação."));
S(p([
  tr("Burke (2002) sistematiza as estratégias "), tr("híbridas", { italics: true }),
  tr(" em sete tipos: weighted, switching, mixed, feature combination, cascade, feature augmentation e meta-level. A combinação de CF e CBF é a mais comum porque cada técnica cobre as fraquezas da outra: a CF sofre de cold start (itens/utilizadores novos sem avaliações) e de esparsidade, enquanto a CBF tende à sobre-especialização. A abordagem "),
  tr("weighted", { italics: true }),
  tr(" combina as pontuações de vários recomendadores numa soma ponderada, sendo simples de interpretar e de afinar."),
]));
S(p("No domínio específico de restaurantes e reviews, o Yelp Open Dataset é amplamente utilizado em investigação e competições (Kaggle), oferecendo avaliações (stars), texto, categorias, atributos e horários. Trabalhos típicos exploram CF, modelos baseados em conteúdo sobre categorias/atributos, e sinais contextuais (localização, horário de funcionamento) — explorados também neste projeto através de uma componente contextual de período de refeição."));
S(p("A avaliação de SR distingue métricas de erro de predição de rating (RMSE, MAE) de métricas de qualidade de ranking (Precision@K, Recall@K, MAP@K, NDCG@K). A escolha depende do objetivo: prever a nota exata versus ordenar bem os itens relevantes (Herlocker et al., 2004)."));

// 3. Especificação técnica
S(h1("3. Especificação técnica"));

S(h2("3.1. Dataset"));
S(p("O sistema usa um subconjunto do Yelp Open Dataset, complementado por um ficheiro de pessoas sintéticas para enriquecimento demográfico dos perfis. Os volumes são:"));
S(table(
  ["Ficheiro", "Registos", "Descrição"],
  [
    ["business_final.json", "18 806", "Negócios (restaurantes): nome, morada, cidade, estado, coordenadas, stars, review_count, is_open, categorias, atributos, horários"],
    ["review_final.json", "29 243", "Avaliações: user_id, business_id, stars (1–5), texto, útil/funny/cool, data"],
    ["user_final.json", "300", "Utilizadores do dataset: identificação, amigos e estatísticas"],
    ["person_10000.csv", "10 000", "Pessoas sintéticas (nome, género, idade, morada, email) para enriquecer perfis"],
  ],
  [2600, 1300, 5126],
));
S(p([
  tr("As entidades persistidas (PostgreSQL) são: "), tr("businesses", { bold: true }),
  tr(", "), tr("users", { bold: true }), tr(" (utilizador do dataset), "), tr("reviews", { bold: true }),
  tr(", e as tabelas de aplicação "), tr("auth_users", { bold: true }), tr(", "),
  tr("auth_user_dataset_links", { bold: true }), tr(" e "), tr("auth_user_preferences", { bold: true }),
  tr(". As categorias são uma lista textual separada por vírgulas e os atributos/horários são objetos JSON."),
]));

S(h2("3.2. Funcionalidades"));
S(bullet("Recomendações não personalizadas para visitantes não autenticados (página inicial e endpoint público)."));
S(bullet("Registo de utilizadores com inquérito de cold start (categorias preferidas, cidade e faixa de preço); apenas email e password são obrigatórios."));
S(bullet("Autenticação por JWT e autorização baseada em propriedade do recurso (cada utilizador só acede e altera os seus próprios dados)."));
S(bullet("Atribuição de ratings (1–5) e flag de recomendação aos restaurantes."));
S(bullet("Atualização dinâmica do perfil do utilizador (categorias preferidas ajustadas pelos ratings) e do item (stars e review_count recalculados a cada avaliação)."));
S(bullet("Recomendações personalizadas: colaborativas, híbridas completas, previsão de rating para um restaurante e utilizadores semelhantes."));
S(bullet("Gestão de perfil: categorias, faixa de preço, amigos (social) e nome."));

S(h2("3.3. Arquitetura"));
S(p([
  tr("A solução segue uma arquitetura cliente-servidor desacoplada. O "), tr("backend", { bold: true }),
  tr(" é uma Web API em FastAPI (Python) com SQLAlchemy 2.0 sobre PostgreSQL, organizada em routers (auth, users, businesses, reviews, recommendations). O "),
  tr("frontend", { bold: true }),
  tr(" é uma SPA em React 18 + Vite com React Router. A comunicação é via JSON sobre HTTP, com CORS configurável."),
]));
S(p([
  tr("Um aspeto central é o "), tr("modelo de dupla identidade", { bold: true }),
  tr(": a conta autenticada (auth_users) é ligada a um utilizador do dataset (users) através de uma tabela de associação (auth_user_dataset_links). Isto permite que contas reais herdem o histórico de um utilizador do dataset e que o sistema de recomendação opere sobre o mesmo espaço de identificadores."),
]));
S(p([
  tr("A segurança usa JWT (PyJWT) com hashing de password PBKDF2-HMAC-SHA256 e sal por utilizador. Cada pedido a recursos privados apresenta o token em "),
  tr("Authorization: Bearer", { font: "Courier New" }),
  tr("; uma dependência valida o token e a propriedade do recurso, devolvendo 401 (token inválido/expirado) ou 403 (recurso de outro utilizador). No frontend, um wrapper authFetch injeta o token e trata o 401, e um componente ProtectedRoute protege as rotas privadas."),
]));
S(p("Para desempenho, os mapas utilizador→item e item→utilizador, bem como as normas dos vetores de avaliação, são mantidos em cache (TTL de 30 s) e invalidados quando uma nova review é submetida. A seleção de vizinhos usa um índice invertido item→utilizadores, evitando varrer todos os utilizadores em cada pedido. O esquema da base de dados é gerido com Alembic."));

S(h2("3.4. Algoritmos implementados"));
S(p([tr("Recomendador não personalizado (baseline).", { bold: true }),
  tr(" Ordenação por classificação ponderada Bayesiana, que equilibra a média do item com a confiança dada pelo número de avaliações:")]));
S(p([tr("score = (v / (v + m)) · R + (m / (v + m)) · C", { font: "Courier New" })], { alignment: AlignmentType.CENTER }));
S(p([tr("onde v = nº de avaliações do item, R = média do item, C = média global e m = limiar de confiança (por omissão 50). Itens com poucas avaliações são puxados para a média global, evitando sobrevalorizar itens com uma única avaliação alta.")]));
S(p([tr("Filtragem colaborativa (CF).", { bold: true }),
  tr(" KNN user-based com similaridade do cosseno entre vetores de avaliação. A previsão para um item é a média das avaliações dos vizinhos ponderada pela similaridade. Os candidatos a vizinhos são restritos aos utilizadores que partilham pelo menos um item avaliado (índice invertido).")]));
S(p([tr("Filtragem baseada em conteúdo (CBF).", { bold: true }),
  tr(" Similaridade de Jaccard sobre conjuntos de características do negócio (categorias e atributos, incluindo atributos aninhados como GoodForMeal). A pontuação de conteúdo de um candidato é a média das similaridades aos itens avaliados, ponderada pelo rating.")]));
S(p([tr("Componente de perfil.", { bold: true }),
  tr(" Grau de correspondência entre as categorias preferidas do utilizador e as do candidato, convertido numa pontuação em [1, 5].")]));
S(p([tr("Componente social.", { bold: true }),
  tr(" Média das avaliações que os amigos do utilizador deram ao candidato (ativável por preferência use_friends_boost). Concretiza a vertente de Social Filtering.")]));
S(p([tr("Solução híbrida (weighted).", { bold: true }),
  tr(" A pontuação final combina as quatro componentes:")]));
S(p([tr("score = 0.50·CF + 0.20·CBF + 0.15·perfil + 0.15·social", { font: "Courier New" })], { alignment: AlignmentType.CENTER }));
S(p("Sobre esta pontuação aplicam-se ainda: (i) filtros de cidade e faixa de estrelas preferidas, com fallback (se um filtro esvaziar a lista, é ignorado para garantir resultados); (ii) um sinal contextual de período de refeição (almoço/jantar) baseado nos atributos e horários; e (iii) a injeção de candidatos para cold start de itens (Secção 5). Listas baseadas em conteúdo usam ainda uma distância euclidiana ao item ideal (5 estrelas, muito avaliado) para ordenação."));
S(p([tr("Justificação da escolha.", { bold: true }),
  tr(" Optou-se pelo tipo weighted por ser transparente e afinável: cada componente tem um peso explícito e interpretável, o que é adequado a um domínio onde queremos combinar gosto pessoal (CF), semelhança de conteúdo (CBF), preferências declaradas (perfil) e influência social (amigos). É também robusto: quando uma componente não tem sinal (ex.: utilizador sem amigos), o seu contributo é nulo e as restantes continuam a ordenar os itens.")]));

// 4. Cold start utilizadores
S(h1("4. Estratégia para Cold Start de utilizadores"));
S(p("Um utilizador novo não tem histórico de avaliações, pelo que a CF não produz recomendações. A estratégia adotada tem três camadas:"));
S(bullet([tr("Inquérito no registo.", { bold: true }), tr(" O formulário de registo recolhe (opcionalmente) categorias preferidas, cidade e faixa de preço, criando de imediato um perfil que alimenta as componentes de conteúdo e de perfil do híbrido.")]));
S(bullet([tr("Fallback por popularidade.", { bold: true }), tr(" Enquanto não houver avaliações suficientes, o sistema apresenta as recomendações não personalizadas (classificação Bayesiana), garantindo sugestões de qualidade desde o primeiro acesso.")]));
S(bullet([tr("Atualização dinâmica do perfil.", { bold: true }), tr(" À medida que o utilizador avalia, as categorias dos itens muito apreciados (≥ 4) são adicionadas ao perfil e as dos muito penalizados (≤ 2) removidas, fazendo a transição suave de cold start para recomendação personalizada.")]));

// 5. Cold start itens
S(h1("5. Estratégia para Cold Start de itens"));
S(p("Um item novo (poucas ou nenhumas avaliações) é invisível à CF, porque nenhum vizinho o avaliou — nunca entra no conjunto de candidatos colaborativos. A estratégia para o cold start de itens combina:"));
S(bullet([tr("Injeção de candidatos baseados em conteúdo.", { bold: true }), tr(" Para além dos candidatos colaborativos, o híbrido recupera da base de dados negócios cujas categorias correspondem ao perfil/itens apreciados do utilizador, dando prioridade aos que têm menos avaliações. Estes itens entram com pontuação colaborativa nula e são ordenados pela sua adequação de conteúdo/perfil/social.")]));
S(bullet([tr("Boost de exploração.", { bold: true }), tr(" Itens com menos de 5 avaliações recebem um pequeno incremento de pontuação, evitando que sejam sempre suplantados pelos itens populares.")]));
S(bullet([tr("Robustez do recomendador não personalizado.", { bold: true }), tr(" O parâmetro m da classificação Bayesiana controla quanta confiança é exigida, evitando expor itens com avaliação insuficiente como se fossem fiáveis.")]));
S(p("Esta abordagem é validada empiricamente na Secção 6 (cobertura da long-tail): o recomendador por popularidade nunca expõe itens cold, enquanto as variantes de conteúdo e híbrida os colocam consistentemente no top-K."));

// 6. Experimentação e resultados
S(h1("6. Experimentação e resultados"));
S(h2("6.1. Metodologia"));
S(p("A avaliação offline usa uma divisão temporal por utilizador: para cada utilizador, as avaliações mais antigas formam o treino e as mais recentes o teste (test_ratio = 0,2; mínimo de 2 itens de teste; utilizadores com pelo menos 3 avaliações). Esta divisão é mais realista do que uma aleatória, pois evita usar o futuro para prever o passado. Após a divisão obtêm-se 15 470 itens de catálogo em treino, 5 260 casos de teste e 299 utilizadores avaliados."));
S(p("Usaram-se duas famílias de métricas: RMSE para o erro de predição de rating, e Precision@10, Recall@10, MAP@10 e NDCG@10 (média macro por utilizador) para a qualidade do ranking. Compararam-se cinco modelos: baseline (popularidade), conteúdo, colaborativo (cosseno), colaborativo (Jaccard) e o híbrido ponderado."));

S(h2("6.2. Erro de predição (RMSE)"));
S(table(
  ["Modelo", "RMSE (↓ melhor)"],
  [
    ["Híbrido (weighted)", "1,0769"],
    ["Conteúdo", "1,0835"],
    ["Colaborativo (cosseno)", "1,1333"],
    ["Colaborativo (Jaccard)", "1,1340"],
    ["Baseline (popularidade)", "1,1800"],
  ],
  [6026, 3000],
));
S(p("O híbrido obtém o menor RMSE (1,0769), superando todas as abordagens individuais, incluindo a melhor isolada (conteúdo, 1,0835) e claramente o baseline (1,1800). A combinação de sinais colaborativo e de conteúdo produz previsões de rating mais precisas do que qualquer técnica sozinha."));

S(h2("6.3. Qualidade de ranking (@10)"));
S(table(
  ["Modelo", "Precision", "Recall", "MAP", "NDCG"],
  [
    ["Baseline", "0,0060", "0,0023", "0,0021", "0,0064"],
    ["Híbrido (weighted)", "0,0043", "0,0030", "0,0013", "0,0044"],
    ["Colaborativo (Jaccard)", "0,0037", "0,0024", "0,0010", "0,0036"],
    ["Conteúdo", "0,0027", "0,0011", "0,0008", "0,0027"],
    ["Colaborativo (cosseno)", "0,0023", "0,0016", "0,0005", "0,0021"],
  ],
  [3026, 1500, 1500, 1500, 1500],
));
S(p("No ranking, os valores absolutos são baixos para todos os modelos (ver análise crítica). O baseline lidera em Precision e NDCG, enquanto o híbrido obtém o melhor Recall@10 e fica em segundo nas restantes métricas, à frente das três abordagens individuais personalizadas. Observa-se o conhecido compromisso entre o enviesamento por popularidade (favorece a precision quando os itens recentes retidos tendem a ser populares) e a personalização (favorece a cobertura/recall)."));

S(h2("6.4. Cold start de itens (cobertura da long-tail)"));
S(p("Mediu-se o número médio de itens cold (< 5 avaliações de treino) que cada modelo coloca no top-10. Note-se que, nesta amostra esparsa, 15 222 dos 15 470 itens são cold, pelo que a métrica reflete sobretudo a capacidade de explorar a cauda do catálogo."));
S(table(
  ["Modelo", "Itens cold no top-10 (média)"],
  [
    ["Baseline (popularidade)", "0,00"],
    ["Colaborativo (cosseno)", "9,06"],
    ["Conteúdo", "9,19"],
    ["Híbrido (weighted)", "9,42"],
  ],
  [6026, 3000],
));
S(p("O recomendador por popularidade não expõe qualquer item cold (cobertura nula da long-tail), confirmando a sua cegueira a itens novos. As abordagens de conteúdo e híbrida expõem-nos consistentemente, com o híbrido a apresentar a maior cobertura — evidência empírica direta da eficácia da estratégia de cold start de itens."));

// 7. Análise crítica
S(h1("7. Análise crítica"));
S(p("Os resultados confirmam a hipótese central: a solução híbrida melhora a predição de rating (melhor RMSE de todos os modelos) e equilibra precisão e cobertura no ranking, sendo competitiva e mais robusta do que qualquer abordagem isolada. A vantagem é particularmente clara no cold start de itens, onde só as componentes de conteúdo permitem alcançar a long-tail."));
S(p("Os valores absolutos das métricas de ranking são, contudo, muito baixos. Isto deve-se à natureza dos dados e do protocolo: apenas 300 utilizadores e ~29 mil avaliações sobre ~18,8 mil itens resultam numa matriz extremamente esparsa; a divisão temporal deixa poucos itens relevantes por utilizador no teste; e o espaço de candidatos é enorme (acertar 2–3 itens exatos no top-10 entre milhares é improvável). Estes números devem, por isso, ser lidos em termos relativos (comparação entre modelos) e não absolutos."));
S(p("O baseline supera ligeiramente o híbrido em Precision/NDCG porque os itens retidos mais recentes tendem a ser populares — um efeito de enviesamento por popularidade bem documentado na literatura, que penaliza injustamente a personalização nas métricas de ranking offline. O melhor Recall e a maior cobertura de itens cold do híbrido mostram, ainda assim, o seu valor para descoberta e diversidade."));
S(p("Limitações: (i) a componente social foi omitida da avaliação offline por o grafo de amigos ser esparso no conjunto de teste; (ii) a CF não pondera a recência das avaliações; (iii) os pesos do híbrido foram definidos por conhecimento do domínio e não otimizados automaticamente; (iv) o texto das reviews não é explorado (apenas categorias/atributos). Trabalho futuro: otimização dos pesos (ex.: grid search), modelos de fatores latentes (SVD), e incorporação de sinais textuais e de localização geográfica."));

// 8. Conclusões
S(h1("8. Conclusões"));
S(p("Foi desenvolvido um Sistema de Recomendação Híbrido completo para restauração, exposto por uma Web API com autenticação e autorização, recomendações não personalizadas para visitantes, registo com inquérito, atribuição de ratings e atualização dinâmica de perfis e itens. A solução híbrida ponderada combina filtragem colaborativa, baseada em conteúdo, perfil e sinais sociais, com estratégias explícitas para o cold start de utilizadores e de itens."));
S(p("A experimentação mostra que o híbrido supera as abordagens individuais no RMSE e oferece o melhor compromisso no ranking, além de cobrir a long-tail que a popularidade ignora. Os resultados, ainda que modestos em valor absoluto devido à esparsidade dos dados, validam a abordagem e apontam direções claras de melhoria."));

// 9. Referências
S(h1("9. Referências"));
const refs = [
  "Burke, R. (2002). Hybrid Recommender Systems: Survey and Experiments. User Modeling and User-Adapted Interaction, 12(4), 331–370.",
  "Ricci, F., Rokach, L., & Shapira, B. (2015). Recommender Systems Handbook (2nd ed.). Springer.",
  "Sarwar, B., Karypis, G., Konstan, J., & Riedl, J. (2001). Item-based Collaborative Filtering Recommendation Algorithms. WWW '01.",
  "Herlocker, J., Konstan, J., Borchers, A., & Riedl, J. (1999). An Algorithmic Framework for Performing Collaborative Filtering. SIGIR '99.",
  "Herlocker, J., Konstan, J., Terveen, L., & Riedl, J. (2004). Evaluating Collaborative Filtering Recommender Systems. ACM TOIS, 22(1), 5–53.",
  "Yelp Open Dataset. https://www.yelp.com/dataset",
  "FastAPI Documentation. https://fastapi.tiangolo.com",
  "SQLAlchemy 2.0 Documentation. https://docs.sqlalchemy.org",
  "React Documentation. https://react.dev",
];
refs.forEach((r) => S(bullet(r)));

// 10. Declaração IA
S(h1("10. Declaração de utilização de IA generativa"));
S(p([tr("Ferramentas utilizadas.", { bold: true }), tr(" Foram utilizadas ferramentas de IA generativa, nomeadamente o Claude (Anthropic), através do assistente de desenvolvimento Claude Code.")]));
S(p([tr("De que forma foram utilizadas.", { bold: true }), tr(" Apoio na refatoração e correção do backend (introdução de autenticação/autorização por JWT, implementação do cold start de itens e da componente social, organização do híbrido ponderado), na criação de testes automáticos (pytest e vitest), na configuração de migrações (Alembic), na adição de células de avaliação ao notebook e na redação inicial deste relatório.")]));
S(p([tr("Objetivo.", { bold: true }), tr(" Acelerar tarefas repetitivas e de documentação, sugerir boas práticas (segurança, estrutura de testes) e estruturar a comparação experimental, mantendo o foco do grupo nas decisões de conceção.")]));
S(p([tr("Partes resultantes desse apoio.", { bold: true }), tr(" Excertos de código nos módulos de autenticação, recomendação e testes, a configuração de Alembic, as células de avaliação do híbrido no notebook e o rascunho textual deste documento. Todo o conteúdo gerado foi revisto, testado e validado pelo grupo.")]));
S(p([tr("Responsabilidade.", { bold: true }), tr(" A responsabilidade científica, técnica e ética do trabalho é integralmente do grupo. Os resultados experimentais reportados foram obtidos pela execução do código sobre o dataset, e não gerados pela ferramenta de IA.")]));

// ── document ───────────────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: "Arial", color: ACCENT },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 160, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 600, hanging: 280 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [tr("SISREC 2025/2026 — Relatório Final     ", { size: 16, color: "808080" }),
          tr("Página ", { size: 16, color: "808080" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "808080" })],
      })] }),
    },
    children: [...cover, ...toc, ...body],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("../SISREC_Relatorio_Final.docx", buf);
  console.log("WROTE SISREC_Relatorio_Final.docx", buf.length, "bytes");
});
