#!/usr/bin/env python3
"""
CLI para o Conversor Jurídico PDF/DOCX → Markdown.

Uso:
    python cli.py documento.pdf
    python cli.py documento.pdf -o saida.md --mode doutrina
    python cli.py ./pasta/ --batch --mode forense
    python cli.py documento.pdf --ocr --config config.yaml
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from core.config import load_config, merge_cli_into_config
from core.pipeline import convert_document


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="Conversor de documentos juridicos (PDF/DOCX/TXT) para Markdown limpo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python cli.py peticao.pdf
  python cli.py peticao.pdf -o peticao.md --mode forense --toc
  python cli.py ./autos/ --batch -o ./saida/
  python cli.py grande.pdf --ocr --pages 1-50
  python cli.py grande.pdf --pages 10-100 --chunk-size 50
  python cli.py doc.pdf --config config.yaml --separate
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Arquivo PDF/DOCX/TXT ou pasta (com --batch). "
             "Opcional para --ocr-cache-stats e --ocr-cache-clear.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Arquivo ou pasta de saida. Padrao: <input>.md ou ./saida/",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Processa todos os arquivos suportados no nivel imediato da pasta "
             "(nao-recursivo).",
    )
    parser.add_argument(
        "--mode",
        choices=["forense", "doutrina", "google"],
        default=None,
        help="Modo de heuristicas: forense (pecas processuais), "
             "doutrina (livros/artigos), google (negrito inline, sem headings).",
    )

    # Funcionalidades
    feat = parser.add_argument_group("funcionalidades")
    feat.add_argument("--toc", action="store_true", help="Gerar sumario automatico.")
    feat.add_argument("--separate", action="store_true", help="Separar pecas processuais.")
    feat.add_argument("--citations", action="store_true", default=None,
                      help="Detectar citacoes jurisprudenciais como blockquote.")
    feat.add_argument("--no-citations", action="store_true", help="Desabilitar deteccao de citacoes.")
    feat.add_argument("--metadata", action="store_true", help="Extrair metadados expandidos da peca.")
    feat.add_argument("--procedural", action="store_true", help="Extrair metadados processuais (autor, reu, comarca).")
    feat.add_argument("--enums", action="store_true", help="Separar itens enumerados com ;")
    feat.add_argument("--notes", action="store_true", help="Demarcar notas internas em blockquote.")
    feat.add_argument("--no-hf", action="store_true", help="Nao remover cabecalhos/rodapes repetidos.")
    feat.add_argument("--columns", action="store_true", default=None,
                      help="Detectar layout de 2 colunas em PDFs (padrao: ativo).")
    feat.add_argument("--no-columns", action="store_true",
                      help="Desabilitar deteccao de colunas.")
    feat.add_argument("--format", choices=["md", "html", "docx"], default=None,
                      dest="output_format",
                      help="Formato de saida: md (padrao), html ou docx.")

    # OCR
    ocr = parser.add_argument_group("OCR")
    ocr.add_argument("--ocr", action="store_true", help="Habilitar OCR seletivo por pagina (requer pytesseract).")
    ocr.add_argument(
        "--ocr-lang", default="por",
        help="Idioma do Tesseract (padrao: por). "
             "Use 'auto' para deteccao automatica.",
    )
    ocr.add_argument(
        "--ocr-threshold", type=int, default=30,
        help="Chars minimos para considerar pagina com texto (padrao: 30).",
    )
    ocr.add_argument(
        "--ocr-cache", action="store_true",
        help="Habilitar cache de OCR em disco.",
    )
    ocr.add_argument(
        "--ocr-cache-dir", default=None,
        help="Diretorio do cache OCR "
             "(padrao: ~/.cache/conversor-juridico/ocr).",
    )
    ocr.add_argument(
        "--ocr-cache-clear", action="store_true",
        help="Limpar cache de OCR e sair.",
    )
    ocr.add_argument(
        "--ocr-cache-stats", action="store_true",
        help="Mostrar estatisticas do cache e sair.",
    )

    # Performance
    perf = parser.add_argument_group("performance")
    perf.add_argument("--pages", default=None,
                      help='Paginas a processar (1-based). Ex: "1-10", "1,5,10-20". '
                           'Pagina 1 = primeira pagina do documento.')
    perf.add_argument("--workers", type=int, default=None,
                      help="Workers para processamento paralelo de chunks dentro de PDFs. "
                           "0 = sequencial (padrao). -1 = auto (detectar CPUs). "
                           "Em --batch, o paralelismo e aplicado dentro de cada arquivo.")
    perf.add_argument("--chunk-size", type=int, default=None,
                      help="Paginas por chunk para PDFs grandes. Processa N paginas por "
                           "vez, liberando memoria entre chunks. Recomendado: 50-200 para "
                           "PDFs com 500+ paginas em maquinas com pouca RAM.")

    # Config
    parser.add_argument(
        "--config",
        default=None,
        help="Arquivo de configuracao YAML.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detalhado.")
    parser.add_argument("--quiet", action="store_true", help="Apenas erros no log.")

    return parser


def _resolve_output(input_path: Path, output: str | None, batch: bool) -> Path:
    if output:
        return Path(output)
    if batch:
        return input_path / "saida_md"
    return input_path.with_suffix(".md")


def _convert_single(input_path: Path, output_path: Path, cfg: dict) -> bool:
    start = time.monotonic()
    result = convert_document(
        file_path=str(input_path),
        filename=input_path.name,
        mode=cfg.get("mode", "forense"),
        separate=cfg.get("separate", False),
        remove_headers_footers=not cfg.get("no_hf", False),
        detect_citations=cfg.get("detect_citations", True),
        extract_metadata=cfg.get("extract_metadata", False),
        extract_procedural=cfg.get("extract_procedural", False),
        separate_enums=cfg.get("separate_enums", False),
        wrap_notes=cfg.get("wrap_notes", False),
        generate_toc_flag=cfg.get("toc", False),
        ocr_enabled=cfg.get("ocr", False),
        ocr_lang=cfg.get("ocr_lang", "por"),
        ocr_threshold=cfg.get("ocr_threshold", 30),
        page_range=cfg.get("pages"),
        chunk_size=cfg.get("chunk_size"),
        detect_columns=cfg.get("detect_columns", True),
        output_format=cfg.get("output_format", "md"),
        max_workers=cfg.get("max_workers"),
        ocr_cache_enabled=cfg.get("ocr_cache", False),
        ocr_cache_dir=cfg.get("ocr_cache_dir"),
    )
    elapsed = time.monotonic() - start

    if not result.success:
        print(f"ERRO: {result.error}", file=sys.stderr)
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = cfg.get("output_format", "md")
    if fmt == "html" and result.html:
        output_path = output_path.with_suffix(".html")
        output_path.write_text(result.html, encoding="utf-8")
    elif fmt == "docx" and result.docx_bytes:
        output_path = output_path.with_suffix(".docx")
        output_path.write_bytes(result.docx_bytes)
    else:
        output_path.write_text(result.markdown, encoding="utf-8")

    stats = result.stats
    print(f"OK: {input_path.name}")
    print(f"    {stats.get('chars_raw', 0):,} chars bruto -> {stats.get('chars_final', 0):,} chars final")
    if "pieces_count" in stats and stats["pieces_count"] > 1:
        print(f"    {stats['pieces_count']} pecas detectadas")
    print(f"    Tempo: {elapsed:.1f}s")
    print(f"    Saida: {output_path}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Ações especiais de cache (executam e saem)
    if getattr(args, "ocr_cache_clear", False):
        from core.ocr_cache import OCRCache
        cache = OCRCache(cache_dir=args.ocr_cache_dir)
        n = cache.clear()
        print(f"Cache limpo: {n} entradas removidas.")
        return 0
    if getattr(args, "ocr_cache_stats", False):
        from core.ocr_cache import OCRCache
        cache = OCRCache(cache_dir=args.ocr_cache_dir)
        s = cache.stats()
        print(f"Entradas: {s['total_entries']}")
        print(f"Tamanho: {s['total_size_bytes']:,} bytes")
        return 0

    # Validar que input foi fornecido para operações normais
    if args.input is None:
        parser.error("argumento 'input' é obrigatório (exceto para --ocr-cache-stats / --ocr-cache-clear).")

    # Validar chunk_size
    if args.chunk_size is not None and args.chunk_size < 1:
        print("ERRO: --chunk-size deve ser >= 1.", file=sys.stderr)
        return 1

    if args.quiet:
        _setup_logging(False)
        logging.getLogger().setLevel(logging.ERROR)
    else:
        _setup_logging(args.verbose)

    # Carregar config
    cfg = load_config(args.config) if args.config else {}
    cfg = merge_cli_into_config(cfg, args)

    # Validar chunk_size do config também
    if cfg.get("chunk_size") is not None and cfg["chunk_size"] < 1:
        print("ERRO: chunk_size deve ser >= 1.", file=sys.stderr)
        return 1

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERRO: '{input_path}' nao encontrado.", file=sys.stderr)
        return 1

    if args.batch:
        if not input_path.is_dir():
            print(f"ERRO: '{input_path}' nao e uma pasta. Use --batch com pastas.", file=sys.stderr)
            return 1

        exts = {".pdf", ".docx", ".txt", ".md"}
        files = sorted(f for f in input_path.iterdir() if f.suffix.lower() in exts)
        if not files:
            print(f"Nenhum arquivo suportado em '{input_path}'.", file=sys.stderr)
            return 1

        output_dir = _resolve_output(input_path, args.output, batch=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processando {len(files)} arquivo(s) em '{input_path}'...")
        ok_count = 0
        for i, f in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] ", end="")
            ext_map = {"md": ".md", "html": ".html", "docx": ".docx"}
            out_ext = ext_map.get(cfg.get("output_format", "md"), ".md")
            out = output_dir / f.with_suffix(out_ext).name
            if _convert_single(f, out, cfg):
                ok_count += 1

        print(f"\nConcluido: {ok_count}/{len(files)} convertidos com sucesso.")
        return 0 if ok_count == len(files) else 1

    else:
        if not input_path.is_file():
            print(f"ERRO: '{input_path}' nao e um arquivo.", file=sys.stderr)
            return 1

        output_path = _resolve_output(input_path, args.output, batch=False)
        ok = _convert_single(input_path, output_path, cfg)
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
