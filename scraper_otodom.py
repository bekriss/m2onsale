from playwright.sync_api import sync_playwright

def scrape_otodom(city="warszawa"):
    url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{city}"

    apartments = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        offers = page.query_selector_all("article")

        for offer in offers[:10]:
            try:
                title_element = offer.query_selector("a")
                title = title_element.inner_text() if title_element else "No title"
                link = title_element.get_attribute("href") if title_element else ""

                text = offer.inner_text()

                apartments.append({
                    "title": title,
                    "location": city,
                    "price": text,
                    "rooms": None,
                    "url": link
                })
            except Exception as e:
                print("Error:", e)

        browser.close()

    return apartments

if __name__ == "__main__":
    results = scrape_otodom("warszawa")

    for item in results:
        print(item)
