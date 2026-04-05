"""Detecção automática de idioma para OCR."""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Mapeamento de código ISO 639-1 → Tesseract lang code
LANG_MAP = {
    "pt": "por",
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "de": "deu",
    "it": "ita",
}

# Palavras-chave por idioma (stop words frequentes em documentos)
_LANG_KEYWORDS = {
    "pt": {
        "de", "do", "da", "dos", "das", "que", "para", "com", "por", "não",
        "uma", "seu", "sua", "nos", "pelo", "pela", "este", "esta", "artigo",
        "lei", "processo", "tribunal", "juiz", "sentença", "recurso",
    },
    "en": {
        "the", "and", "for", "that", "with", "this", "from", "not", "but",
        "are", "was", "were", "have", "has", "been", "will", "would", "court",
        "law", "judge", "case", "shall", "section",
    },
    "es": {
        "del", "los", "las", "que", "para", "con", "por", "una", "sus",
        "este", "esta", "como", "más", "pero", "han", "ley", "tribunal",
        "juez", "sentencia", "recurso", "artículo",
    },
    "fr": {
        "les", "des", "que", "pour", "avec", "par", "dans", "une", "sur",
        "est", "sont", "pas", "cette", "mais", "loi", "tribunal", "juge",
        "article", "décision",
    },
    "de": {
        "der", "die", "das", "und", "den", "von", "mit", "für", "auf",
        "ein", "ist", "nicht", "des", "dem", "auch", "gericht", "gesetz",
        "richter", "urteil", "artikel",
    },
    "it": {
        "del", "dei", "che", "per", "con", "una", "gli", "non", "suo",
        "sua", "nel", "dalla", "questo", "questa", "legge", "tribunale",
        "giudice", "sentenza", "articolo",
    },
}


def detect_language(text: str, min_words: int = 20) -> str:
    """Detecta idioma do texto via análise de stop words.

    Retorna código Tesseract (por, eng, spa, fra, deu, ita).
    Se não conseguir detectar (texto curto ou ambíguo), retorna "por".
    Não usa dependências externas (sem langdetect/fasttext).
    Abordagem leve: conta palavras-chave por idioma e retorna o com mais hits.
    """
    if not text or len(text.strip()) < 30:
        return "por"

    # Tokenizar: palavras lowercase, apenas letras
    words = re.findall(r"[a-záàâãéèêíïóôõúüçñ]+", text.lower())
    if len(words) < min_words:
        return "por"

    # Contar palavras-chave por idioma
    scores: dict[str, int] = {}
    word_set = set(words)  # Para lookup rápido
    word_counter = Counter(words)
    for lang_code, keywords in _LANG_KEYWORDS.items():
        score = sum(word_counter[w] for w in keywords if w in word_set)
        scores[lang_code] = score

    if not scores or max(scores.values()) == 0:
        return "por"

    best_lang = max(scores, key=scores.get)
    best_score = scores[best_lang]

    # Verificar se a detecção é confiável (score mínimo)
    total_scored_words = sum(scores.values())
    if total_scored_words < 5:
        return "por"

    # Verificar se não é muito ambíguo (2o lugar muito próximo)
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[0] > 0:
        ratio = sorted_scores[1] / sorted_scores[0]
        if ratio > 0.8:  # Muito próximos = ambíguo
            logger.debug(
                "Detecção ambígua (ratio=%.2f), usando 'por'", ratio
            )
            return "por"

    tess_lang = LANG_MAP.get(best_lang, "por")
    logger.debug(
        "Idioma detectado: %s (score=%d, total=%d) -> %s",
        best_lang, best_score, total_scored_words, tess_lang,
    )
    return tess_lang


def detect_language_from_page(page) -> str:
    """Detecta idioma do texto nativo de uma página PyMuPDF.

    Extrai texto nativo (sem OCR) e analisa.
    Se a página tem pouco texto, retorna "por".
    """
    try:
        text = page.get_text("text")
        return detect_language(text)
    except Exception:
        return "por"


def detect_document_language(doc, sample_pages: int = 10) -> str:
    """Detecta idioma dominante do documento inteiro.

    Amostra até sample_pages páginas e faz votação.
    Útil para definir idioma antes do OCR.
    """
    if len(doc) == 0:
        return "por"

    indices = list(range(min(sample_pages, len(doc))))
    if len(doc) > sample_pages:
        step = len(doc) / sample_pages
        indices = [int(i * step) for i in range(sample_pages)]

    votes = Counter()
    for idx in indices:
        try:
            text = doc[idx].get_text("text")
            if len(text.strip()) > 30:
                lang = detect_language(text)
                votes[lang] += 1
        except Exception:
            continue

    if not votes:
        return "por"
    return votes.most_common(1)[0][0]
