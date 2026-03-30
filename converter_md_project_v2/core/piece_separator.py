"""
Módulo para separação de peças processuais em PDFs.
Detecta múltiplas peças dentro de um único documento e as separa.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Padrões que indicam início de uma nova peça processual
PIECE_START_PATTERNS = [
    r"^PETIÇÃO\s+INICIAL",
    r"^CONTESTAÇÃO",
    r"^RÉPLICA",
    r"^RECONVENÇÃO",
    r"^SENTENÇA",
    r"^ACÓRDÃO",
    r"^DESPACHO",
    r"^DECISÃO\s+(INTERLOCUTÓRIA|MONOCRÁTICA)",
    r"^RECURSO\s+(DE\s+)?(APELAÇÃO|ESPECIAL|EXTRAORDINÁRIO|ORDINÁRIO)",
    r"^AGRAVO\s+(DE\s+INSTRUMENTO|INTERNO|REGIMENTAL)",
    r"^APELAÇÃO",
    r"^EMBARGOS\s+(DE\s+DECLARAÇÃO|INFRINGENTES)",
    r"^MANDADO\s+DE\s+SEGURANÇA",
    r"^HABEAS\s+CORPUS",
    r"^PARECER",
    r"^LAUDO\s+(PERICIAL|TÉCNICO)",
    r"^CERTIDÃO",
    r"^ATA\s+DE\s+AUDIÊNCIA",
    r"^TERMO\s+DE\s+AUDIÊNCIA",
    r"^CONTRA[\s-]?RAZÕES",
    r"^RAZÕES\s+DE\s+APELAÇÃO",
    r"^RAZÕES\s+DE\s+RECURSO",
    r"^MEMORIAL",
    r"^IMPUGNAÇÃO",
    r"^MANIFESTAÇÃO",
    r"^ALEGAÇÕES\s+FINAIS",
    r"^EXCELENTÍSSIM[OA]\s+SENHOR[A]?",
    r"^AO\s+JUÍZ[OA]?\s+DE\s+DIREITO",
]

# Padrão para número de página (usado como delimitador auxiliar)
PAGE_BREAK_PATTERN = r"\f"


def separate_pieces(text: str) -> list[dict]:
    """Separa o texto em múltiplas peças processuais.

    Args:
        text: Texto completo do documento.

    Returns:
        Lista de dicts com 'title' e 'content' de cada peça.
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")
    pieces = []
    current_title = "Documento Principal"
    current_lines = []
    piece_count = 0

    for line in lines:
        stripped = line.strip()
        # Remover prefixos de heading markdown para matching
        clean_line = re.sub(r"^#{1,6}\s+", "", stripped)
        upper = clean_line.upper()

        is_new_piece = False
        new_title = None

        for pattern in PIECE_START_PATTERNS:
            if re.match(pattern, upper):
                # Confirmar que é um heading (linha relativamente curta)
                if len(clean_line) < 150:
                    is_new_piece = True
                    new_title = clean_line
                    break

        if is_new_piece and (current_lines or piece_count == 0):
            # Salvar peça anterior se houver conteúdo
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    pieces.append({
                        "title": current_title,
                        "content": content,
                    })

            current_title = new_title
            current_lines = [line]
            piece_count += 1
        else:
            current_lines.append(line)

    # Salvar última peça
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            pieces.append({
                "title": current_title,
                "content": content,
            })

    if len(pieces) <= 1:
        logger.info("Documento contém peça única")
    else:
        logger.info("Detectadas %d peças processuais", len(pieces))

    return pieces


def format_separated_pieces(pieces: list[dict]) -> str:
    """Formata peças separadas em um documento Markdown único com delimitadores."""
    if not pieces:
        return ""

    parts = []
    for i, piece in enumerate(pieces):
        parts.append(f"# {piece['title']}")
        parts.append("")
        parts.append(piece["content"])
        if i < len(pieces) - 1:
            parts.append("")
            parts.append("---")
            parts.append("")

    return "\n".join(parts)
