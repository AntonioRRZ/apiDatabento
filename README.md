# Proyecto de Extracción de la documentación de Databento

## Ejemplos de uso de `scrapApi.py`

### En un notebook de Jupyter

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
