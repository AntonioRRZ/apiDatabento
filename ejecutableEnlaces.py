from scrapApi import SPADOMRenderer, SPASidebarExtractor


def main() -> None:
    renderer = SPADOMRenderer()
    rendered = renderer.render_to_memory(
        "https://databento.com/docs/examples/futures/futures-introduction/finding-futures-contracts-with-highest-volume"
    )

    extractor = SPASidebarExtractor(rendered)
    links = extractor.extract_links_to_memory()
    print(f"Se encontraron {len(links)} enlaces del sidebar")


if __name__ == "__main__":
    main()
