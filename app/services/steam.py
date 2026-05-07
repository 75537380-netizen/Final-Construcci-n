import re
from html import unescape as _unescape

import httpx
from typing import Optional

SEARCH_URL        = "https://store.steampowered.com/api/storesearch/"
DETAILS_URL       = "https://store.steampowered.com/api/appdetails"
STORE_SEARCH_URL  = "https://store.steampowered.com/search/results/"
STORE_PAGE_URL    = "https://store.steampowered.com/search/"

# Steam's search/results endpoint requires a browser-like UA to return results
BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://store.steampowered.com/search/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

CATEGORY_FILTERS: dict[str, str] = {
    "top_sellers":  "topsellers",
    "new_releases": "newreleases",
    "coming_soon":  "comingsoon",
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",   "PEN": "S/",  "ARS": "$",   "BRL": "R$",
    "MXN": "$",   "CLP": "$",   "GBP": "£",   "EUR": "€",
    "AUD": "A$",  "CAD": "C$",  "COP": "$",   "UYU": "$",
}

CC_TO_CURRENCY: dict[str, str] = {
    "US": "USD", "PE": "PEN", "AR": "ARS", "BR": "BRL",
    "MX": "MXN", "CL": "CLP", "GB": "GBP", "DE": "EUR",
    "AU": "AUD", "CA": "CAD",
}

GENRE_SECTIONS = [
    {
        "section": "Géneros Principales",
        "items": [
            {"key": "accion",      "label": "Acción",       "tag": 19,   "icon": "🗡️"},
            {"key": "aventura",    "label": "Aventura",     "tag": 25,   "icon": "🗺️"},
            {"key": "rpg",         "label": "RPG",          "tag": 122,  "icon": "⚔️"},
            {"key": "estrategia",  "label": "Estrategia",   "tag": 9,    "icon": "♟️"},
            {"key": "simulacion",  "label": "Simulación",   "tag": 599,  "icon": "🛸"},
            {"key": "deportes",    "label": "Deportes",     "tag": 701,  "icon": "⚽"},
            {"key": "carreras",    "label": "Carreras",     "tag": 699,  "icon": "🏎️"},
            {"key": "casual",      "label": "Casual",       "tag": 597,  "icon": "🎲"},
            {"key": "indie",       "label": "Indie",        "tag": 492,  "icon": "🎨"},
        ],
    },
    {
        "section": "Shooter & Combate",
        "items": [
            {"key": "shooter",      "label": "Shooter",       "tag": 1774, "icon": "🔫"},
            {"key": "fps",          "label": "FPS",           "tag": 1155, "icon": "🎯"},
            {"key": "combate",      "label": "Combate",       "tag": 1743, "icon": "🥊"},
            {"key": "battle_royale","label": "Battle Royale", "tag": 1201, "icon": "🪖"},
            {"key": "moba",         "label": "MOBA",          "tag": 1446, "icon": "🏆"},
        ],
    },
    {
        "section": "Terror & Supervivencia",
        "items": [
            {"key": "terror",       "label": "Terror",           "tag": 834,  "icon": "👻"},
            {"key": "supervivencia","label": "Supervivencia",    "tag": 1662, "icon": "🪓"},
            {"key": "zombies",      "label": "Zombies",          "tag": 1032, "icon": "🧟"},
            {"key": "mundo_abierto","label": "Mundo Abierto",    "tag": 1695, "icon": "🌍"},
            {"key": "sandbox",      "label": "Sandbox",          "tag": 3826, "icon": "🏗️"},
        ],
    },
    {
        "section": "Plataformas & Puzzle",
        "items": [
            {"key": "plataformas",   "label": "Plataformas",    "tag": 1625, "icon": "🕹️"},
            {"key": "metroidvania",  "label": "Metroidvania",   "tag": 1110, "icon": "🗝️"},
            {"key": "puzzle",        "label": "Puzzle",         "tag": 1664, "icon": "🧩"},
            {"key": "roguelike",     "label": "Roguelike",      "tag": 3959, "icon": "🎰"},
            {"key": "historia",      "label": "Historia Rica",  "tag": 1742, "icon": "📖"},
        ],
    },
    {
        "section": "Estrategia Avanzada",
        "items": [
            {"key": "rts",           "label": "Estrategia RT",  "tag": 1693, "icon": "⚡"},
            {"key": "tower_defense", "label": "Tower Defense",  "tag": 534,  "icon": "🏰"},
            {"key": "jrpg",          "label": "JRPG",           "tag": 4434, "icon": "🌸"},
            {"key": "turno",         "label": "Por Turnos",     "tag": 1716, "icon": "🎯"},
            {"key": "4x",            "label": "4X",             "tag": 1720, "icon": "🗺️"},
        ],
    },
    {
        "section": "Multijugador & Online",
        "items": [
            {"key": "multijugador",  "label": "Multijugador",   "tag": 3859, "icon": "👥"},
            {"key": "cooperativo",   "label": "Cooperativo",    "tag": 3843, "icon": "🤝"},
            {"key": "pvp",           "label": "PvP",            "tag": 1673, "icon": "⚔️"},
            {"key": "mmo",           "label": "MMO",            "tag": 1752, "icon": "🌐"},
        ],
    },
    {
        "section": "Arte & Estilo",
        "items": [
            {"key": "anime",         "label": "Anime",          "tag": 4085, "icon": "🌺"},
            {"key": "pixel_art",     "label": "Pixel Art",      "tag": 1702, "icon": "🖼️"},
            {"key": "visual_novel",  "label": "Visual Novel",   "tag": 1029, "icon": "📝"},
            {"key": "atmospheric",   "label": "Atmosférico",    "tag": 4736, "icon": "🌫️"},
        ],
    },
]


class SteamService:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def search(self, query: str, cc: str = "US") -> list[dict]:
        try:
            r = await self.client.get(
                SEARCH_URL, params={"term": query, "l": "spanish", "cc": cc}
            )
            r.raise_for_status()
        except httpx.HTTPError:
            return []
        return self._parse_items(r.json().get("items", []))

    async def _store_search(self, params: list[tuple]) -> tuple[list[dict], int]:
        """Shared helper: call Steam search and parse priced HTML results."""
        try:
            r = await self.client.get(STORE_SEARCH_URL, params=params, headers=BROWSER_HEADERS)
            r.raise_for_status()
            data = r.json()
            html = data.get("results_html", "")
            if html:
                count = next((int(v) for k, v in params if k == "count"), 24)
                return self._parse_search_html(html)[:count], data.get("total_count", 0)
        except Exception:
            pass

        try:
            page_params = [(k, v) for k, v in params if k not in {"json", "start", "count"}]
            start = next((int(v) for k, v in params if k == "start"), 0)
            count = next((int(v) for k, v in params if k == "count"), 24)
            page_params.append(("page", (start // count) + 1))
            r = await self.client.get(STORE_PAGE_URL, params=page_params, headers=BROWSER_HEADERS)
            r.raise_for_status()
            html = r.text
        except Exception:
            return [], 0
        return self._parse_search_html(html)[:count], self._parse_total_count(html)

    async def search_by_tags(self, tags: str, cc: str = "US", start: int = 0, category: str = "") -> dict:
        """Tag-filtered store search, optionally combined with a category filter. Returns {results, total_count}."""
        params: list[tuple] = [
            ("query", ""), ("start", start), ("count", 24),
            ("sort_by", "_ASC"), ("json", 1), ("cc", cc),
        ]
        filter_name = CATEGORY_FILTERS.get(category)
        if filter_name:
            params.append(("filter", filter_name))
        elif category == "specials":
            params.append(("specials", 1))
        for tag_id in tags.split(","):
            tag_id = tag_id.strip()
            if tag_id:
                params.append(("tags", tag_id))
        results, total = await self._store_search(params)
        return {"results": results, "total_count": total}

    async def get_specials(self, cc: str = "US", start: int = 0, count: int = 24) -> dict:
        params: list[tuple] = [
            ("query", ""), ("start", start), ("count", count),
            ("sort_by", "_ASC"), ("specials", 1), ("json", 1),
            ("cc", cc), ("l", "spanish"),
        ]
        results, total = await self._store_search(params)
        return {"results": results, "total_count": total}

    async def get_category(self, category: str = "top_sellers", cc: str = "US", start: int = 0) -> dict:
        """Browse a category (top_sellers / new_releases / coming_soon). Returns {results, total_count}."""
        filter_name = CATEGORY_FILTERS.get(category)
        if not filter_name:
            return {"results": [], "total_count": 0}
        try:
            r = await self.client.get(
                SEARCH_URL,
                params={"term": "", "filter": filter_name, "cc": cc, "l": "spanish", "start": start},
            )
            r.raise_for_status()
            data = r.json()
        except Exception:
            return {"results": [], "total_count": 0}
        return {
            "results": self._parse_items(data.get("items", [])),
            "total_count": data.get("total", len(data.get("items", []))),
        }

    def _parse_search_html(self, html: str) -> list[dict]:
        results: list[dict] = []
        seen: set[int] = set()
        for m in re.finditer(r'data-ds-appid="([\d,]+)"', html):
            raw_id = m.group(1)
            if "," in raw_id:   # skip bundles
                continue
            appid = int(raw_id)
            if appid in seen:
                continue
            seen.add(appid)
            # Slice up to the next app entry for isolated parsing
            rest = html[m.end():]
            nxt = re.search(r'data-ds-appid=', rest)
            chunk = html[m.start(): m.end() + (nxt.start() if nxt else 2000)]
            title_m = re.search(r'<span class="title">([^<]+)</span>', chunk)
            if not title_m:
                continue
            name = _unescape(title_m.group(1).strip())
            img_m = re.search(r'<div class="search_capsule">\s*<img src="([^"]+)"', chunk)
            image = _unescape(img_m.group(1).strip()) if img_m else ""
            results.append({
                "appid": appid,
                "name":  name,
                "image": image or f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg",
                "price": self._price_from_search_chunk(chunk),
            })
        return results

    def _parse_total_count(self, html: str) -> int:
        m = re.search(r'([\d.,]+)\s+resultados', html, re.I)
        if not m:
            m = re.search(r'([\d.,]+)\s+results', html, re.I)
        if not m:
            return 0
        return int(re.sub(r"\D", "", m.group(1)) or 0)

    def _price_from_search_chunk(self, chunk: str) -> dict:
        empty: dict = {
            "currency": "USD", "initial": 0.0, "final": 0.0, "discount": 0,
            "is_on_sale": False, "is_free": False,
            "initial_formatted": "", "final_formatted": "", "display": "",
        }
        final_m = re.search(r'class="discount_final_price">([^<]+)</div>', chunk)
        if final_m:
            initial_m = re.search(r'class="discount_original_price">([^<]+)</div>', chunk)
            disc_m = re.search(r'class="discount_pct">-(\d+)%</div>', chunk)
            final_str = _unescape(final_m.group(1).strip())
            initial_str = _unescape(initial_m.group(1).strip()) if initial_m else ""
            discount = int(disc_m.group(1)) if disc_m else 0
            return {
                **empty,
                "discount": discount,
                "is_on_sale": discount > 0,
                "initial_formatted": initial_str,
                "final_formatted": final_str,
                "display": final_str,
            }

        pb = re.search(r'class="[^"]*search_price[^"]*"[^>]*>(.*?)</div>', chunk, re.DOTALL)
        if not pb:
            return empty
        price_html = pb.group(1)
        flat = " ".join(_unescape(re.sub(r"<[^>]+>", " ", price_html)).split())
        if not flat:
            return empty
        if re.search(r"\bfree\b|gratis", flat, re.I):
            return {**empty, "display": "Gratis", "is_free": True,
                    "initial_formatted": "Gratis", "final_formatted": "Gratis"}
        # Discount % lives in a sibling div
        disc_m = re.search(r'search_discount[^"]*"[^>]*>\s*<span>-(\d+)%', chunk)
        discount = int(disc_m.group(1)) if disc_m else 0
        # Original (struck-through) price
        strike_m = re.search(r"<strike>([^<]+)</strike>", price_html)
        initial_str = _unescape(strike_m.group(1).strip()) if strike_m else ""
        # Final price: text after removing strike tags
        final_html = re.sub(r"<strike>.*?</strike>", "", price_html, flags=re.DOTALL)
        final_str = " ".join(_unescape(re.sub(r"<[^>]+>", "", final_html)).split())
        display = final_str or flat
        return {
            **empty,
            "discount": discount,
            "is_on_sale": discount > 0,
            "initial_formatted": initial_str,
            "final_formatted": final_str or display,
            "display": display,
        }

    async def get_details(self, appid: int, cc: str = "US") -> Optional[dict]:
        try:
            r = await self.client.get(
                DETAILS_URL, params={"appids": appid, "cc": cc, "l": "spanish"}
            )
            r.raise_for_status()
        except httpx.HTTPError:
            return None

        payload = r.json().get(str(appid), {})
        if not payload.get("success"):
            return None

        data = payload["data"]
        return {
            "appid": appid,
            "name": data["name"],
            "header_image": data.get("header_image", ""),
            "short_description": data.get("short_description", ""),
            "is_free": data.get("is_free", False),
            "genres": [g["description"] for g in data.get("genres", [])],
            "developers": data.get("developers", []),
            "publishers": data.get("publishers", []),
            "steam_url": f"https://store.steampowered.com/app/{appid}/",
            "metacritic": data.get("metacritic", {}).get("score"),
            "release_date": data.get("release_date", {}).get("date", ""),
            "price": self._parse_price(data.get("price_overview", {}))
            if not data.get("is_free")
            else {
                "currency": CC_TO_CURRENCY.get(cc, "USD"),
                "is_free": True, "display": "Gratis",
                "discount": 0, "is_on_sale": False, "final": 0, "initial": 0,
                "initial_formatted": "Gratis", "final_formatted": "Gratis",
            },
        }

    # -------------------------------------------------------------------------
    def _parse_items(self, items: list) -> list[dict]:
        results = []
        for item in items:
            if item.get("type") != "app":
                continue
            results.append({
                "appid": item["id"],
                "name":  item["name"],
                "image": item.get("tiny_image", ""),
                "price": self._parse_price(item.get("price", {})),
            })
        return results

    def _parse_price(self, p: dict) -> dict:
        if not p:
            return {
                "currency": "USD", "initial": 0.0, "final": 0.0, "discount": 0,
                "is_on_sale": False, "initial_formatted": "",
                "final_formatted": "", "display": "N/A", "is_free": False,
            }
        discount      = p.get("discount_percent", 0)
        final_cents   = p.get("final", 0)
        initial_cents = p.get("initial", 0)
        currency      = p.get("currency", "USD")
        symbol        = CURRENCY_SYMBOLS.get(currency, "$")
        return {
            "currency": currency,
            "initial":  initial_cents / 100,
            "final":    final_cents / 100,
            "discount": discount,
            "is_on_sale": discount > 0,
            "initial_formatted": p.get("initial_formatted") or f"{symbol}{initial_cents / 100:.2f}",
            "final_formatted":   p.get("final_formatted")   or f"{symbol}{final_cents / 100:.2f}",
            "display":           p.get("final_formatted")   or f"{symbol}{final_cents / 100:.2f}",
            "is_free": False,
        }
