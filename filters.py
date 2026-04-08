"""
Filter module: checks whether a listing matches a chat's filter criteria.
"""

import re
import logging

logger = logging.getLogger(__name__)


class FilterManager:
    def matches(self, listing: dict, filters: dict) -> bool:
        """Return True if the listing passes all configured filters."""

        # ── Location ────────────────────────────────────────────────────────
        location_filter = filters.get("location")
        if location_filter:
            listing_location = (listing.get("location") or "").lower()
            listing_title = (listing.get("title") or "").lower()
            keywords = [k.strip().lower() for k in re.split(r"[,;|]", location_filter) if k.strip()]
            if not any(kw in listing_location or kw in listing_title for kw in keywords):
                return False

        # ── Rooms ────────────────────────────────────────────────────────────
        rooms_filter = filters.get("rooms")
        if rooms_filter is not None:
            listing_rooms = listing.get("rooms")
            if listing_rooms is not None:
                allowed_rooms = self._parse_rooms_filter(str(rooms_filter))
                if allowed_rooms and listing_rooms not in allowed_rooms:
                    return False

        # ── Price ────────────────────────────────────────────────────────────
        price_min = filters.get("price_min")
        price_max = filters.get("price_max")
        listing_price = listing.get("price")

        if price_min is not None and listing_price is not None:
            if listing_price < int(price_min):
                return False

        if price_max is not None and listing_price is not None:
            if listing_price > int(price_max):
                return False

        # ── Size ─────────────────────────────────────────────────────────────
        size_min = filters.get("size_min")
        size_max = filters.get("size_max")
        listing_size = listing.get("size")

        if size_min is not None and listing_size is not None:
            if float(listing_size) < float(size_min):
                return False

        if size_max is not None and listing_size is not None:
            if float(listing_size) > float(size_max):
                return False

        return True

    def _parse_rooms_filter(self, text: str) -> set[int]:
        """Parse rooms filter: '2', '3', '2,3', '2-4'."""
        rooms = set()
        # Range: 2-4
        range_m = re.match(r"^(\d+)\s*-\s*(\d+)$", text.strip())
        if range_m:
            start, end = int(range_m.group(1)), int(range_m.group(2))
            return set(range(start, end + 1))
        # List: 2,3,4
        for part in re.split(r"[,;\s]+", text):
            try:
                rooms.add(int(part.strip()))
            except ValueError:
                pass
        return rooms
