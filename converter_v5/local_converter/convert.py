#!/usr/bin/env python3
"""
Conversor PDF → Markdown (Etapa 1 — Local)
Wrapper para o Marker com configurações otimizadas para documentos jurídicos brasileiros.

Uso:
    python convert.py documento.pdf
    python convert.py documento.pdf --use-ollama
    python convert.py documento.pdf --use-claude
    python convert.py ./pasta/ --batch --use-ollama
    python convert.py documento.pdf --pages "0-10"
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


def run_marker_single(
    input_path: str,
    output_dir: str,
    use_llm: bool = False,
    llm_backend: str = "ollama",
    ollama_model: str = "gemma3",
    claude_model: str = "claude-sonnet-4-20250514",
    page_range: str = None,
    force_ocr: bool = False,
    extract_images: bool = True,
    langs: str = "pt",
) -> Path:
    """Executa marker_single para um PDF."""

    cmd = [
        "marker_single",
        str(input_path),
        "--output_dir", str(output_dir),
        "--output_format", "markdown",
    ]

    if langs:
        cmd.extend(["--langs", langs])

    if page_range:
        cmd.extend(["--page_range", page_range])

    if force_ocr:
        cmd.append("--force_ocr")

    if not extract_images:
        cmd.append("--disable_image_extraction")

    if use_llm:
        cmd.append("--use_llm")

        if llm_backend == "ollama":
            cmd.extend([
                "--llm_service", "marker.services.ollama.OllamaService",
                "--ollama_base_url", "http://localhost:11434",
                "--ollama_model", ollama_model,
            ])
        elif llm_backend == "claude":
            cmd.extend([
                "--llm_service", "marker.services.claude.ClaudeService",
                "--claude_model_name", claude_model,
            ])
        elif llm_backend == "gemini":
            cmd.extend([
                "--llm_service", "marker.services.gemini.GoogleGeminiService",
            ])

    print(f"\n{'='*60}")
    print(f"Convertendo: {input_path}")
    print(f"Backend LLM: {llm_backend if use_llm else 'nenhum'}")
    print(f"Comando: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"ERRO: Marker retornou código {result.returncode}")
        return None

    output_path = Path(output_dir)
    md_files = list(output_path.rglob("*.md"))

    if md_files:
        print(f"\nConversão concluída: {md_files[0]}")
        return md_files[0]
    else:
        print("ERRO: Nenhum arquivo .md encontrado na saída.")
        return None


def run_marker_batch(
    input_dir: str,
    output_dir: str,
    workers: int = 2,
    **kwargs,
) -> list:
    """Executa marker em lote para uma pasta de PDFs."""

    cmd = [
        "marker",
        str(input_dir),
        str(output_dir),
        "--workers", str(workers),
        "--output_format", "markdown",
    ]

    if kwargs.get("langs"):
        cmd.extend(["--langs", kwargs["langs"]])

    if kwargs.get("use_llm"):
        cmd.append("--use_llm")
        backend = kwargs.get("llm_backend", "ollama")

        if backend == "ollama":
            cmd.extend([
                "--llm_service", "marker.services.ollama.OllamaService",
                "--ollama_base_url", "http://localhost:11434",
                "--ollama_model", kwargs.get("ollama_model", "gemma3"),
            ])

    print(f"\nConvertendo pasta: {input_dir}")
    print(f"Workers: {workers}")
    print(f"Comando: {' '.join(cmd)}\n")

    subprocess.run(cmd, capture_output=False)

    output_path = Path(output_dir)
    return list(output_path.rglob("*.md"))


def create_zip(output_dir: str, zip_name: str = None) -> Path:
    """Compacta a saída em .zip para upload no Streamlit."""

    output_path = Path(output_dir)

    if zip_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"conversao_{timestamp}.zip"

    zip_path = output_path.parent / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in output_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(output_path)
                zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\nZIP criado: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def check_ollama():
    """Verifica se o Ollama está rodando."""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:11434", timeout=3)
        return req.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Conversor PDF → Markdown via Marker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python convert.py documento.pdf
  python convert.py documento.pdf --use-ollama
  python convert.py documento.pdf --use-claude
  python convert.py documento.pdf --pages "0-10" --force-ocr
  python convert.py ./pasta/ --batch --use-ollama --workers 4
        """,
    )

    parser.add_argument("input", help="PDF ou pasta com PDFs")
    parser.add_argument("-o", "--output", default="./saida", help="Pasta de saída (default: ./saida)")
    parser.add_argument("--batch", action="store_true", help="Modo lote (pasta de PDFs)")
    parser.add_argument("--workers", type=int, default=2, help="Workers paralelos (lote)")
    parser.add_argument("--use-ollama", action="store_true", help="Usar Ollama como LLM backend")
    parser.add_argument("--use-claude", action="store_true", help="Usar Claude API como LLM backend")
    parser.add_argument("--use-gemini", action="store_true", help="Usar Gemini API como LLM backend")
    parser.add_argument("--ollama-model", default="gemma3", help="Modelo Ollama (default: gemma3)")
    parser.add_argument("--pages", default=None, help='Páginas a converter. Ex: "0,5-10,20"')
    parser.add_argument("--force-ocr", action="store_true", help="Forçar OCR em todo o documento")
    parser.add_argument("--no-images", action="store_true", help="Não extrair imagens")
    parser.add_argument("--langs", default="pt", help="Idiomas para OCR (default: pt)")
    parser.add_argument("--zip", action="store_true", help="Criar .zip da saída")
    parser.add_argument("--no-zip", action="store_true", help="Não criar .zip")

    args = parser.parse_args()

    use_llm = args.use_ollama or args.use_claude or args.use_gemini
    llm_backend = "ollama"
    if args.use_claude:
        llm_backend = "claude"
    elif args.use_gemini:
        llm_backend = "gemini"

    if args.use_ollama:
        if not check_ollama():
            print("ERRO: Ollama não está rodando em localhost:11434")
            print("Inicie com: ollama serve")
            print("Ou instale: curl -fsSL https://ollama.com/install.sh | sh")
            sys.exit(1)
        print("Ollama detectado e rodando.")

    if args.batch:
        md_files = run_marker_batch(
            args.input,
            args.output,
            workers=args.workers,
            use_llm=use_llm,
            llm_backend=llm_backend,
            ollama_model=args.ollama_model,
            langs=args.langs,
        )
        print(f"\n{len(md_files)} arquivo(s) convertido(s).")
    else:
        md_file = run_marker_single(
            args.input,
            args.output,
            use_llm=use_llm,
            llm_backend=llm_backend,
            ollama_model=args.ollama_model,
            page_range=args.pages,
            force_ocr=args.force_ocr,
            extract_images=not args.no_images,
            langs=args.langs,
        )

    if args.zip or (not args.no_zip and not args.batch):
        create_zip(args.output)

    print("\nConcluído.")


if __name__ == "__main__":
    main()
