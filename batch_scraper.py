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
from urllib.parse import urljoin, urlparse

from DOCAPIscraper import PageExtraction, SPAPlaywrightScraper


def _normalize_link(raw: Any, base_url: str | None) -> str | None:
    """Convierte un enlace en cadena absoluta o devuelve ``None`` si no es válido."""

    href = None
    if isinstance(raw, dict):
        href = raw.get("href") or raw.get("url")
    else:
        href = str(raw)

    if href is None:
        return None

    cleaned = str(href).strip()
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    if parsed.scheme:
        return cleaned

    if cleaned.startswith("//"):
        # URLs tipo protocol-relative
        return "https:" + cleaned

    if cleaned.startswith("/") and base_url:
        return urljoin(base_url, cleaned)

    if base_url and not parsed.netloc:
        return urljoin(base_url.rstrip("/"), cleaned)

    # Si sigue siendo relativo y no hay base, no es navegable
    return None


def _load_links(json_path: str | Path, base_url: str | None = None) -> List[str]:
    """
    Carga una lista de enlaces desde un JSON y los normaliza.

    - Si el JSON contiene una lista, se usa directamente.
    - Si el JSON contiene un objeto con la clave ``links``, se usa ese array.
    - Si los elementos son diccionarios con ``href``/``url`` o rutas relativas,
      se resuelven con ``base_url``.
    """

    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        links = payload
    else:
        links = payload.get("links", []) if isinstance(payload, dict) else []

    if not isinstance(links, list):
        raise ValueError("El JSON debe contener una lista o una clave 'links' con la lista de URLs")

    normalized = [_normalize_link(link, base_url) for link in links]
    cleaned = [link for link in normalized if link]

    if not cleaned:
        hint = " Usa --base-url si tus enlaces son relativos."
        raise ValueError("No se encontraron enlaces navegables en el JSON de entrada." + hint)

    return cleaned


async def scrape_links_async(links: Sequence[str]) -> List[PageExtraction]:
    scraper = SPAPlaywrightScraper()
    results: List[PageExtraction] = []
    for url in links:
        results.append(await scraper.scrape_page(url))
    return results


def scrape_links_to_memory(
    links: Iterable[Any], *, base_url: str | None = None
) -> List[Dict[str, Any]]:
    """Procesa los enlaces y devuelve una lista serializable en memoria.

    Acepta tanto URLs directas como diccionarios con clave ``href``/``url`` y
    resuelve enlaces relativos cuando se proporciona ``base_url``.
    """

    normalized = [_normalize_link(link, base_url) for link in links]
    usable = [link for link in normalized if link]
    if not usable:
        hint = " Define base_url cuando tus enlaces son relativos."
        raise ValueError("No se encontraron enlaces navegables en memoria." + hint)

    pages = asyncio.run(scrape_links_async(usable))
    return [
        {
            "url": page.url,
            "page_title": page.page_title,
            "examples": [asdict(ex) for ex in page.examples],
        }
        for page in pages
    ]


def scrape_links_to_json(
    links_json_path: str | Path, output_path: str | Path, *, base_url: str | None = None
) -> List[Dict[str, Any]]:
    """
    Ejecuta la extracción en lote y guarda un "super JSON" con todas las páginas.

    Devuelve la misma estructura para reutilizarla en memoria.
    """

    links = _load_links(links_json_path, base_url=base_url)
    payload = scrape_links_to_memory(links, base_url=base_url)

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
    parser.add_argument(
        "--base-url",
        help="URL base para resolver enlaces relativos (ej: https://docs.databento.com)",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = scrape_links_to_json(args.links_json, args.out, base_url=args.base_url)
    print(f"Se procesaron {len(result)} páginas. JSON guardado en {args.out}")


if __name__ == "__main__":
    main()
