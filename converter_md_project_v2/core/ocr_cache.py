"""Cache de resultados OCR por página de PDF.

Evita re-processar OCR em páginas já processadas anteriormente.
O cache é baseado em hash do conteúdo da página (pixmap) + idioma OCR.
Armazenamento em disco via JSON em diretório configurável.
"""

import hashlib
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "conversor-juridico" / "ocr"


class OCRCache:
    """Gerencia cache de resultados OCR em disco.

    Cada entrada é um arquivo JSON: {hash}.json
    Conteúdo: {"text": "...", "lang": "por", "created_at": timestamp}
    Hash: SHA256 do pixmap (72 DPI) + lang.
    """

    def __init__(self, cache_dir: str | Path | None = None, enabled: bool = True):
        self.enabled = enabled
        self._cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        if self.enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _page_hash(self, page, lang: str) -> str:
        """Calcula hash SHA256 do conteúdo visual da página + idioma.

        Usa pixmap em 72 DPI para ser rápido.
        """
        pix = page.get_pixmap(dpi=72)
        raw = pix.samples
        h = hashlib.sha256()
        h.update(raw)
        h.update(lang.encode("utf-8"))
        del pix
        return h.hexdigest()

    def get(self, page, lang: str) -> str | None:
        """Busca texto OCR no cache. None se miss."""
        if not self.enabled:
            return None
        try:
            page_hash = self._page_hash(page, lang)
            cache_file = self._cache_dir / f"{page_hash}.json"
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                logger.debug("OCR cache hit: %s", page_hash[:12])
                return data.get("text")
            return None
        except Exception as e:
            logger.debug("OCR cache get error: %s", e)
            return None

    def put(self, page, lang: str, text: str) -> None:
        """Salva texto OCR no cache."""
        if not self.enabled:
            return
        try:
            page_hash = self._page_hash(page, lang)
            cache_file = self._cache_dir / f"{page_hash}.json"
            data = {
                "text": text,
                "lang": lang,
                "page_hash": page_hash,
                "created_at": time.time(),
            }
            cache_file.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            logger.debug("OCR cache put: %s (%d chars)", page_hash[:12], len(text))
        except Exception as e:
            logger.debug("OCR cache put error: %s", e)

    def clear(self) -> int:
        """Limpa todo o cache. Retorna número de entradas removidas."""
        count = 0
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    pass
        logger.info("OCR cache cleared: %d entries", count)
        return count

    def clear_older_than(self, days: int) -> int:
        """Remove entradas mais velhas que N dias."""
        count = 0
        cutoff = time.time() - (days * 86400)
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if data.get("created_at", 0) < cutoff:
                        f.unlink()
                        count += 1
                except (OSError, json.JSONDecodeError):
                    pass
        logger.info(
            "OCR cache cleanup: removed %d entries older than %d days",
            count, days,
        )
        return count

    def stats(self) -> dict:
        """Estatísticas do cache."""
        total = 0
        size = 0
        oldest = float("inf")
        newest = 0.0
        if self._cache_dir.exists():
            for f in self._cache_dir.glob("*.json"):
                total += 1
                size += f.stat().st_size
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    ts = data.get("created_at", 0)
                    oldest = min(oldest, ts)
                    newest = max(newest, ts)
                except (OSError, json.JSONDecodeError):
                    pass
        return {
            "total_entries": total,
            "total_size_bytes": size,
            "oldest": oldest if total > 0 else None,
            "newest": newest if total > 0 else None,
        }
