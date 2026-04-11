"""Classificador semântico de callouts para Markdown jurídico.

Substitui o uso indiscriminado de `> [!NOTE] Definição` por classificação
contextual baseada em padrões reconhecíveis. Aplica callouts apenas
quando há sinal forte do tipo de bloco; caso contrário, mantém prosa.

Categorias suportadas:
- [!QUOTE] Legislação (Art./§/inciso)
- [!QUOTE] Jurisprudência (REsp/STF/STJ ementa)
- [!QUOTE] Súmula (Súmula NN do STF/STJ)
- [!QUOTE] Enunciado (CJF/FPPC)
- [!INFO] Definição (consiste em / é definido como / trata-se de)
- [!WARNING] Atenção (Atenção:/Cuidado:/Pegadinha:)
- [!IMPORTANT] (Importante:/Não confundir/Distinção:)
- [!TIP] Questão de concurso (CESPE/FGV/FCC + Correto/Errado)
- [!NOTE] (OBS:/Obs.:/Observação:)
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================
# Padrões de detecção
# ============================================================

# Legislação: começa com Art., § seguido de número, ou padrão de dispositivo
_LEGISLATION_RE = re.compile(
    r'^\s*(?:\*\*)?(?:Art\.?\s+\d+|§\s*\d+|Inciso\s+[IVX]+|Parágrafo\b)',
    re.IGNORECASE,
)

# Súmula: "Súmula NN do STF/STJ"
_SUMULA_RE = re.compile(
    r'^\s*(?:\*\*)?S[úu]mula\s+\d+',
    re.IGNORECASE,
)

# Enunciado: "Enunciado NN do CJF" ou "Enunciado NN da Jornada"
_ENUNCIADO_RE = re.compile(
    r'^\s*(?:\*\*)?Enunciado\s+\d+',
    re.IGNORECASE,
)

# Jurisprudência: padrão STF/STJ + número de processo, ou "REsp/RE/HC NNN"
_JURIS_RE = re.compile(
    r'^\s*(?:\*\*)?(?:STF|STJ|TST|TSE|TRF\d?|TJ[A-Z]{2})\s*\.?\s*'
    r'(?:\d+ª\s*(?:Turma|Seção)|REsp|HC|RE|MS|AgRg)',
    re.IGNORECASE,
)

# Questão de concurso: banca conhecida + ano
_QUESTAO_RE = re.compile(
    r'\((?:CESPE|CEBRASPE|FGV|FCC|VUNESP|FUNDATEC|IBFC|IADES|MPE|MPT|'
    r'TRF|TRT|TJ|FUMARC|CONSULPLAN|FUNCAB|UFRGS|FUNDEP)[\s/\-—]',
    re.IGNORECASE,
)

# Definição: "X consiste em", "X é definido como", "trata-se de", "entende-se por"
_DEFINICAO_RE = re.compile(
    r'\b(?:consiste\s+em|é\s+definid[oa]\s+como|trata[-\s]se\s+de|'
    r'entende[-\s]se\s+por|conceitua[-\s]se|define[-\s]se\s+como|'
    r'pode\s+ser\s+definid[oa]\s+como)\b',
    re.IGNORECASE,
)

# Atenção/Cuidado
_WARNING_RE = re.compile(
    r'^\s*(?:\*\*)?(?:Aten[çc][ãa]o|Cuidado|Pegadinha|CUIDADO|ATEN[ÇC][ÃA]O)\s*[:!]',
    re.IGNORECASE,
)

# Importante / Distinção
_IMPORTANT_RE = re.compile(
    r'^\s*(?:\*\*)?(?:Importante|N[ãa]o\s+confundir|Distin[çc][ãa]o|'
    r'IMPORTANTE|DISTIN[ÇC][ÃA]O)\s*[:!]',
    re.IGNORECASE,
)

# Observação
_NOTE_RE = re.compile(
    r'^\s*(?:\*\*)?(?:Obs\.?|OBS\.?|Observa[çc][ãa]o)\s*[:!]',
    re.IGNORECASE,
)


def classify_block(text: str) -> str | None:
    """Classifica um bloco textual e retorna o tipo de callout apropriado.

    Args:
        text: bloco de texto (parágrafo único)

    Returns:
        Header do callout (ex: '> [!QUOTE] Legislação') ou None se prosa.
    """
    stripped = text.strip()
    if not stripped:
        return None

    # Ordem importa — padrões mais específicos primeiro
    if _LEGISLATION_RE.match(stripped):
        return "> [!QUOTE] Legislação"
    if _SUMULA_RE.match(stripped):
        return "> [!QUOTE] Súmula"
    if _ENUNCIADO_RE.match(stripped):
        return "> [!QUOTE] Enunciado"
    if _JURIS_RE.match(stripped):
        return "> [!QUOTE] Jurisprudência"
    if _QUESTAO_RE.search(stripped):
        return "> [!TIP] Questão de concurso"
    if _WARNING_RE.match(stripped):
        return "> [!WARNING] Atenção"
    if _IMPORTANT_RE.match(stripped):
        return "> [!IMPORTANT]"
    if _NOTE_RE.match(stripped):
        return "> [!NOTE]"
    if _DEFINICAO_RE.search(stripped) and len(stripped) < 400:
        return "> [!INFO] Definição"
    return None


def apply_smart_callouts(text: str) -> str:
    """Aplica classificação semântica de callouts ao texto.

    Percorre parágrafos e envolve em callout apenas quando o classificador
    retorna um tipo definido. Prosa corrida permanece intacta.
    """
    lines = text.split('\n')
    result = []
    i = 0
    applied = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Pular linhas já em callout, headings, tabelas, listas
        if (
            not stripped
            or stripped.startswith('>')
            or stripped.startswith('#')
            or stripped.startswith('|')
            or stripped.startswith('- ')
            or stripped.startswith('* ')
        ):
            result.append(line)
            i += 1
            continue

        # Coletar parágrafo completo (até linha em branco)
        para_lines = [stripped]
        j = i + 1
        while j < len(lines) and lines[j].strip() and not (
            lines[j].strip().startswith('>')
            or lines[j].strip().startswith('#')
            or lines[j].strip().startswith('|')
            or lines[j].strip().startswith('- ')
            or lines[j].strip().startswith('* ')
        ):
            para_lines.append(lines[j].strip())
            j += 1

        full_para = ' '.join(para_lines)
        callout_header = classify_block(full_para)

        if callout_header:
            result.append(callout_header)
            for pl in para_lines:
                result.append(f"> {pl}")
            applied += 1
            i = j
        else:
            for pl in para_lines:
                result.append(pl)
            i = j

    if applied > 0:
        logger.info(
            "callout_classifier: %d callouts semânticos aplicados", applied,
        )
    return '\n'.join(result)
