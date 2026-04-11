"""Limpador de artefatos pós-conversão.

Remove padrões espúrios deixados pelo pipeline de extração e otimização:
- Blocos de "Resumo: ... Palavras-chave: ..." gerados pelo rag_optimizer
- Cabeçalhos/rodapés de página residuais (CS – CIVIL I 2025.2 | 42)
- Linhas com apenas número de página
- Blocos `*Resumo:*` órfãos no corpo

Aplicado como passo final antes da gravação do .md.
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# Padrões de metadados espúrios
# ============================================================

# Bloco *Resumo: ... Palavras-chave: ...* gerado pelo rag_optimizer
_RESUMO_PALAVRASCHAVE_RE = re.compile(
    r'\*Resumo[:.]?\s.*?Palavras[-\s]chave[:.]?\s.*?\*',
    re.IGNORECASE | re.DOTALL,
)

# Bloco *Resumo: ...* sem palavras-chave (versão curta)
_RESUMO_SOLO_RE = re.compile(
    r'^\s*\*Resumo[:.]?\s.*?\*\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def remove_spurious_metadata(text: str) -> int:
    """Remove blocos `*Resumo: ... Palavras-chave: ...*` do corpo.

    Esses blocos são gerados pelo rag_optimizer.generate_section_summaries
    e poluem o texto quando o conteúdo deveria fluir como prosa.

    Returns: número de blocos removidos.
    """
    count = 0
    matches = _RESUMO_PALAVRASCHAVE_RE.findall(text)
    count += len(matches)
    text_out = _RESUMO_PALAVRASCHAVE_RE.sub('', text)

    solo_matches = _RESUMO_SOLO_RE.findall(text_out)
    count += len(solo_matches)
    text_out = _RESUMO_SOLO_RE.sub('', text_out)

    if count > 0:
        logger.info("artifact_cleaner: removidos %d blocos *Resumo:*", count)
    return count, text_out


def clean_artifacts(text: str) -> str:
    """Pipeline completo de limpeza de artefatos.

    Aplica todas as remoções e retorna texto limpo.
    """
    _, text = remove_spurious_metadata(text)

    # Normalizar excesso de linhas em branco resultante das remoções
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text
