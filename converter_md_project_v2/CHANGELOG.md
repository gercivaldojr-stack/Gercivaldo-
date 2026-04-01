# Changelog

## v4.1 (2026-04-01)

### Novos recursos (M1–M5)

- **M1 — Metadados processuais**: nova funcao `extract_procedural_metadata()` extrai comarca, acoes cumuladas e outros dados processuais do texto estruturado. Ativado via `extract_procedural=True` (apenas modo forense). Campos injetados no frontmatter YAML antes do fechamento `---`.
- - **M2 — Itens enumerados**: nova funcao `separate_enumerated_items()` converte sequencias com `;` apos linha terminando em `:` em listas Markdown (`- `). Ativado via `separate_enums=True` (apenas modo forense).
  - - **M3 — Notas internas**: nova funcao `wrap_internal_notes()` detecta blocos como "Observacoes finais de uso", "Nota de adequacao", "Instrucoes para protocolo" e os demarca em blockquote com rotulo `> **Nota interna**`. Ativado via `wrap_notes=True` (apenas modo forense).
    - - **M4 — Paginacao residual**: `remove_residual_pagination()` melhorada — remove "Pagina N", "Pag. N", "— N —" e numeros isolados nas 3 primeiras/ultimas linhas.
      - - **M5 — Secoes numeradas forense**: secoes `\d+. MAIUSCULAS` viram H2, subsecoes `\d+.\d+` viram H3, `EXCELENTISSIMO` vira H2, sem promocao H2→H1.
       
        - ### Protecoes e correcoes
       
        - - **M3 (protecao)**: alineas juridicas `a)`, `b)`, `I —`, `1.1`, `1.2` protegidas de virar headings `###` no modo forense.
          - - **Correcao titulo "Sumario"**: `_strip_existing_frontmatter()` agora remove blocos `## Sumario` / `## Indice` seguido de listas `- [...]` ate linha em branco; tambem remove TOC malformado (3+ linhas `- [` sem `](#`).
            - - **Correcao YAML inline**: linhas soltas tipo `titulo: "..."`, `data: "..."` do documento original sao removidas antes de gerar o novo frontmatter.
              - - **Correcao frontmatter duplicado**: a funcao `_strip_existing_frontmatter` foi movida para ANTES do passo 3b (`generate_frontmatter`), eliminando titulos "Sumario"/"Indice" e YAML residual.
               
                - ### Interface Streamlit
               
                - - Novas opcoes na sidebar: "Extrair metadados processuais" (M1), "Separar itens enumerados" (M2), "Demarcar notas internas" (M3).
                  - - Versao exibida na sidebar: v4.1.
                   
                    - ### Testes
                   
                    - - 246 testes passando (28 novos desde v4.0).
                      - - Novos testes para: `separate_enumerated_items`, `wrap_internal_notes`, `extract_procedural_metadata`, secoes numeradas forense (M5), alineas protegidas (M3).
                       
                        - ---

                        ## v4.0 (2026-04-01)

                        ### Criticos (integridade do conteudo)

                        - **P1/P2**: Extracao de tabelas PDF (PyMuPDF `find_tables()`) e DOCX (`iter_block_items()`) ja implementados desde v3.0.
                        - - **P3/P10**: Header/footer com preservacao da 1a ocorrencia — `remove_repeated_headers_footers(preserve_first=True)` mantem a primeira aparicao de cada padrao repetido (pode ser conteudo substantivo na pagina 1).
                          - - **P11/M4**: `remove_residual_pagination()` — remove "Pagina N", "Pag. N", "— N —" e numeros isolados nas primeiras/ultimas 3 linhas.
                           
                            - ### Importantes (estrutura e legibilidade)
                           
                            - - **P4/M5**: Hierarquia de headings forense — secoes numeradas `\d+. MAIUSCULAS` viram H2, subsecoes `\d+.\d+` viram H3, EXCELENTISSIMO vira H2, sem promocao H2→H1.
                              - - **P5/M1**: `rejoin_broken_paragraphs()` melhorado — preposicoes no final (de/da/do/na/com/que/e/ou/para/por/ao/a) forcam juncao; protecao de tabelas Markdown (|), headings (#), listas (-, *, >), alineas juridicas.
                                - - **P6/M2**: `reconnect_cnj_numbers()` — reconecta siglas CNJ (REsp, HC, ADI, ADPF, ARE, AgRg, etc.) partidas por quebra de linha.
                                  - - **P7**: Citacoes jurisprudenciais "No HC/REsp/AgRg..." detectadas como blockquote Markdown (modo forense apenas). Nova funcao `_JURISPRUDENCE_CITATION_START` em `detect_blockquotes()`.
                                    - - **P8**: Metadados expandidos no frontmatter YAML — `tipo_peca`, `paciente`, `autoridade_coatora`, `processo_origem`, `impetrante`, `pedido_liminar`. Ativado via `extract_metadata=True`.
                                      - - **P9**: `separate_enumerations()` — garante que alineas juridicas (a), b), I —, 1.1) sejam paragrafos separados com linha em branco antes.
                                        - - **M3**: Alineas juridicas (a), I —, 1.1) protegidas de virar headings ### no modo forense.
                                         
                                          - ### Interface Streamlit
                                         
                                          - - Nova opcao: "Detectar citacoes jurisprudenciais como blockquote" (default: on, modo forense).
                                            - - Nova opcao: "Extrair metadados da peca" (default: off).
                                              - - Versao exibida na sidebar: v4.0.
                                               
                                                - ### Testes
                                               
                                                - - 218 testes passando (72 novos desde v3.0).
                                                  - - Cobertura para: preposicoes, linhas protegidas, CNJ, paginacao, alineas, header/footer P10, citacoes P7, metadados P8, enumeracoes P9.
                                                   
                                                    - ---

                                                    ## v3.0

                                                    - Implementacao inicial do conversor juridico.
                                                    - - Modulos: extractors, cleaning, legal_heuristics, pipeline, piece_separator, metadata.
                                                      - - Interface Streamlit com upload, preview, download ZIP.
                                                        - - 146 testes.
