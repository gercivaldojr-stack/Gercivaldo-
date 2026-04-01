# Conversor Juridico PDF/DOCX → Markdown (v4.0)

Converte documentos juridicos (PDF, DOCX, TXT) para Markdown limpo e estruturado, com heuristicas especificas para pecas processuais e doutrina juridica.

## Funcionalidades

- **Extracao**: PDF (PyMuPDF com tabelas), DOCX (paragrafos + tabelas intercalados), TXT, MD
- **Limpeza**: hifenizacao, OCR, headers/footers repetidos (preserva 1a ocorrencia), paginacao residual, glyphs corrompidos, e-reader boilerplate
- **Reconexao CNJ**: siglas (HC, REsp, ADI...) partidas por quebra de linha
- **Juncao de paragrafos**: preposicoes no final forcam juncao; protege tabelas, headings, listas, alineas
- **Heuristicas juridicas**:
  - **Modo forense**: titulo da peca (H1), secoes numeradas MAIUSCULAS (H2), subsecoes Da/Do (H3), citacoes jurisprudenciais (blockquote), metadados expandidos
  - **Modo doutrina**: CAPITULO/PARTE (H1), SECAO (H2), secoes numeradas (H3)
- **Separacao de alineas**: a), b), I —, 1.1 como paragrafos separados
- **Metadados YAML**: titulo, proad/SEI, data, orgao, tipo_peca, paciente, autoridade_coatora, pedido_liminar
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
)
print(result.markdown)
```

## Testes

```bash
cd converter_md_project_v2
python -m pytest -v
```

218 testes cobrindo todos os modulos.

## Arquitetura

```
converter_md_project_v2/
├── app/main.py              # Interface Streamlit
├── core/
│   ├── extractors.py        # PDF/DOCX/TXT/MD extraction
│   ├── cleaning.py          # Limpeza, CNJ, paginacao, paragrafos, alineas
│   ├── legal_heuristics.py  # Headings, blockquotes, citacoes, TOC
│   ├── metadata.py          # Frontmatter YAML + metadados expandidos
│   ├── pipeline.py          # Orquestrador principal
│   └── piece_separator.py   # Separacao de pecas processuais
├── tests/                   # 218 testes
├── requirements.txt
├── CHANGELOG.md
└── README.md
```
