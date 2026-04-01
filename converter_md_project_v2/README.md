# Conversor Juridico PDF/DOCX → Markdown (v4.1)

Converte documentos juridicos (PDF, DOCX, TXT) para Markdown limpo e estruturado, com heuristicas especificas para pecas processuais e doutrina juridica.

## Funcionalidades

- **Extracao**: PDF (PyMuPDF com tabelas), DOCX (paragrafos + tabelas intercalados), TXT, MD
- **Limpeza**: hifenizacao, OCR, headers/footers repetidos (preserva 1a ocorrencia), paginacao residual, glyphs corrompidos, e-reader boilerplate
- **Reconexao CNJ**: siglas (HC, REsp, ADI...) partidas por quebra de linha
- **Juncao de paragrafos**: preposicoes no final forcam juncao; protege tabelas, headings, listas, alineas
- **Heuristicas juridicas**:
  - Modo forense: titulo da peca (H1), secoes numeradas MAIUSCULAS (H2), subsecoes Da/Do (H3), citacoes jurisprudenciais (blockquote), metadados expandidos
  - Modo doutrina: CAPITULO/PARTE (H1), SECAO (H2), secoes numeradas (H3)
- **Separacao de alineas**: a), b), I —, 1.1 como paragrafos separados
- **Metadados YAML**: titulo, proad/SEI, data, orgao, tipo_peca, paciente, autoridade_coatora, pedido_liminar
- **Metadados processuais** (v4.1): comarca, acoes_cumuladas, processo_origem
- **Itens enumerados** (v4.1): sequencias com `;` convertidas em listas Markdown
- **Notas internas** (v4.1): blocos "Observacoes finais de uso" demarcados em blockquote
- **Separacao de pecas**: detecta multiplas pecas processuais em um documento
- **Sumario automatico**: TOC gerado a partir dos headings
- **Interface Streamlit**: upload, configuracao, preview, download individual e ZIP

## Instalacao

```bash
pip install -r converter_md_project_v2/requirements.txt
```

## Uso

### Interface web (Streamlit)

```bash
cd converter_md_project_v2
streamlit run app/main.py
```

### Uso programatico

```python
from core.pipeline import convert_document

result = convert_document(
    file_bytes=open("peticao.pdf", "rb").read(),
    filename="peticao.pdf",
    mode="forense",           # ou "doutrina"
    detect_citations=True,    # citacoes como blockquote (P7)
    extract_metadata=True,    # metadados expandidos (P8)
    extract_procedural=True,  # metadados processuais (M1 v4.1)
    separate_enums=True,      # itens enumerados (M2 v4.1)
    wrap_notes=True,          # notas internas (M3 v4.1)
)

print(result.markdown)
```

## Testes

```bash
cd converter_md_project_v2
python -m pytest -v
```

246 testes cobrindo todos os modulos.

## Arquitetura

```
converter_md_project_v2/
├── app/main.py                # Interface Streamlit
├── core/
│   ├── extractors.py          # PDF/DOCX/TXT/MD extraction
│   ├── cleaning.py            # Limpeza, CNJ, paginacao, paragrafos, alineas
│   ├── legal_heuristics.py    # Headings, blockquotes, citacoes, TOC, enumerados, notas
│   ├── metadata.py            # Frontmatter YAML + metadados expandidos + processuais
│   ├── pipeline.py            # Orquestrador principal
│   └── piece_separator.py     # Separacao de pecas processuais
├── tests/                     # 246 testes
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

### Fluxo do pipeline (`convert_document`)

```
Documento (PDF/DOCX/TXT)
        |
   [1] extract_text()           <- extractors.py
        |
   [2] clean_text()             <- cleaning.py
        |   - dehyphenation, OCR cleanup
        |   - remove headers/footers repetidos
        |   - remove paginacao residual
        |   - rejoin broken paragraphs
        |   - reconnect CNJ numbers
        |   - separate enumerations
        |
   [3] apply_legal_heuristics() <- legal_heuristics.py
        |   - classifica headings (H1/H2/H3) por modo
        |   - detecta citacoes jurisprudenciais (blockquote)
        |   - separa itens enumerados (M2)
        |   - demarca notas internas (M3)
        |
  [3a] _strip_existing_frontmatter()  <- pipeline.py
        |   - remove YAML/TOC residual do original
        |
  [3b] generate_frontmatter()   <- metadata.py
        |   - gera bloco YAML com metadados
        |   - injeta metadados processuais (M1)
        |
  [3c] generate_toc()           <- legal_heuristics.py
        |   - gera sumario automatico
        |
   [4] separate_pieces()        <- piece_separator.py (opcional)
        |
   ConversionResult
        - .markdown   (texto final)
        - .pieces     (pecas separadas, se habilitado)
        - .stats      (chars_raw, chars_cleaned, chars_final, lines_*)
        - .success / .error
```

### Decisoes de design

**Heuristicas por modo**: o conversor opera em dois modos exclusivos. O modo "forense" usa padroes especificos de pecas processuais brasileiras (PETICAO INICIAL como H1, DOS FATOS/DOS PEDIDOS como H2, Da responsabilidade como H3). O modo "doutrina" segue hierarquia academica (CAPITULO/PARTE como H1, SECAO como H2, numeradas como H3).

**Protecao de alineas**: alineas juridicas como `a)`, `b)`, `I —`, `1.1` sao explicitamente protegidas de virar headings. Isso evita que listas de pedidos sejam erroneamente classificadas como secoes do documento.

**Frontmatter idempotente**: o pipeline remove qualquer frontmatter YAML pre-existente antes de gerar um novo, garantindo que reconversoes nao acumulem metadados duplicados.

**Citacoes como blockquote**: no modo forense, paragrafos que comecam com "No HC", "No REsp", "No AgRg" sao automaticamente formatados como blockquote Markdown, preservando a distincao visual entre argumentacao e jurisprudencia citada.
