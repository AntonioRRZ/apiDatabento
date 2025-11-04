from DOCAPIscraper import SPAPlaywrightScraper

if __name__ == "__main__":
    url = "https://databento.com/docs/examples/futures/futures-introduction/finding-futures-contracts-with-highest-volume"
    scraper = SPAPlaywrightScraper()
    data = scraper.scrape_to_json(url, "out/databento_highest_volume.json")
    print(f"Guardado JSON con {len(data['examples'])} ejemplos y {len(data['links'])} enlaces.")
