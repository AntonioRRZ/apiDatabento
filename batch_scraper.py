"""
Script para procesar en lote la lista de enlaces de documentación y extraer
página a página los títulos y ejemplos de código usando ``DOCAPIscraper.py``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from DOCAPIscraper import PageExtraction, SPAPlaywrightScraper


def _load_links(json_path: str | Path) -> List[str]:
    """
    Carga una lista de enlaces desde un JSON.

    - Si el JSON contiene una lista, se usa directamente.
    - Si el JSON contiene un objeto con la clave ``links``, se usa ese array.
    """

    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        links = payload
    else:
        links = payload.get("links", []) if isinstance(payload, dict) else []

    if not isinstance(links, list):
        raise ValueError("El JSON debe contener una lista o una clave 'links' con la lista de URLs")

    cleaned = [str(link).strip() for link in links if str(link).strip()]
    if not cleaned:
        raise ValueError("No se encontraron enlaces válidos en el JSON de entrada")
    return cleaned


async def scrape_links_async(links: Sequence[str]) -> List[PageExtraction]:
    scraper = SPAPlaywrightScraper()
    results: List[PageExtraction] = []
    for url in links:
        results.append(await scraper.scrape_page(url))
    return results


def scrape_links_to_memory(links: Iterable[str]) -> List[Dict[str, Any]]:
    """Procesa los enlaces y devuelve una lista serializable en memoria."""

    pages = asyncio.run(scrape_links_async(list(links)))
    return [
        {
            "url": page.url,
            "page_title": page.page_title,
            "examples": [asdict(ex) for ex in page.examples],
        }
        for page in pages
    ]


def scrape_links_to_json(links_json_path: str | Path, output_path: str | Path) -> List[Dict[str, Any]]:
    """
    Ejecuta la extracción en lote y guarda un "super JSON" con todas las páginas.

    Devuelve la misma estructura para reutilizarla en memoria.
    """

    links = _load_links(links_json_path)
    payload = scrape_links_to_memory(links)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"pages": payload}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrae títulos y ejemplos para una lista de enlaces de documentación"
    )
    parser.add_argument("links_json", help="Ruta al JSON con la lista de enlaces")
    parser.add_argument(
        "--out",
        default="out/all_pages.json",
        help="Ruta de salida para el JSON combinado (por defecto: out/all_pages.json)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = scrape_links_to_json(args.links_json, args.out)
    print(f"Se procesaron {len(result)} páginas. JSON guardado en {args.out}")


if __name__ == "__main__":
    main()
