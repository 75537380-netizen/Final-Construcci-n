import httpx
from typing import Optional

GAMES_URL = "https://www.cheapshark.com/api/1.0/games"
DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"


class CheapSharkService:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def get_historical_low(
        self, game_name: str, steam_appid: Optional[str] = None
    ) -> Optional[dict]:
        try:
            params = {"title": game_name, "limit": 10}
            if steam_appid:
                params["steamAppID"] = steam_appid

            r = await self.client.get(GAMES_URL, params=params)
            r.raise_for_status()
            games = r.json()
            if not games:
                return None

            game = self._best_match(games, steam_appid)
            if not game:
                return None

            details_r = await self.client.get(GAMES_URL, params={"id": game["gameID"]})
            details_r.raise_for_status()
            details = details_r.json()

            cheapest = details.get("cheapestPriceEver", {})
            if not cheapest or cheapest.get("price") is None:
                return None

            price = float(cheapest["price"])
            return {
                "price":     price,
                "formatted": f"${price:.2f}",
                "currency":  "USD",
                "date":      cheapest.get("date"),
            }
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            return None

    async def get_deals_page(self, page: int = 0, page_size: int = 24) -> list[dict]:
        """Paginated Steam deals sorted by deal rating (real infinite pagination)."""
        try:
            r = await self.client.get(DEALS_URL, params={
                "storeID":    "1",
                "sortBy":     "DealRating",
                "pageNumber": page,
                "pageSize":   page_size,
                "onSale":     1,
            })
            r.raise_for_status()
            deals = r.json()
            results = []
            for d in deals:
                sale   = float(d.get("salePrice",   "0") or "0")
                normal = float(d.get("normalPrice", "0") or "0")
                discount = round((1 - sale / normal) * 100) if normal > 0 else 0
                results.append({
                    "appid": int(d["steamAppID"]) if d.get("steamAppID") else 0,
                    "name":  d.get("title", ""),
                    "image": d.get("thumb", ""),
                    "price": {
                        "currency":          "USD",
                        "initial":           normal,
                        "final":             sale,
                        "discount":          discount,
                        "is_on_sale":        discount > 0,
                        "initial_formatted": f"${normal:.2f}",
                        "final_formatted":   f"${sale:.2f}",
                        "display":           f"${sale:.2f}",
                        "is_free":           sale == 0 and normal == 0,
                    },
                })
            return results
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            return []

    def _best_match(self, games: list[dict], steam_appid: Optional[str]) -> Optional[dict]:
        if steam_appid:
            for g in games:
                if g.get("steamAppID") == steam_appid:
                    return g
        return games[0] if games else None
