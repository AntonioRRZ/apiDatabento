"""Utilities para capturar el DOM renderizado de documentación estilo Docusaurus."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Coroutine, Optional

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright

__all__ = [
    "RenderedPage",
    "SPADOMRenderer",
    "SidebarLink",
    "SPASidebarExtractor",
]



@dataclass
class RenderedPage:
    """Contenido renderizado de una página SPA sin etiquetas de script o style."""

    url: str
    html: str


class SPADOMRenderer:
    """Encapsula la captura del DOM renderizado mediante Playwright.

    Está pensada para sitios de documentación estilo Docusaurus donde es necesario
    hidratar el contenido dinámico antes de extraer información. La clase ofrece
    métodos asíncronos y síncronos para reutilizar el HTML en memoria o persistirlo
    en disco, devolviendo únicamente la estructura HTML sin código CSS o JavaScript.
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        post_render_delay_ms: int = 0,
    ) -> None:
        """Configura el renderer.

        Args:
            user_agent: Cadena personalizada para la navegación headless.
            post_render_delay_ms: Tiempo adicional en milisegundos para esperar
                después de que la red quede ociosa antes de capturar el DOM.
        """

        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.post_render_delay_ms = max(0, post_render_delay_ms)

    async def _render(self, url: str, timeout_ms: int = 60_000) -> RenderedPage:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.user_agent)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Espera a que la red quede ociosa para aumentar la probabilidad de que
            # el contenido dinámico haya sido inyectado en el DOM.
            await page.wait_for_load_state("networkidle")
            if self.post_render_delay_ms:
                await page.wait_for_timeout(self.post_render_delay_ms)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")
            for unwanted in soup(["script", "style"]):
                unwanted.decompose()
            clean_html = soup.decode()
            await browser.close()
            return RenderedPage(url=url, html=clean_html)

    async def fetch_rendered_page(self, url: str, timeout_ms: int = 60_000) -> RenderedPage:
        """Devuelve el DOM renderizado de forma asíncrona."""

        return await self._render(url, timeout_ms=timeout_ms)

    def render_to_memory(self, url: str, timeout_ms: int = 60_000) -> RenderedPage:
        """Obtiene el DOM renderizado y lo retorna en memoria."""

        return self._run_sync(self.fetch_rendered_page(url, timeout_ms=timeout_ms))

    async def render_to_file_async(
        self, url: str, out_path: str | Path, timeout_ms: int = 60_000
    ) -> RenderedPage:
        """Captura el DOM y lo persiste a disco en contextos asíncronos."""

        rendered = await self.fetch_rendered_page(url, timeout_ms=timeout_ms)
        self._write_to_file(rendered, out_path)
        return rendered

    def render_to_file(
        self, url: str, out_path: str | Path, timeout_ms: int = 60_000
    ) -> RenderedPage:
        """Guarda el DOM renderizado en un fichero y devuelve el resultado."""

        return self._run_sync(
            self.render_to_file_async(url, out_path, timeout_ms=timeout_ms)
        )

    def _run_sync(self, coroutine: Coroutine[Any, Any, RenderedPage]) -> RenderedPage:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError(
            "Ya existe un bucle de eventos en ejecución. Usa 'await fetch_rendered_page' "
            "en entornos asíncronos."
        )

    def _write_to_file(self, rendered: RenderedPage, out_path: str | Path) -> None:
        destination = Path(out_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered.html, encoding="utf-8")


@dataclass(frozen=True)
class SidebarLink:
    """Representa un enlace del sidebar lateral."""

    title: str
    href: str


class SPASidebarExtractor:
    """Extrae enlaces del sidebar de navegación en sitios Docusaurus."""

    def __init__(self, rendered: RenderedPage | str) -> None:
        """Inicializa el extractor a partir del HTML renderizado."""

        if isinstance(rendered, RenderedPage):
            html = rendered.html
        else:
            html = rendered
        self.dom = BeautifulSoup(html, "html.parser")

    def _sidebar_container(self) -> Optional[Tag]:
        return self.dom.find("div", class_="os-padding")

    def extract_links(self) -> list[SidebarLink]:
        """Recupera los enlaces únicos del sidebar lateral."""

        container = self._sidebar_container()
        if container is None:
            return []

        seen: set[tuple[str, str]] = set()
        links: list[SidebarLink] = []
        for anchor in container.find_all("a", href=True):
            href = anchor.get("href", "").strip()
            title = anchor.get_text(strip=True)
            if not href:
                continue
            key = (href, title)
            if key in seen:
                continue
            seen.add(key)
            links.append(SidebarLink(title=title, href=href))
        return links

    def extract_links_to_memory(self) -> list[dict[str, str]]:
        """Devuelve los enlaces del sidebar en formato serializable."""

        return [asdict(link) for link in self.extract_links()]

    def extract_links_to_file(self, out_path: str | Path) -> list[dict[str, str]]:
        """Guarda los enlaces del sidebar en un fichero JSON."""

        data = self.extract_links_to_memory()
        destination = Path(out_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    async def extract_links_to_memory_async(self) -> list[dict[str, str]]:
        """Versión asíncrona para cuadernos Jupyter."""

        return await asyncio.to_thread(self.extract_links_to_memory)

    async def extract_links_to_file_async(self, out_path: str | Path) -> list[dict[str, str]]:
        """Persistencia de enlaces pensada para entornos asíncronos."""

        return await asyncio.to_thread(self.extract_links_to_file, out_path)
