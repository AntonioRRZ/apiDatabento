import asyncio
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from playwright.async_api import async_playwright


@dataclass
class CodeExample:
    title: str
    description: str
    language: str
    code: str


@dataclass
class PageExtraction:
    url: str
    page_title: str
    links: List[str]
    examples: List[CodeExample]


class SPAPlaywrightScraper:
    """
    Scraper que renderiza con Playwright (Chromium headless), extrae:
      - Título de la página
      - Todos los enlaces (absolutos)
      - Ejemplos de código: título (h2/h3 cercano), descripción (p/ul/ol entre heading y el bloque) y el snippet.
    Probado con doc sites estilo Docusaurus (Databento, etc.).
    """

    def __init__(self, user_agent: Optional[str] = None, selector_wait: str = "pre code"):
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        self.selector_wait = selector_wait

    async def _fetch_rendered_html(self, url: str, timeout_ms: int = 60_000) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=self.user_agent)
            # En SPAs, domcontentloaded + esperar selectores es más estable que networkidle
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Espera a que haya contenido real de docs (code blocks o markdown principal)
            try:
                await page.wait_for_selector(self.selector_wait, timeout=30_000)
            except Exception:
                # fallback: intenta el contenedor principal típico de Docusaurus
                await page.wait_for_selector("div.theme-doc-markdown, main, article", timeout=20_000)
            html = await page.content()
            await browser.close()
            return html

    def _absolute_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        links = []
        seen = set()
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            # Evita anchors vacíos/mailto/tel
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            abs_url = urljoin(base_url, href)
            # Normaliza fragmentos (opcional)
            parsed = urlparse(abs_url)
            abs_url = parsed._replace(fragment="").geturl()
            if abs_url not in seen:
                seen.add(abs_url)
                links.append(abs_url)
        return links

    def _closest_section_heading(self, node: Tag) -> Optional[Tag]:
        """
        Busca el heading (h2/h3) anterior más cercano al bloque de código.
        """
        curr = node
        while curr:
            curr = curr.find_previous_sibling()
            if curr and curr.name in ("h2", "h3"):
                return curr
            # Si se cruza con otro code block o un contenedor grande, paramos cuando subamos de nivel
            if curr is None and node.parent:
                # Subimos un nivel y seguimos buscando hacia atrás
                node = node.parent
                curr = node
        return None

    def _collect_description_between(self, start_heading: Optional[Tag], end_code_block: Tag) -> str:
        """
        Junta los textos (p/ul/ol/precode NO) que hay entre el heading y el bloque de código.
        Si no hay heading, recoge el texto inmediatamente anterior al code block dentro de su contenedor.
        """
        texts: List[str] = []

        # Caso 1: hay heading → capturamos hermanos entre el heading y el code block
        if start_heading:
            for sib in start_heading.next_siblings:
                if isinstance(sib, Tag):
                    if sib is end_code_block or end_code_block in sib.descendants:
                        break
                    if sib.name in ("p", "ul", "ol"):
                        texts.append(self._clean_text(sib.get_text(" ", strip=True)))
                    # Docusaurus a veces mete envoltorios
                    if sib.name in ("div", "section", "article"):
                        for sub in sib.find_all(["p", "ul", "ol"], recursive=True):
                            # Detente si el code block está aquí dentro
                            if sub.find("code"):
                                break
                            texts.append(self._clean_text(sub.get_text(" ", strip=True)))
        else:
            # Caso 2: sin heading → toma los p/ul/ol inmediatamente anteriores al code block
            for prev in end_code_block.find_all_previous():
                if isinstance(prev, Tag) and prev.name in ("p", "ul", "ol"):
                    texts.append(self._clean_text(prev.get_text(" ", strip=True)))
                if prev.name in ("h2", "h3"):
                    break
                # Para no abarcar demasiado, corta al encontrar el contenedor principal
                if prev.name in ("main", "article"):
                    break
            texts.reverse()

        # Quita duplicados por envoltorios
        desc = "\n\n".join([t for i, t in enumerate(texts) if t and (i == 0 or t != texts[i - 1])])
        return desc.strip()

    def _clean_text(self, s: str) -> str:
        return " ".join(s.split())

    def _language_from_code(self, code_tag: Tag) -> str:
        classes = code_tag.get("class", []) or []
        for c in classes:
            if c.startswith("language-"):
                return c.split("language-")[1]
        return "text"

    def _extract_examples(self, soup: BeautifulSoup) -> List[CodeExample]:
        # Los code blocks “de verdad” suelen ser <pre><code class="language-...">
        code_tags = soup.select("pre code")
        examples: List[CodeExample] = []

        # Título de sección general (por si no hay h2/h3 cercano)
        page_h1 = soup.select_one("h1")
        page_title = page_h1.get_text(" ", strip=True) if page_h1 else ""

        for code in code_tags:
            # El <pre> contenedor
            pre = code.parent if code and isinstance(code.parent, Tag) and code.parent.name == "pre" else None
            block = pre or code

            heading = self._closest_section_heading(block)
            title = (
                self._clean_text(heading.get_text(" ", strip=True))
                if heading is not None
                else (page_title or "Example")
            )

            description = self._collect_description_between(heading, block)
            language = self._language_from_code(code)
            code_text = code.get_text()

            # Filtra ruido: si ni title ni code aportan, sáltalo
            if code_text.strip():
                examples.append(
                    CodeExample(
                        title=title,
                        description=description,
                        language=language,
                        code=code_text,
                    )
                )
        return examples

    def _page_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1")
        if h1:
            return self._clean_text(h1.get_text(" ", strip=True))
        # fallback al <title>
        tit = soup.select_one("title")
        return self._clean_text(tit.get_text(" ", strip=True)) if tit else ""

    async def scrape_page(self, url: str) -> PageExtraction:
        html = await self._fetch_rendered_html(url)
        soup = BeautifulSoup(html, "lxml")

        page_title = self._page_title(soup)
        links = self._absolute_links(soup, url)
        examples = self._extract_examples(soup)

        return PageExtraction(
            url=url,
            page_title=page_title,
            links=links,
            examples=examples,
        )

    def scrape_to_json(self, url: str, out_path: str | Path) -> Dict:
        """
        Wrapper síncrono: ejecuta Playwright y guarda el JSON.
        Devuelve el dict por si lo quieres reutilizar en memoria.
        """
        data = asyncio.run(self.scrape_page(url))
        payload = {
            "url": data.url,
            "page_title": data.page_title,
            "links": data.links,  # <- etiqueta a nivel superior con todos los enlaces
            "examples": [asdict(ex) for ex in data.examples],
        }
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
