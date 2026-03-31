"""
Geração de frontmatter YAML para documentos jurídicos convertidos.
Extrai metadados do texto estruturado e produz bloco YAML.
"""

import re
from datetime import datetime


def generate_frontmatter(text: str, filename: str = "") -> str:
    """Gera bloco YAML frontmatter a partir do texto convertido.

    Extrai automaticamente:
      - titulo: primeira linha significativa ou nome do arquivo
      - proad: número PROAD/SEI se encontrado
      - data: data do documento se encontrada
      - orgao_emissor: órgão identificado no texto
      - status: 'vigente' por padrão

    Args:
        text: Texto Markdown já processado pelas heurísticas.
        filename: Nome original do arquivo (fallback para título).

    Returns:
        String com bloco YAML entre delimitadores '---'.
    """
    meta: dict[str, str] = {}

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
        r"(?:PROAD|SEI|Processo|Proc\.)\s*(?:n[º°.]?\s*)?(\d[\d./-]+)",
        text,
        re.IGNORECASE,
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

    meta.setdefault("status", "vigente")
    meta["convertido_em"] = datetime.now().strftime("%Y-%m-%d")

    # Monta YAML
    lines = ["---"]
    for key, value in meta.items():
        safe_value = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{safe_value}"')
    lines.append("---")
    return "\n".join(lines)
