"""
Geração de frontmatter YAML para documentos jurídicos convertidos.
Extrai metadados do texto estruturado e produz bloco YAML compatível
com Claude Projects e indexação semântica.
"""

import re
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


def extract_procedural_metadata(text: str) -> dict:
    """Extrai metadados estruturados de peça processual (modo forense).

    Detecta: autor (com CPF), réu, comarca/vara, número do processo,
    pedido liminar/tutela de urgência e ações cumuladas.
    """
    meta: dict = {}

    # --- Autor / Requerente (com CPF) ---
    autor_patterns = [
        # NOME, qualificação..., CPF nº XXX
        r"([A-ZÀ-Ú\s\[\]/.]+?),\s*(?:brasileiro|brasileira|produtor|produtora|"
        r"empresári[oa]|comerciante|agricultor|pessoa\s+física).*?"
        r"CPF\s*(?:n[.ºo°]*\s*)?(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2})",
        # Fallback: qualquer menção a CPF próxima de qualificação
        r"(?:inscrit[oa]\s+no\s+)?CPF\s*(?:n[.ºo°]*\s*)?"
        r"(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2})",
    ]
    for pat in autor_patterns:
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            cpf = match.group(match.lastindex)
            # Tentar capturar qualificação resumida
            qual_match = re.search(
                r"(produtor\s+rural|empresári[oa]|comerciante|agricultor|"
                r"pessoa\s+física|servidor\s+público)",
                text[: match.end()],
                re.IGNORECASE,
            )
            qual = qual_match.group(1).strip().capitalize() if qual_match else ""
            if qual:
                meta["autor"] = f"{qual}, CPF {cpf}"
            else:
                meta["autor"] = f"CPF {cpf}"
            break

    # --- Réu / Requerido ---
    reu_patterns = [
        r"em\s+face\s+d[eao]\s+([A-ZÀ-Ú\s.]+(?:S\.?\s*A\.?|LTDA\.?|ME|EPP|EIRELI))",
        r"(?:Réu|Requerido|Requerida|Impetrado|Executado)[:\s]+(.+?)(?:\n|,\s*(?:pessoa|sociedade|inscrit))",
        r"(?:Autoridade\s+coatora)[:\s]+(.+?)(?:\n)",
    ]
    for pat in reu_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Remove trailing comma/space but preserve dots in abbreviations like S.A.
            value = re.sub(r"[,\s]+$", "", value)
            meta["reu"] = value
            break

    # --- Comarca / Vara ---
    vara_patterns = [
        r"JUIZ(?:O|A)?\s+DE\s+DIREITO\s+D[AO]?\s*(.+?COMARCA\s+DE\s+.+?)(?:\n|$)",
        r"(\d+[.ªºa]*\s*Vara\s+.+?(?:Comarca|Seção|Subseção)\s+.+?)(?:\n|$)",
        r"(?:Vara\s+Cível\s+da\s+Comarca\s+de\s+)(.+?)(?:\n|$|[–—])",
    ]
    for pat in vara_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            meta["comarca"] = match.group(1).strip().rstrip(",. ")[:100]
            break

    # --- Pedido liminar / tutela de urgência ---
    if re.search(
        r"(?:pedido\s+(?:de\s+)?(?:medida\s+)?liminar|"
        r"tutela\s+(?:de\s+)?urgência|"
        r"tutela\s+antecipada|"
        r"medida\s+cautelar)",
        text,
        re.IGNORECASE,
    ):
        meta["pedido_liminar"] = True

    # --- Ações cumuladas (headings H1 com nomes de ações) ---
    acoes = []
    acao_patterns = [
        r"^#\s+(AÇÃO\s+.+)$",
        r"^#\s+(C/C\s+.+)$",
        r"^#\s+(HABEAS\s+CORPUS.*)$",
        r"^#\s+(MANDADO\s+DE\s+SEGURANÇA.*)$",
        r"^#\s+(RECURSO\s+.+)$",
        r"^#\s+(AGRAVO\s+.+)$",
    ]
    for pat in acao_patterns:
        for m in re.finditer(pat, text, re.MULTILINE | re.IGNORECASE):
            cleaned = m.group(1).strip()
            if cleaned and cleaned not in acoes:
                acoes.append(cleaned)
    if acoes:
        meta["acoes_cumuladas"] = acoes

    return meta


def generate_frontmatter(
    text: str,
    filename: str = "",
    mode: str = "forense",
    extract_full_metadata: bool = True,
) -> str:
    """Gera bloco YAML frontmatter a partir do texto convertido.

    Extrai automaticamente:
      - titulo: primeira linha significativa ou nome do arquivo
      - proad: número PROAD/SEI se encontrado
      - data: data do documento se encontrada
      - orgao_emissor: órgão identificado no texto
      - autor, reu, comarca, pedido_liminar, acoes_cumuladas (modo forense)
      - status: 'vigente' por padrão

    Args:
        text: Texto Markdown já processado pelas heurísticas.
        filename: Nome original do arquivo (fallback para título).
        mode: 'forense' ou 'doutrina'.
        extract_full_metadata: Se True e modo forense, extrai metadados processuais.

    Returns:
        String com bloco YAML entre delimitadores '---'.
    """
    meta: dict[str, str | bool | list] = {}

    # Título: primeira linha não-vazia que pareça heading ou ementa
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped and len(stripped) > 5:
            meta["titulo"] = stripped[:120]
            break
    if "titulo" not in meta:
        meta["titulo"] = filename.rsplit(".", 1)[0] if filename else "Documento sem título"

    # PROAD / SEI
    proad_match = re.search(
        r"(?:PROAD|SEI|Processo|Proc\.)\s*(?:n[º°.]?\s*)?(\d[\d./-]+)", text, re.IGNORECASE
    )
    if proad_match:
        meta["proad"] = proad_match.group(1).strip()

    # Data do documento
    date_match = re.search(
        r"(\d{1,2})\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|"
        r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if date_match:
        meta["data"] = date_match.group(0)
    else:
        iso_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
        if iso_match:
            meta["data"] = iso_match.group(0)

    # Órgão emissor
    orgao_patterns = [
        r"(?:TRIBUNAL|CONSELHO|CORREGEDORIA|MINISTÉRIO|SECRETARIA)"
        r"[\w\s]{3,60}?(?=\n)",
    ]
    for pat in orgao_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            meta["orgao_emissor"] = m.group(0).strip()[:80]
            break

    # M1: Metadados processuais (modo forense)
    if mode == "forense" and extract_full_metadata:
        proc_meta = extract_procedural_metadata(text)
        for key, value in proc_meta.items():
            if key not in meta:
                meta[key] = value

    meta.setdefault("status", "vigente")
    meta["convertido_em"] = datetime.now().strftime("%Y-%m-%d")

    # Monta YAML
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                safe_item = str(item).replace('"', '\\"')
                lines.append(f'  - "{safe_item}"')
        else:
            safe_value = str(value).replace('"', '\\"')
            lines.append(f'{key}: "{safe_value}"')
    lines.append("---")
    return "\n".join(lines)
