"""Testes para o cache de OCR."""

import json
import time

from core.ocr_cache import OCRCache


class MockPixmap:
    def __init__(self, data: bytes = b"fake-pixmap-data"):
        self.samples = data


class MockPage:
    """Mock de página PyMuPDF com get_pixmap()."""
    def __init__(self, data: bytes = b"page-content-123"):
        self._data = data

    def get_pixmap(self, dpi=72):
        return MockPixmap(self._data)


class TestOCRCacheDisabled:
    def test_get_returns_none(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c", enabled=False)
        page = MockPage()
        assert cache.get(page, "por") is None

    def test_put_is_noop(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c", enabled=False)
        page = MockPage()
        cache.put(page, "por", "Texto OCR")
        assert not any((tmp_path / "c").glob("*.json"))


class TestOCRCachePutGet:
    def test_put_and_get(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        page = MockPage()
        cache.put(page, "por", "Texto extraido via OCR")
        result = cache.get(page, "por")
        assert result == "Texto extraido via OCR"

    def test_miss_returns_none(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        page = MockPage(b"never-seen")
        assert cache.get(page, "por") is None

    def test_different_lang_different_hash(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        page = MockPage()
        cache.put(page, "por", "Texto portugues")
        assert cache.get(page, "eng") is None
        assert cache.get(page, "por") == "Texto portugues"


class TestOCRCacheClear:
    def test_clear_all(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        for i in range(3):
            page = MockPage(f"page-{i}".encode())
            cache.put(page, "por", f"Texto {i}")
        count = cache.clear()
        assert count == 3
        assert cache.stats()["total_entries"] == 0

    def test_clear_older_than(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        page_old = MockPage(b"old-page")
        page_new = MockPage(b"new-page")
        cache.put(page_old, "por", "Velho")
        # Manipular timestamp para ser "velho"
        for f in (tmp_path / "c").glob("*.json"):
            data = json.loads(f.read_text())
            data["created_at"] = time.time() - 200000
            f.write_text(json.dumps(data))
        cache.put(page_new, "por", "Novo")
        removed = cache.clear_older_than(1)
        assert removed == 1
        assert cache.stats()["total_entries"] == 1


class TestOCRCacheStats:
    def test_stats(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        for i in range(3):
            page = MockPage(f"p{i}".encode())
            cache.put(page, "por", f"T{i}")
        s = cache.stats()
        assert s["total_entries"] == 3
        assert s["total_size_bytes"] > 0
        assert s["oldest"] is not None
        assert s["newest"] is not None


class TestOCRCacheCustomDir:
    def test_custom_dir(self, tmp_path):
        custom = tmp_path / "my" / "custom" / "cache"
        cache = OCRCache(cache_dir=custom)
        page = MockPage()
        cache.put(page, "por", "Custom cache")
        assert custom.exists()
        assert cache.get(page, "por") == "Custom cache"


class TestOCRCacheCorrupted:
    def test_corrupted_file_graceful(self, tmp_path):
        cache = OCRCache(cache_dir=tmp_path / "c")
        page = MockPage()
        cache.put(page, "por", "Original")
        # Corromper o arquivo
        for f in (tmp_path / "c").glob("*.json"):
            f.write_text("NOT VALID JSON{{{")
        result = cache.get(page, "por")
        assert result is None
