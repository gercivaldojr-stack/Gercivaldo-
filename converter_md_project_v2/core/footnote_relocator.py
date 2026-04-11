"""Reconciliador de notas de rodapé.

Resolve o defeito de notas de rodapé deslocadas: quando a extração coleta
definições `[^N]: ...` no final do arquivo mas não insere a chamada `[^N]`
no corpo do texto, transforma cada nota órfã em callout `[!NOTE] **Nota:**`
posicionado de forma heurística.

Estratégia:
1. Encontrar bloco de definições `[^N]: ...` no fim do arquivo.
2. Para cada nota: verificar se há chamada `[^N]` no corpo do texto.
3. Se SIM: mantém como está (o pipeline já está correto).
4. Se NÃO: converte a definição em callout `> [!NOTE]` e move para
   logo após o último parágrafo significativo antes do bloco de notas.
"""

import logging
import re

logger = logging.getLogger(__name__)

_FOOTNOTE_DEF_RE = re.compile(
    r'^\[\^(\d+)\]:\s*(.+)$', re.MULTILINE,
)


def _has_inline_reference(text: str, num: str) -> bool:
    """Verifica se o número aparece como [^N] no corpo do texto."""
    pat = re.compile(r'\[\^' + re.escape(num) + r'\](?!:)')
    return bool(pat.search(text))


def relocate_orphan_footnotes(text: str) -> str:
    """Reposiciona notas de rodapé sem chamada inline.

    Converte definições órfãs em callouts e remove do bloco final.
    """
    matches = list(_FOOTNOTE_DEF_RE.finditer(text))
    if not matches:
        return text

    # Separar corpo (antes do primeiro footnote) das definições
    first_def = matches[0].start()
    body = text[:first_def].rstrip()
    footnote_block = text[first_def:]

    orphan_callouts = []
    used_lines = []

    for m in _FOOTNOTE_DEF_RE.finditer(footnote_block):
        num = m.group(1)
        content = m.group(2).strip()

        if _has_inline_reference(body, num):
            # Tem referência inline → manter no bloco de footnotes
            used_lines.append(f"[^{num}]: {content}")
        else:
            # Órfã → converter para callout
            orphan_callouts.append(
                f"\n> [!NOTE]\n> **Nota:** {content}\n"
            )
            logger.info(
                "footnote_relocator: nota órfã [^%s] convertida para callout",
                num,
            )

    # Reconstruir texto
    result_parts = [body]
    if orphan_callouts:
        result_parts.extend(orphan_callouts)
    if used_lines:
        result_parts.append("\n\n---\n")
        result_parts.append("\n".join(used_lines))

    return "\n".join(result_parts).rstrip() + "\n"
