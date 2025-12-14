# Proyecto de Extracción de la documentación de Databento

## Ejemplos de uso de `scrapApi.py`

### En un notebook de Jupyter

> Nota: los kernels de Jupyter suelen cachear el módulo ya importado. Si has
> actualizado `scrapApi.py` durante la sesión y necesitas nuevos símbolos
> (p. ej. `SPASidebarExtractor`), recarga el módulo antes de importarlo:
>
> ```python
> import importlib, scrapApi
> importlib.reload(scrapApi)
> from scrapApi import SPADOMRenderer, SPASidebarExtractor
> ```

```python
from scrapApi import SPADOMRenderer

renderer = SPADOMRenderer()

rendered = await renderer.fetch_rendered_page(
    "https://docs.databento.com/docs/quickstart"
)

rendered.html[:500]
```

### En un script de Python

```python
from scrapApi import SPADOMRenderer


def main() -> None:
    renderer = SPADOMRenderer()
    rendered = renderer.render_to_memory(
        "https://docs.databento.com/docs/quickstart"
    )
    print(f"Se capturaron {len(rendered.html)} caracteres de HTML")


if __name__ == "__main__":
    main()
```

### Guardar el HTML en un notebook de Jupyter

```python
from scrapApi import SPADOMRenderer

renderer = SPADOMRenderer()

await renderer.render_to_file_async(
    "https://docs.databento.com/docs/quickstart",
    "out/databento_quickstart.html",
)
```

### Guardar el HTML en un script de Python

```python
from pathlib import Path

from scrapApi import SPADOMRenderer


def main() -> None:
    renderer = SPADOMRenderer()
    destino = Path("out/databento_quickstart.html")
    renderer.render_to_file(
        "https://docs.databento.com/docs/quickstart",
        destino,
    )
    print(f"HTML persistido en {destino}")


if __name__ == "__main__":
    main()
```

## Ejemplos de extracción de enlaces del DOM

### En un notebook de Jupyter

```python
from scrapApi import SPADOMRenderer, SPASidebarExtractor

renderer = SPADOMRenderer()
rendered = await renderer.fetch_rendered_page(
    "https://docs.databento.com/docs/quickstart"
)

extractor = SPASidebarExtractor(rendered)
links = await extractor.extract_links_to_memory_async()
links[:5]
```

### En un script de Python

```python
from scrapApi import SPADOMRenderer, SPASidebarExtractor


def main() -> None:
    renderer = SPADOMRenderer()
    rendered = renderer.render_to_memory(
        "https://docs.databento.com/docs/quickstart"
    )

    extractor = SPASidebarExtractor(rendered)
    links = extractor.extract_links_to_memory()
    print(f"Se encontraron {len(links)} enlaces del sidebar")


if __name__ == "__main__":
    main()
```

## Procesado en lote de enlaces con `DOCAPIscraper.py`

Cuando la lista de enlaces proviene del sidebar generado por `scrapApi.py`, los
`href` suelen ser rutas relativas (por ejemplo, `/docs/quickstart`). Para que
`batch_scraper.py` pueda navegar a esas rutas, proporciona la `base_url`
correspondiente (por ejemplo, `https://docs.databento.com`).

### En un script de Python

```python
from batch_scraper import scrape_links_to_json


def main() -> None:
    # El JSON de entrada puede ser una lista de URLs o un objeto con la clave "links"
    scrape_links_to_json(
        "out/sidebar_links.json",  # generado previamente con scrapApi.py
        "out/all_pages.json",
        base_url="https://docs.databento.com",  # resuelve enlaces relativos
    )


if __name__ == "__main__":
    main()
```

### En un notebook de Jupyter

```python
from batch_scraper import scrape_links_to_memory
import json

links_json = "out/sidebar_links.json"
links_payload = json.loads(open(links_json, "r", encoding="utf-8").read())
links = links_payload if isinstance(links_payload, list) else links_payload.get("links", [])

pages = scrape_links_to_memory(links, base_url="https://docs.databento.com")
len(pages)
```
