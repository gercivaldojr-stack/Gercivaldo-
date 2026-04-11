"""Otimização semântica de Markdown jurídico para bases RAG.

Passo pós-processamento opt-in que enriquece o Markdown com:
- Classificação de área/subárea jurídica
- Tags automáticas por frequência de termos
- Formatação semântica (latim itálico, conceitos negrito, doutrinadores)
- Callouts Obsidian/GitHub para definições e alertas
- Resumos heurísticos por seção
- Notas de rodapé normalizadas
"""

import re
import logging
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================
# 1. detect_legal_area
# ============================================================

_AREA_PATTERNS = {
    "Direito Penal": {
        "keywords": re.compile(
            r'\b(?:crime|delito|pena|reclusão|detenção|tipicidade|'
            r'antijuridicidade|culpabilidade|dolo|culpa|imputabilidade|'
            r'código\s+penal|CP\b|homicídio|furto|roubo|estelionato|'
            r'lesão\s+corporal|ação\s+penal)\b', re.IGNORECASE,
        ),
        "subareas": {
            "Crimes contra a pessoa": re.compile(
                r'\b(?:homicídio|lesão\s+corporal|ameaça|'
                r'constrangimento|sequestro|cárcere)\b', re.IGNORECASE,
            ),
            "Crimes contra o patrimônio": re.compile(
                r'\b(?:furto|roubo|extorsão|estelionato|'
                r'receptação|dano|apropriação)\b', re.IGNORECASE,
            ),
            "Teoria do delito": re.compile(
                r'\b(?:tipicidade|antijuridicidade|culpabilidade|'
                r'imputabilidade|dolo|culpa|nexo\s+causal)\b', re.IGNORECASE,
            ),
        },
    },
    "Direito Constitucional": {
        "keywords": re.compile(
            r'\b(?:constituição|constitucional|direito\s+fundamental|'
            r'garantia|mandado\s+de\s+segurança|habeas\s+corpus|'
            r'ação\s+direta|ADI|ADPF|controle\s+de\s+constitucionalidade|'
            r'cláusula\s+pétrea|emenda\s+constitucional)\b', re.IGNORECASE,
        ),
        "subareas": {
            "Direitos fundamentais": re.compile(
                r'\b(?:direito\s+fundamental|liberdade|igualdade|'
                r'dignidade|direitos?\s+sociais?)\b', re.IGNORECASE,
            ),
            "Controle de constitucionalidade": re.compile(
                r'\b(?:ADI|ADPF|controle\s+(?:difuso|concentrado)|'
                r'ação\s+direta|inconstitucionalidade)\b', re.IGNORECASE,
            ),
        },
    },
    "Direito Processual Civil": {
        "keywords": re.compile(
            r'\b(?:CPC|código\s+de\s+processo\s+civil|citação|'
            r'intimação|contestação|réplica|sentença|acórdão|'
            r'recurso\s+(?:especial|extraordinário|de\s+apelação)|'
            r'tutela\s+(?:antecipada|provisória|de\s+urgência)|'
            r'execução|cumprimento\s+de\s+sentença)\b', re.IGNORECASE,
        ),
        "subareas": {
            "Processo de conhecimento": re.compile(
                r'\b(?:petição\s+inicial|contestação|réplica|'
                r'instrução|sentença|audiência)\b', re.IGNORECASE,
            ),
            "Recursos": re.compile(
                r'\b(?:apelação|agravo|embargo|recurso\s+especial|'
                r'recurso\s+extraordinário)\b', re.IGNORECASE,
            ),
        },
    },
    "Direito do Trabalho": {
        "keywords": re.compile(
            r'\b(?:CLT|trabalhista|empregado|empregador|'
            r'vínculo\s+empregatício|rescisão|FGTS|férias|'
            r'jornada\s+de\s+trabalho|salário|aviso\s+prévio)\b',
            re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Tributário": {
        "keywords": re.compile(
            r'\b(?:tributo|imposto|taxa|contribuição|CTN|'
            r'fato\s+gerador|base\s+de\s+cálculo|alíquota|'
            r'ICMS|ISS|IPTU|IPVA|IR\b|PIS|COFINS)\b', re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Administrativo": {
        "keywords": re.compile(
            r'\b(?:administração\s+pública|ato\s+administrativo|'
            r'licitação|contrato\s+administrativo|servidor\s+público|'
            r'poder\s+de\s+polícia|improbidade|Lei\s+8\.?666|'
            r'concessão|permissão)\b', re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Empresarial": {
        "keywords": re.compile(
            r'\b(?:empresa|sociedade\s+(?:limitada|anônima)|'
            r'falência|recuperação\s+judicial|CNPJ|quotas?|ações?|'
            r'título\s+de\s+crédito|nota\s+promissória)\b', re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Ambiental": {
        "keywords": re.compile(
            r'\b(?:meio\s+ambiente|ambiental|licenciamento|'
            r'poluição|fauna|flora|IBAMA|reserva\s+legal|'
            r'área\s+de\s+proteção)\b', re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Processual Penal": {
        "keywords": re.compile(
            r'\b(?:CPP|código\s+de\s+processo\s+penal|inquérito|'
            r'flagrante|prisão\s+preventiva|denúncia|queixa-crime|'
            r'júri|tribunal\s+do\s+júri)\b', re.IGNORECASE,
        ),
        "subareas": {},
    },
    "Direito Civil": {
        "keywords": re.compile(
            r'\b(?:código\s+civil|pessoa\s+(?:natural|jurídica)|'
            r'capacidade\s+civil|obrigação|contrato|posse|'
            r'propriedade|responsabilidade\s+civil|família|'
            r'sucessão|herança|casamento|divórcio|LINDB|'
            r'prescrição|decadência|negócio\s+jurídico)\b',
            re.IGNORECASE,
        ),
        "subareas": {
            "LINDB / Parte Geral": re.compile(
                r'\b(?:LINDB|Lei\s+de\s+Introdução|pessoa\s+natural|'
                r'capacidade|personalidade|domicílio)\b', re.IGNORECASE,
            ),
            "Obrigações": re.compile(
                r'\b(?:obrigação|devedor|credor|adimplemento|'
                r'inadimplemento|mora|pagamento)\b', re.IGNORECASE,
            ),
            "Contratos": re.compile(
                r'\b(?:contrato|compra\s+e\s+venda|locação|'
                r'doação|mandato|fiança|empreitada)\b', re.IGNORECASE,
            ),
            "Responsabilidade Civil": re.compile(
                r'\b(?:responsabilidade\s+civil|dano\s+(?:moral|material)|'
                r'indenização|culpa|nexo\s+causal)\b', re.IGNORECASE,
            ),
            "Família e Sucessões": re.compile(
                r'\b(?:família|casamento|divórcio|união\s+estável|'
                r'guarda|alimentos|herança|inventário|'
                r'testamento|sucessão)\b', re.IGNORECASE,
            ),
        },
    },
}


def detect_legal_area(text: str) -> tuple[str, str]:
    """Classifica área e subárea jurídica do texto."""
    sample = text[:8000]
    scores = {}
    for area, cfg in _AREA_PATTERNS.items():
        matches = cfg["keywords"].findall(sample)
        scores[area] = len(matches)

    if not scores or max(scores.values()) == 0:
        return ("Direito Civil", "Geral")

    best_area = max(scores, key=scores.get)
    cfg = _AREA_PATTERNS[best_area]
    sub_scores = {}
    for sub, pat in cfg.get("subareas", {}).items():
        sub_scores[sub] = len(pat.findall(sample))

    best_sub = "Geral"
    if sub_scores and max(sub_scores.values()) > 0:
        best_sub = max(sub_scores, key=sub_scores.get)

    return (best_area, best_sub)


# ============================================================
# 2. extract_tags
# ============================================================

_STOPWORDS = {
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "que", "se", "um", "uma", "ao", "aos",
    "ou", "não", "mais", "sua", "seu", "pela", "pelo", "como",
    "este", "esta", "esse", "essa", "são", "foi", "será", "pode",
    "deve", "tem", "ter", "ser", "está", "há", "já", "entre",
    "sobre", "quando", "também", "muito", "bem", "até", "sem",
    "isso", "isto", "todo", "toda", "ainda", "então", "mas",
    "artigo", "art", "parágrafo", "inciso", "alínea", "caput",
    "texto", "forma", "caso", "modo", "parte", "acordo", "lei",
    "direito", "tribunal", "juiz", "sentença",
}


def extract_tags(text: str, max_tags: int = 5) -> list[str]:
    """Extrai palavras-chave jurídicas por frequência."""
    words = re.findall(r'[a-záéíóúàâêôãõç]{4,}', text.lower())
    filtered = [w for w in words if w not in _STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(max_tags)]


# ============================================================
# 3. apply_semantic_formatting
# ============================================================

_LATIN_TERMS = [
    "vacatio legis", "norma agendi", "jus cogens", "habeas corpus",
    "habeas data", "ad hoc", "in dubio pro reo", "pacta sunt servanda",
    "erga omnes", "inter partes", "ex tunc", "ex nunc", "ab initio",
    "a priori", "a posteriori", "de facto", "de jure", "in limine",
    "fumus boni juris", "periculum in mora", "res judicata",
    "modus operandi", "stare decisis", "lex specialis",
    "lex posterior", "ultra petita", "extra petita", "citra petita",
    "animus necandi", "animus domini", "lato sensu", "stricto sensu",
    "ad quem", "a quo", "prima facie", "mutatis mutandis",
    "data venia", "sine qua non", "numerus clausus",
    "nulla poena sine lege", "nullum crimen sine lege",
]

_LATIN_RE = re.compile(
    r'(?<!\*)\b(' + '|'.join(re.escape(t) for t in _LATIN_TERMS) + r')\b(?!\*)',
    re.IGNORECASE,
)

_LEGAL_CONCEPTS = [
    "pessoa jurídica", "pessoa natural", "capacidade civil",
    "prescrição", "decadência", "responsabilidade civil",
    "ato jurídico", "negócio jurídico", "fato jurídico",
    "obrigação", "contrato", "posse", "propriedade",
    "boa-fé", "função social", "dignidade da pessoa humana",
    "devido processo legal", "contraditório", "ampla defesa",
    "segurança jurídica", "coisa julgada", "ato administrativo",
    "poder de polícia", "serviço público", "licitação",
    "dano moral", "dano material", "nexo causal",
    "tutela antecipada", "tutela provisória",
]

_DOCTRINATORS = [
    "PONTES DE MIRANDA", "MIGUEL REALE", "CLÓVIS BEVILÁQUA",
    "CAIO MÁRIO", "ORLANDO GOMES", "SILVIO RODRIGUES",
    "MARIA HELENA DINIZ", "FLÁVIO TARTUCE", "PABLO STOLZE",
    "RODOLFO PAMPLONA", "NELSON NERY", "HUMBERTO THEODORO",
    "CÂNDIDO RANGEL DINAMARCO", "FREDIE DIDIER", "DANIEL AMORIM",
    "GUILHERME DE SOUZA NUCCI", "ROGÉRIO GRECO", "FERNANDO CAPEZ",
    "LUIZ FLÁVIO GOMES", "CELSO ANTÔNIO BANDEIRA DE MELLO",
]

_TRIBUNALS_RE = re.compile(
    r'\b(STF|STJ|TST|TSE|STM|TRF\d?|TJ[A-Z]{2}|TJSP|TJRJ|TJMG|'
    r'TJRS|TJPR|TJSC|TJBA|TJPE|TJCE|TJGO|TJDF)\b'
)


def apply_semantic_formatting(text: str) -> str:
    """Aplica formatação semântica: latim, conceitos, doutrinadores."""
    lines = text.split("\n")
    result = []
    bolded_concepts: set[str] = set()

    for line in lines:
        # Não formatar headings
        if line.strip().startswith("#"):
            result.append(line)
            continue

        # a) Itálico em expressões latinas
        line = _LATIN_RE.sub(r'*\1*', line)

        # b) Negrito na PRIMEIRA ocorrência de conceitos
        for concept in _LEGAL_CONCEPTS:
            if concept in bolded_concepts:
                continue
            pat = re.compile(
                r'(?<!\*)\b(' + re.escape(concept) + r')\b(?!\*)',
                re.IGNORECASE,
            )
            if pat.search(line):
                line = pat.sub(r'**\1**', line, count=1)
                bolded_concepts.add(concept)

        # c) CAIXA ALTA + negrito em tribunais
        line = _TRIBUNALS_RE.sub(r'**\1**', line)

        # c) Doutrinadores — detectar variações e padronizar
        for name in _DOCTRINATORS:
            pat = re.compile(
                r'(?<!\*)\b(' + re.escape(name) + r')\b(?!\*)',
                re.IGNORECASE,
            )
            line = pat.sub(lambda m: f'**{m.group(1).upper()}**', line)

        result.append(line)

    return "\n".join(result)


# ============================================================
# 4. insert_callouts
# ============================================================

_DEFINITION_RE = re.compile(
    r'^(.+?)\s+(?:é|são|consiste|define-se\s+como|'
    r'entende-se\s+por|conceito\s+de)\s+',
    re.IGNORECASE,
)

_ALERT_RE = re.compile(
    r'^(?:ATENÇÃO|Atenção|Cuidado|CUIDADO|Importante|IMPORTANTE|'
    r'Não\s+confundir|Distinção|DISTINÇÃO|Observação|OBSERVAÇÃO)\s*[:\-–—]?\s*',
    re.IGNORECASE,
)


def insert_callouts(text: str) -> str:
    """Insere callouts Obsidian/GitHub para definições e alertas."""
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("#") or stripped.startswith(">"):
            result.append(line)
            i += 1
            continue

        # Alertas
        if _ALERT_RE.match(stripped):
            result.append("> [!IMPORTANT]")
            result.append(f"> {stripped}")
            i += 1
            continue

        # Definições
        if (
            _DEFINITION_RE.match(stripped)
            and len(stripped) > 30
            and len(stripped) < 300
        ):
            result.append("> [!NOTE] Definição")
            result.append(f"> {stripped}")
            i += 1
            continue

        result.append(line)
        i += 1

    return "\n".join(result)


# ============================================================
# 5. generate_section_summaries
# ============================================================

def generate_section_summaries(text: str) -> str:
    """Gera resumos heurísticos por seção ##."""
    lines = text.split("\n")
    sections: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        if line.strip().startswith("## "):
            sections.append((idx, line.strip()[3:]))

    if len(sections) < 2:
        return text

    result = list(lines)
    offset = 0

    for sec_idx, (start, title) in enumerate(sections):
        if sec_idx + 1 < len(sections):
            end = sections[sec_idx + 1][0]
        else:
            end = len(lines)

        body_lines = [
            lines[j].strip() for j in range(start + 1, end)
            if lines[j].strip()
            and not lines[j].strip().startswith("#")
            and not lines[j].strip().startswith(">")
        ]

        if not body_lines:
            continue

        first_sentence = body_lines[0]
        dot = first_sentence.find(".")
        if dot > 20:
            first_sentence = first_sentence[:dot + 1]
        elif len(first_sentence) > 120:
            first_sentence = first_sentence[:120] + "..."

        words = re.findall(
            r'[a-záéíóúàâêôãõç]{5,}',
            " ".join(body_lines[:10]).lower(),
        )
        kw = [
            w for w, _ in Counter(words).most_common(5)
            if w not in _STOPWORDS
        ][:3]

        kw_str = ", ".join(kw) if kw else ""
        summary = f"*Resumo: {first_sentence}"
        if kw_str:
            summary += f" Palavras-chave: {kw_str}."
        summary += "*"

        insert_pos = end + offset
        result.insert(insert_pos, "")
        result.insert(insert_pos + 1, summary)
        offset += 2

    return "\n".join(result)


# ============================================================
# 6. normalize_footnotes
# ============================================================

_FOOTNOTE_INLINE_RE = re.compile(r'\((\d{1,3})\)')
_FOOTNOTE_DEF_RE = re.compile(r'^(\d{1,3})\s*[.)\-–—]\s*(.+)')


def normalize_footnotes(text: str) -> str:
    """Converte notas numéricas para Markdown footnotes."""
    lines = text.split("\n")
    definitions: dict[str, str] = {}
    result_lines = []

    for line in lines:
        stripped = line.strip()
        m = _FOOTNOTE_DEF_RE.match(stripped)
        if m and len(stripped) > 20:
            num = m.group(1)
            content = m.group(2).strip()
            definitions[num] = content
            continue
        result_lines.append(line)

    result_text = "\n".join(result_lines)
    used_footnotes: set[str] = set()

    def _replace_inline(m):
        num = m.group(1)
        used_footnotes.add(num)
        return f"[^{num}]"

    result_text = _FOOTNOTE_INLINE_RE.sub(_replace_inline, result_text)

    if definitions:
        footnote_lines = ["\n\n---\n"]
        for num in sorted(definitions.keys(), key=int):
            if num in used_footnotes or num in definitions:
                footnote_lines.append(
                    f"[^{num}]: {definitions[num]}"
                )
        result_text += "\n".join(footnote_lines)

    return result_text


# ============================================================
# 7. optimize_for_rag (orquestrador)
# ============================================================

def optimize_for_rag(text: str, filename: str = "") -> str:
    """Orquestra todas as otimizações RAG na ordem correta.

    Também enriquece o frontmatter YAML com area, subarea, tags.
    """
    area, subarea = detect_legal_area(text)
    tags = extract_tags(text)

    text = apply_semantic_formatting(text)
    # Defeito 2: classificação semântica em vez de insert_callouts indiscriminado
    from .callout_classifier import apply_smart_callouts
    text = apply_smart_callouts(text)
    text = generate_section_summaries(text)
    text = normalize_footnotes(text)

    # Enriquecer frontmatter YAML se existir
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        close_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                close_idx = i
                break
        if close_idx > 0:
            extra = [
                f'area: "{area}"',
                f'subarea: "{subarea}"',
                f'tags: "{", ".join(tags)}"',
                f'ultima_revisao: "{datetime.now().strftime("%Y-%m-%d")}"',
            ]
            lines = (
                lines[:close_idx] + extra + lines[close_idx:]
            )
            text = "\n".join(lines)

    logger.info(
        "RAG optimization: area=%s, subarea=%s, tags=%s",
        area, subarea, tags,
    )
    return text
