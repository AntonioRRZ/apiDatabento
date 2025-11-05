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
