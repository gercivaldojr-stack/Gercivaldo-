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


def strip_footnotes(text: str) -> str:
    """Remove TODAS as notas de rodapé do Markdown.

    Remove:
    - Refs inline [^N] no corpo
    - Definições [^N]: ... no final
    - Callouts > [!NOTE] **Nota:** gerados pelo relocator
    - Separadores --- que ficam antes do bloco de definições
    """
    # Remover callouts de nota
    text = _FOOTNOTE_CALLOUT_RE.sub('', text)
    # Remover refs inline
    text = _FOOTNOTE_INLINE_RE.sub('', text)
    # Remover definições
    text = _FOOTNOTE_DEF_RE.sub('', text)
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

_REF_HEADING_RE = re.compile(
    r'^(#{1,6})\s+'
    r'(?:Refer[êe]ncias?\s*(?:Bibliogr[áa]ficas?)?|'
    r'Bibliografia|'
    r'Obras\s+Consultadas|'
    r'Leitura\s+Complementar|'
    r'Leituras?\s+Recomendadas?|'
    r'Notas\s+Bibliogr[áa]ficas?|'
    r'Fontes\s+Consultadas)'
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

    text = '\n'.join(result)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text
