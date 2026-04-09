# Changelog

## v7.2 (2026-04-09)

### Novos recursos

- **OCR seletivo funcional no Streamlit Cloud**: criado `packages.txt` na raiz do repositório com pacotes Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-por`, `tesseract-ocr-eng`, `tesseract-ocr-spa`, `tesseract-ocr-fra`, `tesseract-ocr-deu`, `tesseract-ocr-ita`) para instalação automática via Streamlit Cloud.
- **Detecção automática de Tesseract na UI** (`app/main.py`): novo decorator `@st.cache_resource` com `_check_tesseract()` verifica disponibilidade, versão e idiomas instalados do Tesseract no boot da aplicação. Indicador visual na sidebar: ✅ verde com versão e idiomas se disponível, ⚠️ amarelo se ausente. Checkbox "Habilitar OCR seletivo" automaticamente desabilitado quando Tesseract não está instalado.
- **Filtragem de idiomas OCR**: selectbox de idioma mostra apenas idiomas realmente instalados no Tesseract do ambiente, evitando erros em runtime.
- **Estatísticas de OCR nos resultados**: pipeline agora rastreia `total_pages` e `ocr_pages` no dict de stats. Interface exibe quantas páginas usaram OCR vs. texto nativo após conversão.
- **Feedback durante conversão com OCR**: barra de progresso indica "(com OCR seletivo)" quando OCR está habilitado. Aviso automático se OCR habilitado mas nenhum PDF selecionado.
- **`tesseract_available()`** (`core/extractors.py`): nova função utilitária para verificação programática da disponibilidade do Tesseract.

### Alterações internas

- `extract_text()` e `_extract_pdf()` aceitam novo parâmetro `stats: dict | None` para rastrear métricas de OCR (total_pages, ocr_pages) durante extração.
- `convert_document()` em `pipeline.py` passa `result.stats` para `extract_text()`, permitindo coleta de estatísticas OCR sem alterar a interface de retorno.
- CSS customizado na UI com classes `.ocr-available` e `.ocr-unavailable` para indicadores visuais de status.


## v7.1 (2026-04-05)

### Novos recursos

- **Detecção automática de idioma** (`core/lang_detector.py`): quando `ocr_lang="auto"`, analisa stop words + palavras jurídicas do texto nativo para detectar idioma (pt, en, es, fr, de, it) e configurar o Tesseract automaticamente. Sem dependências externas. Default continua "por" (backward compatible). Votação por amostragem de páginas para documentos inteiros. Fallback por página em workers paralelos. 15 testes novos.

## v7.0 (2026-04-05)

### Novos recursos

- **Cache de OCR** (`core/ocr_cache.py`): salva resultados OCR em disco (JSON) por hash SHA256 do conteúdo visual da página + idioma. Evita re-processamento ao converter o mesmo PDF múltiplas vezes. Cache compartilhável entre workers paralelos (baseado em arquivos). CLI: `--ocr-cache`, `--ocr-cache-dir`, `--ocr-cache-clear`, `--ocr-cache-stats`. Streamlit: checkbox na seção OCR. 10 testes novos.

## v6.0 (2026-04-05)

### Novos recursos

- **Processamento paralelo**: `core/parallel.py` com `ProcessPoolExecutor` para batch e chunks de PDF. `--workers N` na CLI (0=sequencial, -1=auto, N=fixo). `convert_batch_parallel()` processa múltiplos arquivos em workers separados. `process_pdf_chunks_parallel()` processa chunks de um PDF em paralelo. Fallback sequencial automático quando max_workers=1 ou arquivo único.
- **Header/footer com amostragem**: `_detect_hf_zones()` refatorada para amostrar apenas 50 páginas em PDFs grandes (primeiras 10 + últimas 10 + N do meio), reduzindo memória de O(N) para O(50). Padrões identificados na amostra são aplicados a todas as páginas em streaming.

## v5.1 (2026-04-05)

### Novos recursos

- **Detecção de colunas**: `core/column_detector.py` detecta PDFs com layout de 2 colunas e reordena os blocos de texto na ordem correta de leitura. Habilitado por padrão, desativável via `--no-columns` na CLI ou checkbox na interface Streamlit.
- **Exportação HTML**: `core/html_exporter.py` converte Markdown para HTML completo com CSS jurídico (fonte serif, blockquotes com borda, tabelas com bordas). Usa biblioteca `markdown` com extensões tables, fenced_code e toc.
- **Exportação DOCX**: `core/docx_exporter.py` converte Markdown para DOCX via `python-docx`. Suporta headings H1-H3, parágrafos, blockquotes com indentação e itálico, listas bullet, tabelas e separadores.
- **Formato de saída configurável**: `--format {md,html,docx}` na CLI. Selectbox na interface Streamlit.
- **ConversionResult expandido**: campos `.html` e `.docx_bytes` (None quando não solicitado).
- **Parâmetros novos em pipeline/CLI/config/Streamlit**: `detect_columns`, `output_format`.

## v4.1 (2026-04-01)

### Novos recursos (M1–M5)

- **M1 — Metadados processuais**: nova funcao `extract_procedural_metadata()` extrai comarca, acoes cumuladas e outros dados processuais do texto estruturado. Ativado via `extract_procedural=True` (apenas modo forense). Campos injetados no frontmatter YAML antes do fechamento `---`.
- **M2 — Itens enumerados**: nova funcao `separate_enumerated_items()` converte sequencias com `;` apos linha terminando em `:` em listas Markdown (`- `). Ativado via `separate_enums=True` (apenas modo forense).
- **M3 — Notas internas**: nova funcao `wrap_internal_notes()` detecta blocos como "Observacoes finais de uso", "Nota de adequacao", "Instrucoes para protocolo" e os demarca em blockquote com rotulo `> **Nota interna**`. Ativado via `wrap_notes=True` (apenas modo forense).
- **M4 — Paginacao residual**: `remove_residual_pagination()` melhorada — remove "Pagina N", "Pag. N", "— N —" e numeros isolados nas 3 primeiras/ultimas linhas.
- **M5 — Secoes numeradas forense**: secoes `\d+. MAIUSCULAS` viram H2, subsecoes `\d+.\d+` viram H3, `EXCELENTISSIMO` vira H2, sem promocao H2→H1.

### Novos recursos (F1–F5)

- **F1 — Formatacao inline DOCX** (`9adfc56`): a extracao DOCX agora preserva **bold** e *italic* originais do documento. O extrator itera sobre os runs de cada paragrafo, detectando `run.bold` e `run.italic`, e envolve o texto com `**...**` ou `*...*` conforme apropriado. +6 testes novos (252 total).
- **F2 — Modo `google`** (`8c3e429`): novo modo de heuristica em `apply_legal_heuristics(mode="google")` voltado para documentos do Google Docs. Aplica negrito inline sem gerar headings H1/H2/H3, preservando a estrutura plana do documento. Os modos `forense` e `doutrina` existentes nao foram alterados. +12 testes novos (264 total).
- **F3 — Ementa/resumo em italico** (`96fb59e`): detecta blocos de ementa ou resumo no inicio do documento e os envolve automaticamente em italico Markdown (`*...*`). +7 testes novos (271 total).
- **F4 — Assinaturas formatadas** (`af7b227`): detecta blocos de assinatura (nomes em maiusculas, cargos, OAB, etc.) e os formata com separador `---` antes do bloco e nomes em **negrito**. +7 testes novos (278 total).
- **F5 — TOC opcional** (`42fb111`): o sumario (Table of Contents) agora e desabilitado por padrao. Nova opcao `generate_toc` no pipeline e checkbox "Gerar sumario (TOC)" na sidebar do Streamlit. +2 testes novos (280 total).

### Protecoes e correcoes

- **M3 (protecao)**: alineas juridicas `a)`, `b)`, `I —`, `1.1`, `1.2` protegidas de virar headings `###` no modo forense.
- **Correcao titulo "Sumario"**: `_strip_existing_frontmatter()` agora remove blocos `## Sumario` / `## Indice` seguido de listas `- [...]` ate linha em branco; tambem remove TOC malformado (3+ linhas `- [` sem `](#`).
- **Correcao YAML inline**: linhas soltas tipo `titulo: "..."`, `data: "..."` do documento original sao removidas antes de gerar o novo frontmatter.
- **Correcao frontmatter duplicado**: a funcao `_strip_existing_frontmatter` foi movida para ANTES do passo 3b (`generate_frontmatter`), eliminando titulos "Sumario"/"Indice" e YAML residual.

### Interface Streamlit

- Novas opcoes na sidebar: "Extrair metadados processuais" (M1), "Separar itens enumerados" (M2), "Demarcar notas internas" (M3).
- Nova opcao na sidebar: "Gerar sumario (TOC)" (F5, default: desabilitado).
- Versao exibida na sidebar: v4.1.

### Testes

- 280 testes passando (34 novos com F1–F5, 28 novos com M1–M5, total +62 desde v4.0).
- Novos testes para: `separate_enumerated_items`, `wrap_internal_notes`, `extract_procedural_metadata`, secoes numeradas forense (M5), alineas protegidas (M3).
- Novos testes para: formatacao inline DOCX (F1), modo `google` (F2), ementa italico (F3), assinaturas (F4), TOC opcional (F5).

---

## v4.0 (2026-04-01)

### Criticos (integridade do conteudo)

- **P1/P2**: Extracao de tabelas PDF (PyMuPDF `find_tables()`) e DOCX (`iter_block_items()`) ja implementados desde v3.0.
- **P3/P10**: Header/footer com preservacao da 1a ocorrencia — `remove_repeated_headers_footers(preserve_first=True)` mantem a primeira aparicao de cada padrao repetido (pode ser conteudo substantivo na pagina 1).
- **P11/M4**: `remove_residual_pagination()` — remove "Pagina N", "Pag. N", "— N —" e numeros isolados nas primeiras/ultimas 3 linhas.

### Importantes (estrutura e legibilidade)

- **P4/M5**: Hierarquia de headings forense — secoes numeradas `\d+. MAIUSCULAS` viram H2, subsecoes `\d+.\d+` viram H3, EXCELENTISSIMO vira H2, sem promocao H2→H1.
- **P5/M1**: `rejoin_broken_paragraphs()` melhorado — preposicoes no final (de/da/do/na/com/que/e/ou/para/por/ao/a) forcam juncao; protecao de tabelas Markdown (|), headings (#), listas (-, *, >), alineas juridicas.
- **P6/M2**: `reconnect_cnj_numbers()` — reconecta siglas CNJ (REsp, HC, ADI, ADPF, ARE, AgRg, etc.) partidas por quebra de linha.
- **P7**: Citacoes jurisprudenciais "No HC/REsp/AgRg..." detectadas como blockquote Markdown (modo forense apenas). Nova funcao `_JURISPRUDENCE_CITATION_START` em `detect_blockquotes()`.
- **P8**: Metadados expandidos no frontmatter YAML — `tipo_peca`, `paciente`, `autoridade_coatora`, `processo_origem`, `impetrante`, `pedido_liminar`. Ativado via `extract_metadata=True`.
- **P9**: `separate_enumerations()` — garante que alineas juridicas (a), b), I —, 1.1) sejam paragrafos separados com linha em branco antes.
- **M3**: Alineas juridicas (a), I —, 1.1) protegidas de virar headings ### no modo forense.

### Interface Streamlit

- Nova opcao: "Detectar citacoes jurisprudenciais como blockquote" (default: on, modo forense).
- Nova opcao: "Extrair metadados da peca" (default: off).
- Versao exibida na sidebar: v4.0.

### Testes

- 218 testes passando (72 novos desde v3.0).
- Cobertura para: preposicoes, linhas protegidas, CNJ, paginacao, alineas, header/footer P10, citacoes P7, metadados P8, enumeracoes P9.

---

## v3.0

Implementacao inicial do conversor juridico. Modulos: `extractors`, `cleaning`, `legal_heuristics`, `pipeline`, `piece_separator`, `metadata`. Interface Streamlit com upload, preview, download ZIP. 146 testes.
