"""
Geração de frontmatter YAML para documentos jurídicos convertidos.
Extrai metadados do texto estruturado e produz bloco YAML compatível
com Claude Projects e indexação semântica.
"""

import re
from datetime import datetime


def generate_frontmatter(
    text: str,
    filename: str = "",
    extract_metadata: bool = False,
) -> str:
    """Gera bloco YAML frontmatter a partir do texto convertido.

    Extrai automaticamente:
      - titulo: primeira linha significativa ou nome do arquivo
      - proad: número PROAD/SEI se encontrado
      - data: data do documento se encontrada
      - orgao_emissor: órgão identificado no texto
      - status: 'vigente' por padrão

    Se extract_metadata=True (P8), extrai campos adicionais:
      - tipo_peca: tipo do documento jurídico
      - paciente / autor / impetrante
      - autoridade_coatora / réu / requerido
      - pedido_liminar: true/false

    Args:
        text: Texto Markdown já processado pelas heurísticas.
        filename: Nome original do arquivo (fallback para título).
        extract_metadata: Se True, extrai metadados expandidos da peça.

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

    # P8: Metadados expandidos da peça jurídica
    if extract_metadata:
        _extract_piece_metadata(text, meta)

    meta.setdefault("status", "vigente")
    meta["convertido_em"] = datetime.now().strftime("%Y-%m-%d")

    # Monta YAML
    lines = ["---"]
    for key, value in meta.items():
        safe_value = str(value).replace('"', '\\"')
        lines.append(f'{key}: "{safe_value}"')
    lines.append("---")
    return "\n".join(lines)


# Padrões para detecção de tipo de peça (P8)
_TIPO_PECA_PATTERNS = [
    (r"HABEAS\s+CORPUS", "Habeas Corpus"),
    (r"PETIÇÃO\s+INICIAL", "Petição Inicial"),
    (r"CONTESTAÇÃO", "Contestação"),
    (r"SENTENÇA", "Sentença"),
    (r"ACÓRDÃO", "Acórdão"),
    (r"MANDADO\s+DE\s+SEGURANÇA", "Mandado de Segurança"),
    (r"RECURSO\s+(?:ESPECIAL|ORDINÁRIO|EXTRAORDINÁRIO)", "Recurso"),
    (r"AGRAVO", "Agravo"),
    (r"APELAÇÃO", "Apelação"),
]

# Padrões para extração de partes processuais (P8)
_METADATA_FIELD_PATTERNS = [
    ("processo_origem", re.compile(
        r"Processo(?:\s+de\s+origem)?\s*n[.º°]*\s*(\d[\d./-]+)",
        re.IGNORECASE,
    )),
    ("paciente", re.compile(
        r"Paciente:\s*(.+?)(?:\n|$)", re.IGNORECASE,
    )),
    ("impetrante", re.compile(
        r"Impetrante:\s*(.+?)(?:\n|$)", re.IGNORECASE,
    )),
    ("autor", re.compile(
        r"(?:Autor|Requerente|Exequente):\s*(.+?)(?:\n|$)", re.IGNORECASE,
    )),
    ("autoridade_coatora", re.compile(
        r"Autoridade\s+coatora:\s*(.+?)(?:\n|$)", re.IGNORECASE,
    )),
    ("reu", re.compile(
        r"(?:Réu|Requerido|Impetrado|Executado):\s*(.+?)(?:\n|$)", re.IGNORECASE,
    )),
]


def _extract_piece_metadata(text: str, meta: dict) -> None:
    """Extrai metadados expandidos de peça jurídica (P8)."""
    # Tipo de peça
    upper_text = text[:2000].upper()
    for pattern, label in _TIPO_PECA_PATTERNS:
        if re.search(pattern, upper_text):
            meta["tipo_peca"] = label
            break

    # Partes processuais
    search_area = text[:3000]
    for field_name, pattern in _METADATA_FIELD_PATTERNS:
        m = pattern.search(search_area)
        if m:
            meta[field_name] = m.group(1).strip()[:120]

    # Pedido liminar
    if re.search(
        r"(?:Contém\s+pedido\s+(?:liminar|urgência|tutela)|pedido\s+liminar|MEDIDA\s+LIMINAR)",
        search_area,
        re.IGNORECASE,
    ):
        meta["pedido_liminar"] = "true"
