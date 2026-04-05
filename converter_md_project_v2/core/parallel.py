"""Módulo de processamento paralelo para conversão em lote e chunks de PDF."""

import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def get_optimal_workers(total_items: int, max_workers: int | None = None) -> int:
    """Calcula número ideal de workers.

    * Se max_workers fornecido, usa esse valor (limitado a cpu_count)
    * Senão, usa min(cpu_count, total_items, 4) para evitar overhead
    * Mínimo de 1 worker
    """
    cpu_count = mp.cpu_count() or 1
    if max_workers is not None and max_workers > 0:
        return max(1, min(max_workers, cpu_count))
    return max(1, min(cpu_count, total_items, 4))


def _convert_single_file(kwargs: dict) -> dict:
    """Wrapper para convert_document que pode ser pickled por multiprocessing.

    Recebe dict com todos os argumentos, chama convert_document, retorna
    dict serializado com: filename, markdown, html, docx_bytes, pieces,
    stats, success, error, output_format.

    IMPORTANTE: import de convert_document DENTRO da função (para ser picklable).
    """
    from core.pipeline import convert_document
    try:
        result = convert_document(**kwargs)
        return {
            "filename": result.filename,
            "markdown": result.markdown,
            "html": result.html,
            "docx_bytes": result.docx_bytes,
            "pieces": result.pieces,
            "stats": result.stats,
            "success": result.success,
            "error": result.error,
            "output_format": result.output_format,
            "mode": result.mode,
        }
    except Exception as e:
        return {
            "filename": kwargs.get("filename", "unknown"),
            "markdown": "",
            "html": None,
            "docx_bytes": None,
            "pieces": [],
            "stats": {},
            "success": False,
            "error": str(e),
            "output_format": kwargs.get("output_format", "md"),
            "mode": kwargs.get("mode", "forense"),
        }


def convert_batch_parallel(
    files: list[dict],
    max_workers: int | None = None,
    **convert_kwargs,
) -> list:
    """Versão paralela de convert_batch.

    * Usa ProcessPoolExecutor
    * Cada file é processado em worker separado
    * Mantém ordem original dos resultados
    * Se max_workers=1 ou len(files)=1, usa loop sequencial (sem overhead)
    * Retorna lista de ConversionResult na mesma ordem de files
    * Captura exceções por arquivo sem matar outros workers
    """
    from core.pipeline import ConversionResult

    if len(files) <= 1 or (max_workers is not None and max_workers <= 1):
        from core.pipeline import convert_document
        results = []
        for file_info in files:
            kw = dict(convert_kwargs)
            kw["file_bytes"] = file_info.get("file_bytes")
            kw["filename"] = file_info.get("filename")
            results.append(convert_document(**kw))
        return results

    workers = get_optimal_workers(len(files), max_workers)
    logger.info("Batch paralelo: %d arquivos, %d workers", len(files), workers)

    tasks = []
    for file_info in files:
        kw = dict(convert_kwargs)
        kw["file_bytes"] = file_info.get("file_bytes")
        kw["filename"] = file_info.get("filename")
        tasks.append(kw)

    results_dicts = [None] * len(tasks)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(_convert_single_file, task): i
            for i, task in enumerate(tasks)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results_dicts[idx] = future.result()
            except Exception as e:
                results_dicts[idx] = {
                    "filename": tasks[idx].get("filename", "unknown"),
                    "markdown": "",
                    "html": None,
                    "docx_bytes": None,
                    "pieces": [],
                    "stats": {},
                    "success": False,
                    "error": str(e),
                    "output_format": "md",
                    "mode": "forense",
                }

    results = []
    for d in results_dicts:
        r = ConversionResult(
            markdown=d["markdown"],
            html=d.get("html"),
            docx_bytes=d.get("docx_bytes"),
            pieces=d["pieces"],
            filename=d["filename"],
            mode=d.get("mode", "forense"),
            output_format=d.get("output_format", "md"),
            success=d["success"],
            error=d["error"],
            stats=d["stats"],
        )
        results.append(r)

    return results


def _process_chunk_worker(kwargs: dict) -> dict:
    """Worker que processa um chunk de páginas de um PDF.

    * Abre o PDF via fitz.open(doc_path)
    * Itera sobre as páginas do chunk
    * Chama _extract_single_page para cada página
    * Fecha o doc e retorna {chunk_index, text_parts, ocr_count}
    * IMPORTANTE: imports dentro da função
    """
    import fitz
    from core.extractors import _extract_single_page

    doc_path = kwargs["doc_path"]
    chunk_pages = kwargs["chunk_pages"]
    chunk_index = kwargs["chunk_index"]
    remove_set = set(tuple(x) for x in kwargs["remove_set_list"])
    ocr_enabled = kwargs.get("ocr_enabled", False)
    ocr_lang = kwargs.get("ocr_lang", "por")
    ocr_threshold = kwargs.get("ocr_threshold", 30)
    detect_columns = kwargs.get("detect_columns", True)

    text_parts = []
    ocr_count = 0

    doc = fitz.open(doc_path)
    for page_idx in chunk_pages:
        page = doc[page_idx]
        try:
            page_text, used_ocr = _extract_single_page(
                page, page_idx, remove_set,
                ocr_enabled, ocr_lang, ocr_threshold,
                detect_columns=detect_columns,
            )
            if used_ocr:
                ocr_count += 1
            if page_text.strip():
                text_parts.append(page_text)
        except Exception as e:
            logger.warning("Erro na página %d: %s", page_idx + 1, e)
            try:
                fallback = page.get_text("text")
                if fallback.strip():
                    text_parts.append(fallback)
            except Exception:
                text_parts.append(f"\n[Erro ao extrair página {page_idx + 1}]\n")
    doc.close()

    return {
        "chunk_index": chunk_index,
        "text_parts": text_parts,
        "ocr_count": ocr_count,
    }


def process_pdf_chunks_parallel(
    doc_path: str,
    pages_to_process: list[int],
    chunk_size: int,
    remove_set: set,
    ocr_enabled: bool = False,
    ocr_lang: str = "por",
    ocr_threshold: int = 30,
    detect_columns: bool = True,
    max_workers: int | None = None,
) -> tuple[list[str], int]:
    """Processa chunks de PDF em paralelo.

    * Divide pages_to_process em chunks de chunk_size páginas
    * Cada chunk é processado em worker separado via ProcessPoolExecutor
    * Cada worker abre o PDF, processa suas páginas, fecha o PDF
    * Retorna (text_parts_ordenados, ocr_count)
    * Se max_workers=1 ou só 1 chunk, processa sequencialmente
    * NOTA: remove_set convertido para list para ser picklable
    """
    chunks = []
    for i in range(0, len(pages_to_process), chunk_size):
        chunks.append(pages_to_process[i:i + chunk_size])

    if len(chunks) <= 1 or (max_workers is not None and max_workers <= 1):
        return None, 0  # Signal caller to use sequential

    workers = get_optimal_workers(len(chunks), max_workers)
    logger.info(
        "PDF chunks paralelos: %d chunks, %d workers",
        len(chunks), workers,
    )

    remove_set_list = [list(x) for x in remove_set]

    tasks = []
    for idx, chunk_pages in enumerate(chunks):
        tasks.append({
            "doc_path": doc_path,
            "chunk_pages": chunk_pages,
            "chunk_index": idx,
            "remove_set_list": remove_set_list,
            "ocr_enabled": ocr_enabled,
            "ocr_lang": ocr_lang,
            "ocr_threshold": ocr_threshold,
            "detect_columns": detect_columns,
        })

    results = [None] * len(tasks)
    total_ocr = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(_process_chunk_worker, task): i
            for i, task in enumerate(tasks)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error("Chunk %d falhou: %s", idx, e)
                results[idx] = {
                    "chunk_index": idx,
                    "text_parts": [],
                    "ocr_count": 0,
                }

    all_text_parts = []
    for r in results:
        all_text_parts.extend(r["text_parts"])
        total_ocr += r["ocr_count"]

    return all_text_parts, total_ocr
