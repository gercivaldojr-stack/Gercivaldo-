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
    # Pular linhas de frontmatter YAML e delimitadores ---
    _yaml_keys = re.compile(
        r"^(?:titulo|data|status|convertido_em|proad|orgao_emissor|tipo_peca"
        r"|paciente|autor|reu|impetrante|autoridade_coatora|pedido_liminar"
        r"|processo_origem|comarca|acoes_cumuladas)\s*:", re.IGNORECASE
    )
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if not stripped or len(stripped) <= 5:
            continue
        # Pular delimitadores de frontmatter
        if stripped == "---":
            continue
        # Pular linhas que parecem YAML (chave: "valor")
        if _yaml_keys.match(stripped):
            continue
        if re.match(r"^\w+:\s+[\"']", stripped):
            continue
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


def extract_procedural_metadata(text: str, meta: dict) -> None:
    """Extrai metadados processuais detalhados (v4.1 M1).

    Campos extraídos:
      - autor: nome do autor (com CPF se presente)
      - reu: nome do réu/requerido
      - comarca: comarca/foro do processo
      - pedido_liminar: "true"/"false"
      - acoes_cumuladas: lista de ações cumuladas

    Apenas modo forense.
    """
    search_area = text[:5000]

    # Autor com CPF opcional
    autor_match = re.search(
        r"(?:Autor|Requerente|Exequente|Impetrante)[:\s]+([A-ZÀ-Ú][A-ZÀ-Ú\s]+)"
        r"(?:,?\s*(?:inscrit[oa]\s+no\s+CPF|CPF)\s*(?:n[º°.]?\s*)?(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}))?",
        search_area,
        re.IGNORECASE,
    )
    if autor_match:
        autor_name = autor_match.group(1).strip()[:120]
        cpf = autor_match.group(2)
        if cpf:
            meta["autor"] = f"{autor_name} (CPF: {cpf.strip()})"
        else:
            meta["autor"] = autor_name

    # Réu
    reu_match = re.search(
        r"(?:Réu|Requerido|Executado|Impetrado|Autoridade\s+coatora)[:\s]+"
        r"(.+?)(?:\n|,\s*(?:inscrit|qualificad|com\s+sede))",
        search_area,
        re.IGNORECASE,
    )
    if reu_match:
        meta["reu"] = reu_match.group(1).strip()[:120]

    # Comarca — capturar apenas até newline, heading (#) ou texto em minúsculas longo
    comarca_match = re.search(
        r"(?:Comarca|Foro|Vara)\s+(?:de\s+|da\s+|do\s+)?"
        r"([A-ZÀ-Ú][^\n#]{2,60}?)(?:\s*[-–—]\s*[A-ZÀ-Ú]{2})?(?:\n|#|$)",
        search_area,
        re.IGNORECASE,
    )
    if comarca_match:
        comarca_val = comarca_match.group(1).strip()
        # Limpar slug-style text (palavras-com-hífen) que indicam lixo de heading
        comarca_val = re.split(r"[a-záéíóú]+-[a-záéíóú]+-", comarca_val)[0].strip()
        # Remover trailing pontuação ou caracteres indesejados
        comarca_val = re.sub(r"[\[\]()]+$", "", comarca_val).strip()
        if comarca_val and len(comarca_val) > 2:
            meta["comarca"] = comarca_val[:80]

    # Pedido liminar (booleano explícito)
    has_liminar = bool(re.search(
        r"(?:pedido\s+(?:de\s+)?(?:liminar|tutela\s+(?:de\s+)?urgência|"
        r"tutela\s+antecipada)|MEDIDA\s+LIMINAR|"
        r"Contém\s+pedido\s+(?:liminar|urgência|tutela)|"
        r"inaudita\s+altera\s+parte)",
        search_area,
        re.IGNORECASE,
    ))
    meta["pedido_liminar"] = "true" if has_liminar else "false"

    # Ações cumuladas
    acoes = []
    acoes_patterns = [
        (r"(?:ação\s+de\s+)?indeniza[çc]ão\s+por\s+danos?\s+morais?", "indenização por danos morais"),
        (r"(?:ação\s+de\s+)?indeniza[çc]ão\s+por\s+danos?\s+materiais?", "indenização por danos materiais"),
        (r"(?:ação\s+de\s+)?obriga[çc]ão\s+de\s+fazer", "obrigação de fazer"),
        (r"(?:ação\s+de\s+)?obriga[çc]ão\s+de\s+n[aã]o\s+fazer", "obrigação de não fazer"),
        (r"repara[çc]ão\s+de\s+danos", "reparação de danos"),
        (r"revis[aã]o\s+contratual", "revisão contratual"),
        (r"cobran[çc]a", "cobrança"),
        (r"reintegra[çc]ão\s+de\s+posse", "reintegração de posse"),
        (r"consigna[çc]ão\s+em\s+pagamento", "consignação em pagamento"),
        (r"(?:rescis[aã]o|resolu[çc]ão)\s+contratual", "rescisão contratual"),
        (r"repeti[çc]ão\s+de\s+ind[eé]bito", "repetição de indébito"),
        (r"declarat[oó]ria\s+de\s+(?:nulidade|inexist[eê]ncia)", "declaratória de nulidade"),
    ]
    lower_text = search_area.lower()
    for pattern, label in acoes_patterns:
        if re.search(pattern, lower_text):
            acoes.append(label)

    if acoes:
        meta["acoes_cumuladas"] = ", ".join(acoes)
