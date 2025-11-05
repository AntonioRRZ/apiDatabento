"""Utilities para capturar el DOM renderizado de documentación estilo Docusaurus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Coroutine, Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


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

    def render_to_file(self, url: str, out_path: str | Path, timeout_ms: int = 60_000) -> RenderedPage:
        """Guarda el DOM renderizado en un fichero y devuelve el resultado."""

        rendered = self.render_to_memory(url, timeout_ms=timeout_ms)
        destination = Path(out_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered.html, encoding="utf-8")
        return rendered

    def _run_sync(self, coroutine: Coroutine[Any, Any, RenderedPage]) -> RenderedPage:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError(
            "Ya existe un bucle de eventos en ejecución. Usa 'await fetch_rendered_page' "
            "en entornos asíncronos."
        )
