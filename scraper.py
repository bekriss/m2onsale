"""
Scraper module: fetches apartment listings from Otodom and OLX.
Uses httpx + BeautifulSoup for scraping.
"""

import asyncio
import hashlib
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

OTODOM_URL = "https://www.otodom.pl/pl/wyniki/sprzedaz/mieszkanie"
OLX_URL = "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/"


def make_id(source: str, url: str) -> str:
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()


def parse_price(text: str) -> Optional[int]:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_size(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"([\d,\.]+)\s*m", text.replace("\xa0", " "))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    return None


def parse_rooms(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


class OtodomScraper:
    async def fetch(self, client: httpx.AsyncClient) -> list[dict]:
        listings = []
        try:
            resp = await client.get(OTODOM_URL, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = self._parse(soup)
            logger.info(f"Otodom: fetched {len(listings)} listing(s)")
        except Exception as e:
            logger.error(f"Otodom fetch error: {e}")
        return listings

    def _parse(self, soup: BeautifulSoup) -> list[dict]:
        results = []

        # Otodom renders data as JSON in a script tag
        scripts = soup.find_all("script", {"type": "application/json"})
        for script in scripts:
            try:
                import json
                data = json.loads(script.string or "")
                items = self._extract_from_json(data)
                if items:
                    results.extend(items)
                    return results
            except Exception:
                continue

        # Fallback: parse HTML article cards
        articles = soup.select("article[data-cy='listing-item']")
        for art in articles:
            try:
                listing = self._parse_article(art)
                if listing:
                    results.append(listing)
            except Exception as e:
                logger.debug(f"Otodom article parse error: {e}")

        return results

    def _extract_from_json(self, data) -> list[dict]:
        """Try to extract listings from Otodom's Next.js JSON data."""
        results = []
        try:
            # Navigate the nested structure
            props = data.get("props", {})
            page_props = props.get("pageProps", {})
            listings_data = page_props.get("data", {})

            # Try multiple keys
            items = (
                listings_data.get("searchAds", {}).get("items", [])
                or listings_data.get("items", [])
                or []
            )

            for item in items:
                try:
                    url = "https://www.otodom.pl" + item.get("slug", "")
                    listing = {
                        "id": make_id("otodom", url),
                        "source": "otodom",
                        "title": item.get("title", ""),
                        "url": url,
                        "price": item.get("totalPrice", {}).get("value") if item.get("totalPrice") else None,
                        "location": self._format_location(item.get("location", {})),
                        "size": item.get("areaInSquareMeters"),
                        "rooms": item.get("roomsNumber"),
                    }
                    results.append(listing)
                except Exception:
                    continue
        except Exception:
            pass
        return results

    def _format_location(self, loc: dict) -> str:
        parts = []
        if loc.get("address"):
            addr = loc["address"]
            if addr.get("city", {}).get("name"):
                parts.append(addr["city"]["name"])
            if addr.get("district", {}).get("name"):
                parts.append(addr["district"]["name"])
        return ", ".join(parts) if parts else ""

    def _parse_article(self, art) -> Optional[dict]:
        a_tag = art.find("a", href=True)
        if not a_tag:
            return None
        url = a_tag["href"]
        if not url.startswith("http"):
            url = "https://www.otodom.pl" + url

        title_el = art.find("h3") or art.find("h2") or art.find("p", {"data-cy": "listing-item-title"})
        title = title_el.get_text(strip=True) if title_el else "Apartment"

        price_el = art.find("span", string=re.compile(r"[\d\s]+\s*(PLN|zł)", re.I))
        price = parse_price(price_el.get_text() if price_el else "")

        # Location
        loc_el = art.find("p", {"data-testid": "advert-card-address"}) or art.find("address")
        location = loc_el.get_text(strip=True) if loc_el else ""

        # Size and rooms from details
        details = art.find_all("span", {"data-testid": re.compile("detail")})
        size, rooms = None, None
        for d in details:
            t = d.get_text()
            if "m²" in t or "m2" in t:
                size = parse_size(t)
            elif "pok" in t.lower() or "room" in t.lower():
                rooms = parse_rooms(t)

        return {
            "id": make_id("otodom", url),
            "source": "otodom",
            "title": title,
            "url": url,
            "price": price,
            "location": location,
            "size": size,
            "rooms": rooms,
        }


class OlxScraper:
    async def fetch(self, client: httpx.AsyncClient) -> list[dict]:
        listings = []
        try:
            resp = await client.get(OLX_URL, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = self._parse(soup)
            logger.info(f"OLX: fetched {len(listings)} listing(s)")
        except Exception as e:
            logger.error(f"OLX fetch error: {e}")
        return listings

    def _parse(self, soup: BeautifulSoup) -> list[dict]:
        results = []

        # OLX listing cards
        cards = soup.select("[data-cy='l-card']") or soup.select("div.css-1sw7q4x") or soup.select("article")
        for card in cards:
            try:
                listing = self._parse_card(card)
                if listing:
                    results.append(listing)
            except Exception as e:
                logger.debug(f"OLX card parse error: {e}")

        # Fallback: JSON-LD
        if not results:
            results = self._parse_json_ld(soup)

        return results

    def _parse_json_ld(self, soup: BeautifulSoup) -> list[dict]:
        import json
        results = []
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    items = data
                elif data.get("@type") == "ItemList":
                    items = data.get("itemListElement", [])
                else:
                    items = [data]
                for item in items:
                    thing = item.get("item", item)
                    url = thing.get("url", "")
                    if not url:
                        continue
                    listing = {
                        "id": make_id("olx", url),
                        "source": "olx",
                        "title": thing.get("name", "Apartment"),
                        "url": url,
                        "price": parse_price(str(thing.get("price", ""))),
                        "location": thing.get("address", {}).get("addressLocality", "") if isinstance(thing.get("address"), dict) else "",
                        "size": None,
                        "rooms": None,
                    }
                    results.append(listing)
            except Exception:
                continue
        return results

    def _parse_card(self, card) -> Optional[dict]:
        a_tag = card.find("a", href=True)
        if not a_tag:
            return None
        url = a_tag["href"]
        if not url.startswith("http"):
            url = "https://www.olx.pl" + url

        # Skip promoted/external
        if "otodom.pl" in url:
            return None

        title_el = card.find("h6") or card.find("h3") or card.find("h4") or card.find("strong")
        title = title_el.get_text(strip=True) if title_el else "Apartment"

        # Price
        price_el = (
            card.find("p", {"data-testid": "ad-price"})
            or card.find("span", string=re.compile(r"\d"))
            or card.find("strong", string=re.compile(r"\d"))
        )
        price = parse_price(price_el.get_text() if price_el else "")

        # Location + date
        loc_el = card.find("p", {"data-testid": "location-date"}) or card.find("span", string=re.compile(r"[A-ZŁÓŚĄĆĘ]"))
        location = ""
        if loc_el:
            text = loc_el.get_text(strip=True)
            # Strip trailing date-like text
            location = re.split(r"\s*-\s*\d", text)[0].strip()

        # Parameters (size, rooms) are often in detail spans
        params = card.find_all("span", {"class": re.compile("parameter|detail|param", re.I)})
        size, rooms = None, None
        all_text = " ".join(p.get_text() for p in params)
        size = parse_size(all_text)
        rooms_m = re.search(r"(\d+)\s*(pok|room|izb)", all_text, re.I)
        if rooms_m:
            rooms = int(rooms_m.group(1))

        return {
            "id": make_id("olx", url),
            "source": "olx",
            "title": title,
            "url": url,
            "price": price,
            "location": location,
            "size": size,
            "rooms": rooms,
        }


class ApartmentScraper:
    def __init__(self):
        self.otodom = OtodomScraper()
        self.olx = OlxScraper()

    async def fetch_all(self) -> list[dict]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = await asyncio.gather(
                self.otodom.fetch(client),
                self.olx.fetch(client),
                return_exceptions=True,
            )

        listings = []
        for r in results:
            if isinstance(r, list):
                listings.extend(r)
            elif isinstance(r, Exception):
                logger.error(f"Scraper error: {r}")

        logger.info(f"Total fetched: {len(listings)} listings")
        return listings
