# Conversor Juridico PDF/DOCX → Markdown (v5.0)

Converte documentos juridicos (PDF, DOCX, TXT) para Markdown limpo e estruturado, com heuristicas especificas para pecas processuais e doutrina juridica.

Otimizado para rodar em maquinas sem GPU e com RAM limitada.

## Funcionalidades

- **Extracao nativa rapida**: PDF (PyMuPDF com tabelas), DOCX (paragrafos + tabelas intercalados), TXT, MD
- **OCR seletivo por pagina**: aplica OCR apenas em paginas sem texto nativo (requer Tesseract)
- **Limpeza**: hifenizacao, headers/footers repetidos (preserva 1a ocorrencia), paginacao residual, glyphs corrompidos, e-reader boilerplate
- **Reconexao CNJ**: siglas (HC, REsp, ADI...) partidas por quebra de linha
- **Juncao de paragrafos**: preposicoes no final forcam juncao; protege tabelas, headings, listas, alineas
- **Heuristicas juridicas**:
  - Modo forense: titulo da peca (H1), secoes numeradas MAIUSCULAS (H2), subsecoes Da/Do (H3), citacoes jurisprudenciais (blockquote), metadados expandidos
  - Modo doutrina: CAPITULO/PARTE (H1), SECAO (H2), secoes numeradas (H3)
- **Separacao de alineas**: a), b), I —, 1.1 como paragrafos separados
- **Metadados YAML**: titulo, proad/SEI, data, orgao, tipo_peca, paciente, autoridade_coatora, pedido_liminar
- **Metadados processuais**: comarca, acoes_cumuladas, processo_origem
- **Itens enumerados**: sequencias com `;` convertidas em listas Markdown
- **Notas internas**: blocos "Observacoes finais de uso" demarcados em blockquote
- **Separacao de pecas**: detecta multiplas pecas processuais em um documento
- **Sumario automatico**: TOC gerado a partir dos headings
- **CLI completa**: interface de linha de comando com todas as opcoes
- **Configuracao YAML**: arquivo de config para presets reutilizaveis
- **Interface Streamlit**: upload, configuracao, preview, download individual e ZIP

## Instalacao

```bash
pip install -r converter_md_project_v2/requirements.txt
```

Para OCR seletivo (opcional):
```bash
pip install pytesseract Pillow
sudo apt install tesseract-ocr tesseract-ocr-por  # Ubuntu/Debian
```

## Uso

### CLI (recomendado)

```bash
cd converter_md_project_v2

# Conversao basica
python cli.py peticao.pdf

# Com opcoes
python cli.py peticao.pdf -o saida.md --mode forense --toc --citations

# Modo doutrina
python cli.py livro.pdf --mode doutrina -o livro.md

# OCR seletivo (paginas escaneadas)
python cli.py autos.pdf --ocr --ocr-lang por

# Intervalo de paginas (1-based: pagina 1 = primeira pagina)
python cli.py processo_grande.pdf --pages 1-50
python cli.py processo_grande.pdf --pages 1,5,10-20

# Processamento em chunks (economia de RAM para PDFs grandes)
python cli.py processo_1000pg.pdf --chunk-size 100
python cli.py processo_1000pg.pdf --pages 1-500 --chunk-size 50

# Lote (pasta inteira)
python cli.py ./autos/ --batch -o ./saida/

# Com arquivo de configuracao
python cli.py doc.pdf --config config.yaml

# Todas as opcoes
python cli.py doc.pdf --toc --separate --metadata --procedural --enums --notes
```

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
    mode="forense",
    detect_citations=True,
    extract_metadata=True,
    extract_procedural=True,
    separate_enums=True,
    wrap_notes=True,
    ocr_enabled=True,       # OCR seletivo
    ocr_lang="por",
    page_range="1-100",     # paginas 1-based (None = todas)
    chunk_size=50,          # processar 50 paginas por vez (None = tudo)
)

print(result.markdown)
```

## Configuracao

Copie `config.example.yaml` para `config.yaml` e ajuste:

```yaml
mode: "forense"
toc: false
detect_citations: true
ocr: false
ocr_lang: "por"
ocr_threshold: 30
```

Flags CLI tem prioridade sobre o arquivo YAML.

## Testes

```bash
cd converter_md_project_v2
python -m pytest -v
```

339 testes cobrindo todos os modulos.

## Arquitetura

```
converter_md_project_v2/
├── cli.py                     # Interface de linha de comando
├── config.example.yaml        # Exemplo de configuracao
├── app/main.py                # Interface Streamlit
├── core/
│   ├── config.py              # Sistema de configuracao (YAML + CLI)
│   ├── extractors.py          # PDF/DOCX/TXT/MD extraction + OCR seletivo
│   ├── cleaning.py            # Limpeza, CNJ, paginacao, paragrafos, alineas
│   ├── legal_heuristics.py    # Headings, blockquotes, citacoes, TOC, enumerados, notas
│   ├── metadata.py            # Frontmatter YAML + metadados expandidos + processuais
│   ├── pipeline.py            # Orquestrador principal
│   └── piece_separator.py     # Separacao de pecas processuais
├── tests/                     # 339 testes
├── requirements.txt
└── README.md
```

### Fluxo do pipeline (`convert_document`)

```
Documento (PDF/DOCX/TXT)
        |
   [1] extract_text()           <- extractors.py
        |   - extracao nativa via PyMuPDF (dict mode)
        |   - tabelas via find_tables()
        |   - remocao de header/footer por bbox
        |   - OCR seletivo por pagina (se habilitado)
        |   - page_range: selecao de paginas (1-based)
        |   - chunk_size: processamento em lotes com liberacao de RAM
        |
   [2] clean_text()             <- cleaning.py
        |   - dehyphenation, OCR cleanup
        |   - remove headers/footers repetidos
        |   - remove paginacao residual
        |   - reconstroi headings quebrados pelo PDF
        |   - rejoin broken paragraphs
        |   - reconnect CNJ numbers
        |   - separate enumerations
        |
   [3] apply_legal_heuristics() <- legal_heuristics.py
        |   - classifica headings (H1/H2/H3) por modo
        |   - detecta citacoes jurisprudenciais (blockquote)
        |   - separa itens enumerados
        |   - demarca notas internas
        |   - formata assinaturas
        |   - preenche gaps de numeracao
        |
  [3a] _strip_existing_frontmatter()  <- pipeline.py
  [3b] generate_frontmatter()   <- metadata.py
  [3c] generate_toc()           <- legal_heuristics.py
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

**Extracao nativa primeiro, OCR sob demanda**: a extracao via PyMuPDF e rapida e precisa para PDFs com texto embutido (maioria dos documentos juridicos digitais). O OCR so e acionado em paginas com menos de N caracteres, evitando processamento desnecessario e economizando tempo/memoria.

**Heuristicas por modo**: o conversor opera em dois modos exclusivos. O modo "forense" usa padroes especificos de pecas processuais brasileiras. O modo "doutrina" segue hierarquia academica.

**Protecao de alineas**: alineas juridicas como `a)`, `b)`, `I —`, `1.1` sao protegidas de virar headings.

**Frontmatter idempotente**: o pipeline remove qualquer frontmatter YAML pre-existente antes de gerar um novo.

**Processamento em chunks**: para PDFs com centenas de paginas, o parametro `chunk_size` faz o extrator abrir e fechar o documento a cada N paginas, liberando memoria entre chunks via `gc.collect()`. Isso evita picos de RAM em maquinas com recursos limitados. O resultado e identico ao processamento sem chunks.

**CLI + Config YAML**: a CLI aceita todos os parametros diretamente, mas tambem suporta arquivo YAML para presets reutilizaveis. Flags CLI tem prioridade.

### Limites conhecidos

- **OCR**: depende do Tesseract instalado no sistema. Qualidade varia com resolucao do scan.
- **Tabelas complexas**: tabelas com celulas mescladas podem perder estrutura.
- **PDFs com layout nao-linear**: documentos com colunas multiplas podem ter ordem de leitura incorreta.
- **Codificacao**: alguns PDFs antigos usam encodings nao-padrao que podem gerar glyphs corrompidos.
- **Batch nao-recursivo**: o modo `--batch` processa apenas arquivos no nivel imediato da pasta informada, sem percorrer subpastas.
- **Scan de headers/footers antes do chunking**: a deteccao de cabecalhos/rodapes (`_detect_hf_zones`) percorre todas as paginas do documento antes de iniciar o processamento em chunks. Em PDFs muito grandes, isso causa um pico de memoria inicial mesmo com `chunk_size` definido.

### Melhorias futuras sugeridas

1. **Deteccao de colunas**: analise de layout para PDFs com duas colunas (comum em doutrinas)
2. **Cache de OCR**: salvar resultados de OCR por pagina para evitar reprocessamento
3. **Paralelismo**: processar paginas em paralelo (multiprocessing) para PDFs grandes
4. **Exportacao alternativa**: suporte a saida em HTML ou DOCX alem de Markdown
5. **Deteccao de idioma**: auto-detectar idioma do documento para configurar OCR
