"""Remoção seletiva de conteúdo para saída limpa otimizada para RAG.

Três funções independentes, cada uma ativável por flag booleana:

1. strip_footnotes: remove todas as notas de rodapé
2. strip_conversion_artifacts: remove artefatos residuais de conversão
3. strip_reference_blocks: remove seções de referências bibliográficas
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# 1. strip_footnotes
# ============================================================

# Referência inline: [^N] (não seguido de :)
_FOOTNOTE_INLINE_RE = re.compile(r'\[\^\d+\](?!:)')
# Definição: [^N]: ...
_FOOTNOTE_DEF_RE = re.compile(r'^\[\^\d+\]:\s*.*$', re.MULTILINE)
# Callout gerado pelo footnote_relocator: > [!NOTE]\n> **Nota:** ...
_FOOTNOTE_CALLOUT_RE = re.compile(
    r'>\s*\[!NOTE\]\s*\n>\s*\*\*Nota:\*\*\s*.*',
)

# Contextos onde dígitos NÃO são notas de rodapé (falsos positivos)
_NOT_FOOTNOTE_CONTEXT = re.compile(
    r'(?:Art\.?|art\.?|Lei|lei|Decreto|decreto|Resolução|'
    r'Resolu[çc][ãa]o|n[º°.]|N[º°.]|p\.|P[áa]g\.?|'
    r'§|Súmula|S[úu]mula|Enunciado|[Ii]nciso)\s*$'
)


def _remove_inline_footnote_numbers(text: str) -> str:
    """Remove dígitos de rodapé colados ao texto.

    Ex: "outrem.1" → "outrem.", "Haftung3" → "Haftung"
    Não remove: "Art. 123", "Lei 8.666", "§ 1º", anos (2024),
    datas em frontmatter YAML ("data: \"4 de Novembro\"").
    """
    lines = text.split('\n')
    result = []
    in_frontmatter = False
    _yaml_key_re = re.compile(
        r'^(?:titulo|data|status|convertido_em|proad|orgao_emissor|'
        r'tipo_peca|paciente|autor|reu|impetrante|autoridade_coatora|'
        r'pedido_liminar|processo_origem|comarca|acoes_cumuladas|'
        r'area|subarea|tags|ultima_revisao|edicao|fonte|tipo|ramo|'
        r'subramos|jurisdicao|atualizado_ate|formato_origem)\s*:',
        re.IGNORECASE,
    )
    for idx, line in enumerate(lines):
        # Toggle frontmatter state on --- markers
        if line.strip() == '---':
            if idx == 0 or in_frontmatter:
                in_frontmatter = not in_frontmatter
            result.append(line)
            continue

        # Pular linhas em frontmatter YAML
        if in_frontmatter or _yaml_key_re.match(line.strip()):
            result.append(line)
            continue

        # Pular headings e linhas de tabela
        if line.strip().startswith(('#', '|')):
            result.append(line)
            continue

        def _replace(m):
            start = m.start()
            end = m.end()
            # Pegar os 15 chars antes do match para verificar contexto
            ctx = line[max(0, start - 15):start]
            if _NOT_FOOTNOTE_CONTEXT.search(ctx):
                return m.group(0)  # Manter — é referência legal
            # Verificar se o dígito é parte de uma data "N de <mês>"
            ctx_after = line[end:end + 25]
            if re.match(
                r'\s+de\s+(?:janeiro|fevereiro|março|abril|maio|'
                r'junho|julho|agosto|setembro|outubro|novembro|'
                r'dezembro)',
                ctx_after, re.IGNORECASE,
            ):
                return m.group(0)  # Manter — é dia de data
            return ''

        # Padrão 1: 1-2 dígitos colados após letra/pontuação (sem espaço)
        new_line = re.sub(
            r'(?<=[a-záéíóúàâêôãõç.,:;!?\)\]"\u201d])'
            r'\d{1,2}'
            r'(?=[\s.,;:!?\)\]\n]|$)',
            _replace,
            line,
        )

        # Padrão 2: dígito ISOLADO entre palavras (footnote com espaço)
        # Ex: "publicização 1 previsto" → "publicização previsto"
        # Protege contra Art. 1, Lei 8.666, ano 2024, etc. via contexto
        def _replace_isolated(m):
            start = m.start()
            ctx_before = new_line[max(0, start - 20):start]
            if _NOT_FOOTNOTE_CONTEXT.search(ctx_before):
                return m.group(0)
            # Verificar se é data: "N de <mês>"
            end = m.end()
            ctx_after = new_line[end:end + 25]
            if re.match(
                r'\s*(?:,|e|ou|a)\s*\d',
                ctx_after,
            ):
                return m.group(0)  # "1 e 2", "1, 2" — enumeração
            if re.match(
                r'\s+de\s+(?:janeiro|fevereiro|março|abril|maio|'
                r'junho|julho|agosto|setembro|outubro|novembro|'
                r'dezembro)',
                ctx_after, re.IGNORECASE,
            ):
                return m.group(0)
            # Substituir dígito por nada, preservando 1 espaço
            return ' '

        new_line = re.sub(
            r'(?<=[a-záéíóúàâêôãõç])\s+(\d{1,2})\s+(?=[a-záéíóúàâêôãõç])',
            _replace_isolated,
            new_line,
        )
        # Limpar espaços duplos resultantes
        new_line = re.sub(r'  +', ' ', new_line)
        result.append(new_line)
    return '\n'.join(result)


def strip_footnotes(text: str) -> str:
    """Remove TODAS as notas de rodapé do Markdown.

    Remove:
    - Números de rodapé inline colados ao texto (ex: "outrem.1" → "outrem.")
    - Refs inline [^N] no corpo
    - Definições [^N]: ... no final
    - Callouts > [!NOTE] **Nota:** gerados pelo relocator
    - Separadores --- que ficam antes do bloco de definições
    """
    # Remover callouts de nota
    text = _FOOTNOTE_CALLOUT_RE.sub('', text)
    # Remover refs inline [^N]
    text = _FOOTNOTE_INLINE_RE.sub('', text)
    # Remover definições [^N]: ...
    text = _FOOTNOTE_DEF_RE.sub('', text)
    # Remover números de rodapé colados ao texto
    text = _remove_inline_footnote_numbers(text)
    # Remover separador --- órfão no final (de bloco de footnotes)
    text = re.sub(r'\n---\s*\n*$', '\n', text)
    # Limpar espaços duplos e linhas extras
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    logger.debug("strip_footnotes: notas removidas")
    return text


# ============================================================
# 2. strip_conversion_artifacts
# ============================================================

_ARTIFACT_PATTERNS = [
    # Números de página isolados (linha só com dígitos)
    re.compile(r'^\s*\d{1,4}\s*$', re.MULTILINE),
    # Marcador "--- Página X ---"
    re.compile(
        r'^\s*[-–—]+\s*P[áa]gina\s*\d+\s*[-–—]+\s*$',
        re.IGNORECASE | re.MULTILINE,
    ),
    # Cabeçalhos de caderno: "CS – DISCIPLINA I YYYY.S | NN"
    re.compile(
        r'^\s*\|?\s*CS\s*[–\-—]\s*[A-ZÀ-Ú][A-ZÀ-Ú\s]+'
        r'\s+[IVX]+\s+\d{4}\.\d\s*\|?\s*\d*\s*\|?\s*$',
        re.MULTILINE,
    ),
    # Blocos *Resumo: ... Palavras-chave: ...*
    re.compile(
        r'\*Resumo[:.]?\s.*?Palavras[-\s]chave[:.]?\s.*?\*',
        re.IGNORECASE | re.DOTALL,
    ),
    # Linhas com apenas pipes/traços de tabelas quebradas
    re.compile(r'^\s*\|[\s|]*\|\s*$', re.MULTILINE),
    re.compile(r'^\s*\|[-\s:]+\|\s*$', re.MULTILINE),
    # "Página N" ou "Pág. N" isolados
    re.compile(
        r'^\s*P[áa]g(?:ina|\.)\s*\d+\s*$',
        re.IGNORECASE | re.MULTILINE,
    ),
    # "— N —" (número de página com travessões)
    re.compile(r'^\s*[-–—]\s*\d+\s*[-–—]\s*$', re.MULTILINE),
]


def strip_conversion_artifacts(text: str) -> str:
    """Remove TODOS os artefatos remanescentes de conversão PDF/DOCX."""
    for pat in _ARTIFACT_PATTERNS:
        text = pat.sub('', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    logger.debug("strip_conversion_artifacts: artefatos removidos")
    return text


# ============================================================
# 3. strip_reference_blocks
# ============================================================

# ============================================================
# Referências bibliográficas inline (P2): blocos "SOBRENOME, Nome. [...]. Acesso em:"
# ============================================================

_INLINE_BIBLIO_RE = re.compile(
    r'^[A-ZÀ-Ú]{2,}[A-ZÀ-Ú\s]*,\s+[A-ZÀ-Ú][^\n]*'
    r'(?:Acesso\s+em[:.]|Dispon[íi]vel\s+em[:.])'
    r'[^\n]*\.?',
    re.IGNORECASE | re.MULTILINE,
)


def strip_inline_biblio_references(text: str) -> str:
    """Remove blocos de referência bibliográfica no corpo do texto.

    Padrão: "SOBRENOME, Nome. [...]. Disponível em: [...]. Acesso em: [...]."
    Comum em artigos do JusBrasil e citações acadêmicas.
    """
    return _INLINE_BIBLIO_RE.sub('', text)


# ============================================================
# URLs malformadas (P7)
# ============================================================

def fix_malformed_urls(text: str) -> str:
    """Corrige URLs sem protocolo: 'httpswww' → 'https://www.'."""
    text = re.sub(r'\bhttpswww\.', 'https://www.', text)
    text = re.sub(r'\bhttpwww\.', 'http://www.', text)
    return text


# ============================================================
# Textos de UI/navegação (P8)
# ============================================================

_UI_TEXT_PATTERNS = [
    re.compile(r'^\s*Clique\s+aqui\s+e\s+acesse.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Clique\s+aqui\s+para.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Saiba\s+mais\s+em.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Veja\s+também[:.]?.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Compartilhe.*$', re.IGNORECASE | re.MULTILINE),
    re.compile(r'^\s*Imprimir.*$', re.IGNORECASE | re.MULTILINE),
]


def strip_ui_text(text: str) -> str:
    """Remove textos de navegação/UI comuns em doutrina digital."""
    for pat in _UI_TEXT_PATTERNS:
        text = pat.sub('', text)
    return text


_REF_HEADING_RE = re.compile(
    r'^(#{1,6})\s+'
    r'(?:Refer[êe]ncias?\s*(?:Bibliogr[áa]ficas?|[Cc]itadas?)?|'
    r'Bibliografia|'
    r'Obras\s+Consultadas|'
    r'Leitura\s+Complementar|'
    r'Leituras?\s+Recomendadas?|'
    r'Notas?\s+(?:Bibliogr[áa]ficas?|de\s+Refer[êe]ncia)|'
    r'Fontes?\s*(?:Consultadas|Bibliogr[áa]ficas?)?)'
    r'\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def strip_reference_blocks(text: str) -> str:
    """Remove seções inteiras de referências bibliográficas.

    Detecta headings como 'Referências', 'Bibliografia',
    'Obras Consultadas', etc. e remove tudo até o próximo
    heading de mesmo nível ou fim do arquivo.
    """
    lines = text.split('\n')
    result = []
    skip_until_level = 0
    skipping = False

    for line in lines:
        if skipping:
            m = re.match(r'^(#{1,6})\s+', line)
            if m and len(m.group(1)) <= skip_until_level:
                skipping = False
                result.append(line)
            continue

        m_ref = _REF_HEADING_RE.match(line)
        if m_ref:
            skip_until_level = len(m_ref.group(1))
            skipping = True
            logger.debug(
                "strip_reference_blocks: removendo seção '%s'",
                line.strip()[:60],
            )
            continue

        result.append(line)

    # Detectar bloco bibliográfico sem heading no final:
    # 3+ linhas com padrão SOBRENOME, Nome. Título... YYYY
    _biblio_line = re.compile(
        r'^[A-ZÀ-Ú]{2,}[A-ZÀ-Úa-záéíóúàâêôãõç\s,]+\.\s+.*\d{4}',
    )
    final_lines = list(result)
    if len(final_lines) > 5:
        # Scan forward: find first biblio line cluster at the end
        biblio_start = -1
        biblio_count = 0
        for idx in range(len(final_lines)):
            stripped = final_lines[idx].strip()
            if _biblio_line.match(stripped):
                if biblio_start == -1:
                    biblio_start = idx
                biblio_count += 1
            elif stripped and stripped.startswith('#'):
                biblio_start = -1
                biblio_count = 0
            elif stripped:
                # Non-biblio non-blank content resets if before 3
                if biblio_count < 3:
                    biblio_start = -1
                    biblio_count = 0

        if biblio_count >= 3 and biblio_start >= 0:
            logger.debug(
                "strip_reference_blocks: bloco bibliográfico sem heading"
                " detectado na linha %d (%d refs)",
                biblio_start, biblio_count,
            )
            result = final_lines[:biblio_start]

    text = '\n'.join(result)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text
