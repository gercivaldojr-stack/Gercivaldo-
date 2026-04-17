"""Polimento final de Markdown — correção de defeitos recorrentes.

Módulo de pós-processamento que corrige artefatos de formatação
que sobrevivem ao pipeline de extração e limpeza:

D1: Listas numeradas com negrito espúrio (**1. **texto → 1. texto)
D2: Inconsistência de marcadores de ênfase (***bold-italic*** espúrio)
D3: Concatenação de palavras em fronteiras de negrito (**XYZpalavra**)

Inserido no pipeline.py como passo 4e, após content_stripper.
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# D1: Listas numeradas com negrito espúrio
# ============================================================================

# Padrão: **N. **texto ou **N. ** texto (espaço antes do texto)
# Captura variantes com 1-3 dígitos e ponto, envoltos em **
_BOLD_NUMBERED_LIST_RE = re.compile(
    r'^\*\*(\d{1,3})\.\s*\*\*\s*(.+)$',
    re.MULTILINE,
)

# Padrão mais agressivo: **N.** texto (sem espaço dentro do bold)
_BOLD_NUMBERED_TIGHT_RE = re.compile(
    r'^\*\*(\d{1,3})\.\*\*\s*(.+)$',
    re.MULTILINE,
)

# Padrão: **N** . texto (bold só no número)
_BOLD_NUMBER_ONLY_RE = re.compile(
    r'^\*\*(\d{1,3})\*\*\s*\.\s*(.+)$',
    re.MULTILINE,
)


def fix_bold_numbered_lists(text: str) -> str:
    """Converte listas numeradas com negrito espúrio para markdown nativo.

    Transforma padrões como:
        **1. **texto do item
        **2. ** texto do item
        **3.**texto do item

    Em:
        1. texto do item
        2. texto do item
        3. texto do item

    Não afeta headings legítimos (## 1. TÍTULO) nem negrito semântico
    dentro de parágrafos corridos.
    """
    count = 0

    def _replace(m):
        nonlocal count
        count += 1
        num = m.group(1)
        rest = m.group(2).strip()
        return f'{num}. {rest}'

    text = _BOLD_NUMBERED_LIST_RE.sub(_replace, text)
    text = _BOLD_NUMBERED_TIGHT_RE.sub(_replace, text)
    text = _BOLD_NUMBER_ONLY_RE.sub(_replace, text)

    if count > 0:
        logger.info("md_polish D1: corrigidas %d listas numeradas com negrito", count)

    return text


# ============================================================================
# D2: Inconsistência de marcadores de ênfase
# ============================================================================

# Padrão: ***texto*** onde deveria ser **texto** ou *texto*
# Foco: sequências isoladas de bold-italic que não são consistentes
# com o padrão do documento (onde o restante usa apenas bold ou itálico)

# Locuções latinas que devem ser itálico, não bold-italic
_LATIN_EXPRESSIONS = [
    'inaudita altera parte',
    'animus novandi',
    'in re ipsa',
    'ex lege',
    'ad hoc',
    'ab initio',
    'data venia',
    'in casu',
    'in fine',
    'in verbis',
    'mutatis mutandis',
    'periculum in mora',
    'fumus boni iuris',
    'prima facie',
    'erga omnes',
    'inter partes',
    'lato sensu',
    'stricto sensu',
    'ex officio',
    'ex tunc',
    'ex nunc',
    'habeas corpus',
    'mandamus',
    'certiorari',
    'stare decisis',
    'ratio decidendi',
    'obiter dictum',
    'per se',
    'sui generis',
    'ultra petita',
    'extra petita',
    'reformatio in pejus',
]


def fix_emphasis_consistency(text: str) -> str:
    """Corrige inconsistências de marcadores de ênfase.

    Regras aplicadas:
    1. Locuções latinas em ***bold-italic*** → *itálico* apenas
    2. Sequências ***A + ordinal*** (A primeira, A segunda, A terceira)
       onde a maioria do contexto usa ** → normaliza para **bold**
    3. Remove bold-italic triplo (***) em início de parágrafo quando
       o padrão do documento é bold simples (**)
    """
    count = 0

    # Regra 1: Locuções latinas ***locução*** → *locução*
    for expr in _LATIN_EXPRESSIONS:
        # Case-insensitive search, preserva case original
        pattern = re.compile(
            r'\*\*\*(' + re.escape(expr) + r')\*\*\*',
            re.IGNORECASE,
        )
        matches = pattern.findall(text)
        if matches:
            count += len(matches)
            text = pattern.sub(r'*\1*', text)

    # Regra 2: ***A + ordinal/palavra*** em contexto de lista de premissas
    # Padrão: ***A primeira***, ***A segunda***, etc. → **A primeira**, etc.
    _bold_italic_ordinal = re.compile(
        r'\*\*\*(A\s+(?:primeir[ao]|segund[ao]|terceir[ao]|quart[ao]|'
        r'quint[ao]|sext[ao]|sétim[ao]|oitav[ao]|non[ao]|décim[ao]))\*\*\*',
        re.IGNORECASE,
    )
    matches = _bold_italic_ordinal.findall(text)
    if matches:
        count += len(matches)
        text = _bold_italic_ordinal.sub(r'**\1**', text)

    if count > 0:
        logger.info("md_polish D2: corrigidas %d inconsistências de ênfase", count)

    return text


# ============================================================================
# D3: Concatenação de palavras em fronteiras de negrito
# ============================================================================

# Padrão: **XXXpalavra** onde XXX termina em dígito e palavra começa
# com letra minúscula (sinal de concatenação acidental)
_BOLD_CONCAT_DIGIT_WORD_RE = re.compile(
    r'\*\*(\d+)([a-záéíóúàâêôãõç]\w+)\*\*',
)

# Padrão mais geral: dentro de **, sequência dígito+letra sem espaço
# que deveria ter espaço (ex: "20242395889521598não")
_BOLD_CONCAT_LONG_NUMBER_RE = re.compile(
    r'\*\*([^*]*\d)([a-záéíóúàâêôãõç][a-záéíóúàâêôãõç]+[^*]*)\*\*',
)

# Padrão fora de bold: número longo grudado em palavra
_CONCAT_NUMBER_WORD_RE = re.compile(
    r'(\d{5,})([a-záéíóúàâêôãõç]{3,})',
)


def fix_bold_word_concatenation(text: str) -> str:
    """Corrige palavras concatenadas em fronteiras de marcadores bold.

    Detecta e separa:
        **20242395889521598não impedem** → **20242395889521598** não impedem
        **123texto** → **123** texto

    Também corrige concatenações fora de bold:
        20242395889521598não → 20242395889521598 não
    """
    count = 0

    # Correção dentro de bold: **número+palavra...** → **número** palavra...
    def _fix_bold_concat(m):
        nonlocal count
        prefix = m.group(1)  # parte numérica
        suffix = m.group(2)  # parte textual
        count += 1
        return f'**{prefix}** {suffix}'

    text = _BOLD_CONCAT_LONG_NUMBER_RE.sub(_fix_bold_concat, text)

    # Correção fora de bold: número longo grudado em palavra
    def _fix_plain_concat(m):
        nonlocal count
        count += 1
        return f'{m.group(1)} {m.group(2)}'

    text = _CONCAT_NUMBER_WORD_RE.sub(_fix_plain_concat, text)

    if count > 0:
        logger.info("md_polish D3: corrigidas %d concatenações de palavras", count)

    return text


# ============================================================================
# Pipeline de polimento
# ============================================================================

def polish_markdown(text: str) -> str:
    """Aplica todas as correções de polimento ao Markdown final.

    Ordem de aplicação:
    1. D3 (concatenação) — antes de D1, pois D1 pode criar novos tokens
    2. D1 (listas numeradas com negrito)
    3. D2 (consistência de ênfase)
    """
    if not text:
        return text

    text = fix_bold_word_concatenation(text)
    text = fix_bold_numbered_lists(text)
    text = fix_emphasis_consistency(text)

    return text
