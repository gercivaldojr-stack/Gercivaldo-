"""Testes para processamento paralelo."""

import tempfile
from pathlib import Path

from core.parallel import (
    get_optimal_workers,
    _convert_single_file,
    convert_batch_parallel,
)


class TestGetOptimalWorkers:
    def test_default_caps_at_4(self):
        result = get_optimal_workers(100)
        assert 1 <= result <= 4

    def test_explicit_workers(self):
        result = get_optimal_workers(100, max_workers=2)
        assert result == 2

    def test_single_item(self):
        result = get_optimal_workers(1)
        assert result == 1

    def test_minimum_is_1(self):
        result = get_optimal_workers(0, max_workers=0)
        assert result == 1


class TestConvertSingleFileWrapper:
    def test_converts_txt(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("Texto de teste para conversao.\n")
            f.flush()
            path = f.name
        result = _convert_single_file({
            "file_path": path,
            "filename": "test.txt",
        })
        assert result["success"] is True
        assert "Texto de teste" in result["markdown"]
        Path(path).unlink()

    def test_error_returns_failure(self):
        result = _convert_single_file({
            "file_bytes": b"invalid",
            "filename": "bad.xyz",
        })
        assert result["success"] is False
        assert result["error"]


class TestConvertBatchParallel:
    def test_single_file_sequential(self):
        result = convert_batch_parallel(
            files=[{
                "file_bytes": b"Texto.",
                "filename": "a.txt",
            }],
            max_workers=2,
        )
        assert len(result) == 1
        assert result[0].success

    def test_multiple_files(self):
        files = [
            {"file_bytes": f"Texto {i}.".encode(), "filename": f"f{i}.txt"}
            for i in range(3)
        ]
        results = convert_batch_parallel(files=files, max_workers=2)
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_error_handling(self):
        files = [
            {"file_bytes": b"Bom texto.", "filename": "ok.txt"},
            {"file_bytes": b"invalid", "filename": "bad.xyz"},
            {"file_bytes": b"Outro texto.", "filename": "ok2.txt"},
        ]
        results = convert_batch_parallel(files=files, max_workers=2)
        assert len(results) == 3
        assert results[0].success
        assert not results[1].success
        assert results[2].success

    def test_preserves_order(self):
        files = [
            {"file_bytes": f"Doc {i}.".encode(), "filename": f"doc{i}.txt"}
            for i in range(5)
        ]
        results = convert_batch_parallel(files=files, max_workers=2)
        for i, r in enumerate(results):
            assert r.filename == f"doc{i}.txt"

    def test_workers_1_sequential(self):
        files = [
            {"file_bytes": b"A.", "filename": "a.txt"},
            {"file_bytes": b"B.", "filename": "b.txt"},
        ]
        results = convert_batch_parallel(files=files, max_workers=1)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_config_integration(self):
        from core.config import DEFAULTS, load_config
        assert "max_workers" in DEFAULTS
        cfg = load_config(None)
        assert cfg["max_workers"] is None
