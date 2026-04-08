# scraper_otodom.py
from playwright.sync_api import sync_playwright

def scrape_otodom(city="warszawa", min_rooms=None):
    """
    Scrape Otodom apartments for a specific city and optional minimum number of rooms
    Returns list of dictionaries: {title, location, price, rooms, url}
    """
    city = city.lower().replace(" ", "-")  # format for URL
    url = f"https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie/{city}"
    apartments = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(5000)

        offers = page.query_selector_all("article")

        for offer in offers[:20]:  # limit first 20 for speed
            try:
                title_element = offer.query_selector("a")
                title = title_element.inner_text() if title_element else "No title"
                link = title_element.get_attribute("href") if title_element else ""

                text = offer.inner_text()
                
                # Try to get rooms from text
                rooms = None
                if "pokoi" in text.lower():
                    import re
                    match = re.search(r"(\d+)\s*pokoi", text.lower())
                    if match:
                        rooms = int(match.group(1))

                # Skip if rooms filter is set
                if min_rooms and rooms and rooms < min_rooms:
                    continue

                apartments.append({
                    "title": title,
                    "location": city,
                    "price": text,
                    "rooms": rooms,
                    "url": link
                })
            except Exception as e:
                print("Error:", e)

        browser.close()

    return apartments