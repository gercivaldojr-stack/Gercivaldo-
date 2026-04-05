"""
Sistema de configuracao para o conversor juridico PDF → Markdown.

Suporta:
- Arquivo YAML de configuracao
- Flags CLI (override sobre YAML)
- Defaults sensiveis para documentos juridicos
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULTS = {
    "mode": "forense",
    "separate": False,
    "no_hf": False,
    "detect_citations": True,
    "extract_metadata": False,
    "extract_procedural": False,
    "separate_enums": False,
    "wrap_notes": False,
    "toc": False,
    "ocr": False,
    "ocr_lang": "por",
    "ocr_threshold": 30,
    "pages": None,
    "chunk_size": None,
    "detect_columns": True,
    "output_format": "md",
}


def load_config(config_path: str | None) -> dict:
    """Carrega configuracao de arquivo YAML. Retorna defaults se nao encontrar."""
    cfg = dict(DEFAULTS)

    if not config_path:
        return cfg

    path = Path(config_path)
    if not path.exists():
        logger.warning("Arquivo de config nao encontrado: %s (usando defaults)", config_path)
        return cfg

    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML nao instalado. Ignorando config YAML.")
        return cfg

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict):
            cfg.update(data)
            logger.info("Config carregada de %s", config_path)
        else:
            logger.warning("Config YAML invalida (esperava dict): %s", config_path)
    except Exception as e:
        logger.warning("Erro ao ler config %s: %s", config_path, e)

    return cfg


def merge_cli_into_config(cfg: dict, args) -> dict:
    """Aplica flags CLI sobre a config carregada. CLI tem prioridade."""
    result = dict(cfg)

    if hasattr(args, "mode") and args.mode is not None:
        result["mode"] = args.mode
    if hasattr(args, "toc") and args.toc:
        result["toc"] = True
    if hasattr(args, "separate") and args.separate:
        result["separate"] = True
    if hasattr(args, "no_citations") and args.no_citations:
        result["detect_citations"] = False
    elif hasattr(args, "citations") and args.citations:
        result["detect_citations"] = True
    if hasattr(args, "metadata") and args.metadata:
        result["extract_metadata"] = True
    if hasattr(args, "procedural") and args.procedural:
        result["extract_procedural"] = True
    if hasattr(args, "enums") and args.enums:
        result["separate_enums"] = True
    if hasattr(args, "notes") and args.notes:
        result["wrap_notes"] = True
    if hasattr(args, "no_hf") and args.no_hf:
        result["no_hf"] = True
    if hasattr(args, "ocr") and args.ocr:
        result["ocr"] = True
    if hasattr(args, "ocr_lang") and args.ocr_lang:
        result["ocr_lang"] = args.ocr_lang
    if hasattr(args, "ocr_threshold") and args.ocr_threshold is not None:
        result["ocr_threshold"] = args.ocr_threshold
    if hasattr(args, "pages") and args.pages:
        result["pages"] = args.pages
    if hasattr(args, "chunk_size") and args.chunk_size is not None:
        result["chunk_size"] = args.chunk_size
    if hasattr(args, "no_columns") and args.no_columns:
        result["detect_columns"] = False
    elif hasattr(args, "columns") and args.columns:
        result["detect_columns"] = True
    if hasattr(args, "output_format") and args.output_format is not None:
        result["output_format"] = args.output_format

    # Garantir defaults
    for key, default in DEFAULTS.items():
        result.setdefault(key, default)

    return result
