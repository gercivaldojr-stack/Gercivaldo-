"""Testes para o módulo CLI e configuração."""

import tempfile
from pathlib import Path

from core.config import DEFAULTS, load_config, merge_cli_into_config


class TestLoadConfig:
    def test_returns_defaults_without_file(self):
        cfg = load_config(None)
        assert cfg["mode"] == "forense"
        assert cfg["ocr"] is False
        assert cfg["detect_citations"] is True

    def test_returns_defaults_for_missing_file(self):
        cfg = load_config("/tmp/nonexistent_config_xyz.yaml")
        assert cfg["mode"] == "forense"

    def test_loads_yaml_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("mode: doutrina\nocr: true\nocr_lang: eng\n")
            f.flush()
            cfg = load_config(f.name)
        assert cfg["mode"] == "doutrina"
        assert cfg["ocr"] is True
        assert cfg["ocr_lang"] == "eng"
        Path(f.name).unlink()

    def test_preserves_defaults_for_unset_keys(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("mode: doutrina\n")
            f.flush()
            cfg = load_config(f.name)
        assert cfg["detect_citations"] is True  # default preservado
        assert cfg["ocr_threshold"] == 30
        Path(f.name).unlink()


class TestMergeCliIntoConfig:
    def _make_args(self, **kwargs):
        """Cria objeto mock de args."""
        from types import SimpleNamespace
        defaults = {
            "mode": None, "toc": False, "separate": False,
            "citations": None, "no_citations": False,
            "metadata": False, "procedural": False,
            "enums": False, "notes": False, "no_hf": False,
            "ocr": False, "ocr_lang": "por", "ocr_threshold": 30,
            "pages": None, "chunk_size": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_cli_overrides_config(self):
        cfg = {"mode": "doutrina", "ocr": False}
        args = self._make_args(mode="forense", ocr=True)
        result = merge_cli_into_config(cfg, args)
        assert result["mode"] == "forense"
        assert result["ocr"] is True

    def test_no_citations_flag(self):
        cfg = {"detect_citations": True}
        args = self._make_args(no_citations=True)
        result = merge_cli_into_config(cfg, args)
        assert result["detect_citations"] is False

    def test_defaults_filled(self):
        cfg = {}
        args = self._make_args()
        result = merge_cli_into_config(cfg, args)
        for key, default in DEFAULTS.items():
            assert key in result


class TestCliMain:
    def test_missing_input_returns_error(self):
        from cli import main
        ret = main(["nonexistent_file.pdf"])
        assert ret == 1

    def test_converts_txt_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("PETIÇÃO INICIAL\n\nDOS FATOS\n\nTexto de teste.\n")
            f.flush()
            input_path = f.name

        output_path = input_path.replace(".txt", ".md")
        from cli import main
        ret = main([input_path, "-o", output_path])
        assert ret == 0
        assert Path(output_path).exists()
        content = Path(output_path).read_text()
        assert "PETIÇÃO" in content or "titulo" in content
        Path(input_path).unlink()
        Path(output_path).unlink(missing_ok=True)

    def test_chunk_size_zero_rejected(self):
        """chunk_size <= 0 deve retornar erro."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Texto.\n")
            f.flush()
            input_path = f.name
        from cli import main
        ret = main([input_path, "--chunk-size", "0"])
        assert ret == 1
        Path(input_path).unlink()

    def test_chunk_size_negative_rejected(self):
        """chunk_size negativo deve retornar erro."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Texto.\n")
            f.flush()
            input_path = f.name
        from cli import main
        ret = main([input_path, "--chunk-size", "-5"])
        assert ret == 1
        Path(input_path).unlink()

    def test_batch_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Criar dois arquivos de teste
            for name in ["doc1.txt", "doc2.txt"]:
                (Path(tmpdir) / name).write_text("Texto de teste do documento.\n")

            output_dir = str(Path(tmpdir) / "saida")
            from cli import main
            ret = main([tmpdir, "--batch", "-o", output_dir])
            assert ret == 0
            assert Path(output_dir).exists()
            md_files = list(Path(output_dir).glob("*.md"))
            assert len(md_files) == 2
