"""
Detecção de layout em 2 colunas para páginas PDF.

Analisa bboxes dos blocos de texto para determinar se a página tem
layout de coluna dupla e reordena os blocos na ordem correta de leitura.
"""

import logging

logger = logging.getLogger(__name__)


def detect_and_reorder_columns(page) -> str:
    """Detecta layout de 2 colunas e retorna texto na ordem de leitura.

    Analisa os blocos de texto da página. Se houver um gap vertical
    consistente entre 40-60% da largura da página, considera layout
    de 2 colunas e reordena: coluna esquerda (top→bottom) depois
    coluna direita (top→bottom).

    Args:
        page: Página PyMuPDF (fitz.Page).

    Returns:
        Texto da página na ordem correta de leitura.
    """
    page_width = page.rect.width
    blocks = page.get_text("dict")["blocks"]

    text_blocks = []
    for blk in blocks:
        if blk["type"] != 0:
            continue
        text = ""
        for line in blk.get("lines", []):
            for span in line.get("spans", []):
                text += span.get("text", "")
        text = text.strip()
        if text:
            text_blocks.append({
                "x0": blk["bbox"][0],
                "y0": blk["bbox"][1],
                "x1": blk["bbox"][2],
                "y1": blk["bbox"][3],
                "text": text,
            })

    if not text_blocks:
        return ""

    is_two_col = _is_two_column_layout(text_blocks, page_width)

    if is_two_col:
        midpoint = page_width / 2
        left = sorted(
            [b for b in text_blocks if b["x0"] < midpoint],
            key=lambda b: b["y0"],
        )
        right = sorted(
            [b for b in text_blocks if b["x0"] >= midpoint],
            key=lambda b: b["y0"],
        )
        ordered = left + right
        logger.debug(
            "2 colunas detectadas: %d blocos esquerda, %d direita",
            len(left), len(right),
        )
    else:
        ordered = sorted(text_blocks, key=lambda b: (b["y0"], b["x0"]))

    return "\n".join(b["text"] for b in ordered)


def _is_two_column_layout(
    text_blocks: list[dict], page_width: float
) -> bool:
    """Determina se os blocos formam layout de 2 colunas.

    Critério: existe um gap vertical entre 40-60% da largura da página
    onde nenhum (ou quase nenhum) bloco de texto cruza.
    """
    if len(text_blocks) < 4:
        return False

    left_margin = page_width * 0.40
    right_margin = page_width * 0.60

    left_count = 0
    right_count = 0
    crossing_count = 0

    for b in text_blocks:
        if b["x1"] <= right_margin and b["x0"] < left_margin:
            left_count += 1
        elif b["x0"] >= left_margin:
            right_count += 1
        else:
            if b["x0"] < left_margin and b["x1"] > right_margin:
                crossing_count += 1

    total = len(text_blocks)
    if crossing_count > total * 0.3:
        return False

    if left_count >= 2 and right_count >= 2:
        return True

    return False
