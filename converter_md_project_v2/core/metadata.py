"""
Geração de frontmatter YAML para documentos jurídicos convertidos.
Extrai metadados do texto estruturado e produz bloco YAML compatível
com Claude Projects e indexação semântica.
"""

import re
from datetime import datetime


def _strip_md_formatting(value: str) -> str:
    """Remove marcadores Markdown (**, ***, *) de valores de metadados."""
    cleaned = re.sub(r'\*{2,3}', '', value)
    return cleaned.strip()


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
    _skip_title_words = {"sumário", "índice", "sumario", "indice"}

    # D1-fix: regex para detectar doutrina no texto e no filename
    _doutrina_title_re = re.compile(
        r'(?:Manual|Curso|Tratado|Compêndio|Lições)\s+de\s+[A-ZÀ-Ú][^\n]{3,80}',
        re.IGNORECASE,
    )
    # Filename: _ é word char, usar (?:^|[\s_-]) em vez de \b
    _doutrina_fn_re = re.compile(
        r'(?:^|[\s_\-])(?:Manual|Curso|Tratado|Compêndio|Lições)'
        r'(?=$|[\s_\-])',
        re.IGNORECASE,
    )

    # Prioridade 1: texto com "Manual de X..." (mais preciso)
    doutrina_title = _doutrina_title_re.search(text[:3000])
    if doutrina_title:
        title_raw = doutrina_title.group(0).strip()
        title_raw = re.split(r'\s+\d+[ªº°]\s*(?:ed|edição)', title_raw)[0]
        title_raw = re.split(r'[.;]', title_raw)[0]
        meta["titulo"] = title_raw.strip()[:120]

    # Prioridade 2: filename com keyword de doutrina (fallback robusto)
    if "titulo" not in meta and filename and _doutrina_fn_re.search(filename):
        fn_base = filename.rsplit(".", 1)[0]
        fn_clean = fn_base.replace("_", " ").replace("-", " ").strip()
        fn_clean = re.sub(r'\(\d+\)$', '', fn_clean).strip()
        fn_clean = re.sub(r'\s+\d{4}$', '', fn_clean).strip()
        if fn_clean:
            meta["titulo"] = fn_clean

    # D1-fix: também usar ISBN para confirmar ficha catalográfica
    isbn_match = re.search(r'ISBN\s+([\d\-]+)', text[:5000])
    if isbn_match and "titulo" not in meta:
        # Buscar título próximo ao ISBN
        for line in text[:5000].splitlines():
            stripped = line.strip()
            if _doutrina_title_re.search(stripped):
                meta["titulo"] = stripped[:120]
                break

    if "titulo" not in meta:
        for line in text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if not stripped or len(stripped) <= 5:
                continue
            if stripped == "---":
                continue
            if _yaml_keys.match(stripped):
                continue
            if re.match(r"^\w+:\s+[\"']", stripped):
                continue
            if stripped.lower() in _skip_title_words:
                continue
            if stripped.startswith("- ["):
                continue
            # P1-fix: pular linhas que são referências bibliográficas
            # Padrão: "SOBRENOME, Nome. [...]. In: [...]" ou "Disponível em:" ou "Acesso em:"
            if (
                re.match(r'^[A-ZÀ-Ú]{2,}[A-ZÀ-Ú\s]*,\s+[A-ZÀ-Ú]', stripped)
                and ('. In:' in stripped or 'Acesso em' in stripped
                     or 'Disponível em' in stripped)
            ):
                continue
            # D1-fix: pular nomes de autores (2-3 palavras em MAIÚSCULAS, sem keywords)
            if (
                stripped.isupper()
                and len(stripped.split()) <= 4
                and not re.search(
                    r'\b(?:PETIÇÃO|SENTENÇA|ACÓRDÃO|HABEAS|RECURSO|'
                    r'MANDADO|CONTESTAÇÃO|AGRAVO|APELAÇÃO|EMBARGOS|'
                    r'FATOS|DIREITO|PEDIDOS|MÉRITO|RELATÓRIO|'
                    r'FUNDAMENTAÇÃO|DISPOSITIVO|EMENTA|VOTO)\b',
                    stripped,
                )
            ):
                continue
            meta["titulo"] = stripped[:120]
            break

    if "titulo" not in meta:
        # D1-fix: fallback para filename limpo
        fn = filename.rsplit(".", 1)[0] if filename else ""
        fn = fn.replace("_", " ").replace("-", " ").strip()
        # Remover (1), (2) etc do final
        fn = re.sub(r'\(\d+\)$', '', fn).strip()
        meta["titulo"] = fn if fn else "Documento sem título"

    # PROAD / SEI
    proad_match = re.search(
        r"(?:PROAD|SEI|Processo|Proc\.)\s*(?:n[º°.]?\s*)?(\d[\d./-]+)", text, re.IGNORECASE
    )
    if proad_match:
        meta["proad"] = proad_match.group(1).strip()

    # Data do documento - iterar todos matches e pegar primeiro VÁLIDO
    _date_pat = re.compile(
        r"(\d{1,2})\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|"
        r"julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})",
        re.IGNORECASE,
    )
    valid_date = None
    for m in _date_pat.finditer(text):
        day = int(m.group(1))
        # D1-fix: rejeitar dias inválidos (ex: "61 de dezembro")
        if 1 <= day <= 31:
            valid_date = m.group(0)
            break
    if valid_date:
        meta["data"] = valid_date
    else:
        iso_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
        if iso_match:
            meta["data"] = iso_match.group(0)

    # Órgão emissor (D1-fix: ignorar para doutrina/livros)
    is_book = bool(_doutrina_title_re.search(text[:3000]))
    if not is_book:
        orgao_patterns = [
            r"(?:TRIBUNAL|CONSELHO|CORREGEDORIA|MINISTÉRIO|SECRETARIA)"
            r"[\w\s]{3,60}?(?=\n)",
        ]
        for pat in orgao_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(0).strip()
                # Excluir falsos positivos de livros
                if "Conselho Fiscal" not in val:
                    meta["orgao_emissor"] = val[:80]
                break

    # P8: Metadados expandidos da peça jurídica
    if extract_metadata:
        _extract_piece_metadata(text, meta)

    meta.setdefault("status", "vigente")
    meta["convertido_em"] = datetime.now().strftime("%Y-%m-%d")

    # Monta YAML
    lines = ["---"]
    for key, value in meta.items():
        safe_value = _strip_md_formatting(str(value)).replace('"', '\\"')
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
    # Padrão 1: "Autor: NOME" / "Requerente: NOME" (com label explícito)
    autor_match = re.search(
        r"(?:Autor|Requerente|Exequente|Impetrante)[,:]\s+"
        r"([A-ZÀ-Ú][A-ZÀ-Ú ]{3,})"
        r"(?:,?\s*(?:inscrit[oa]\s+no\s+CPF|CPF)"
        r"\s*(?:n[º°.]?\s*)?"
        r"(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}))?",
        search_area,
    )
    # Padrão 2: "**NOME EM MAIÚSCULAS**, brasileiro/nacionalidade"
    # (petições que apresentam o nome no cabeçalho sem label)
    if not autor_match:
        autor_match = re.search(
            r"\*{0,2}([A-ZÀ-Ú][A-ZÀ-Ú ]{5,})\*{0,2}"
            r",\s*(?:brasileiro|brasileira|nacionalidade)"
            r"(?:[^,]*inscrit[oa]\s+no\s+CPF[^\d]*(\d{3}"
            r"[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}))?",
            search_area,
        )
    if autor_match:
        autor_name = _strip_md_formatting(
            autor_match.group(1)
        ).strip()[:120]
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
        comarca_val = _strip_md_formatting(comarca_match.group(1)).strip()
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
