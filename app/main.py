from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.services.cheapshark import CheapSharkService
from app.services.steam import SteamService, GENRE_SECTIONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(12.0, connect=5.0),
        headers={"User-Agent": "SteamPriceChecker/1.0"},
        follow_redirects=True,
    )
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="Steam Price Checker", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    with open("app/static/index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/search")
async def search_games(
    request: Request,
    q: str = Query(..., min_length=2),
    cc: str = Query("US"),
):
    service = SteamService(request.app.state.http_client)
    results = await service.search(q, cc)
    return {"results": results, "query": q, "count": len(results)}


@app.get("/api/game/{appid}")
async def get_game(appid: int, request: Request, cc: str = Query("US")):
    steam      = SteamService(request.app.state.http_client)
    cheapshark = CheapSharkService(request.app.state.http_client)

    game = await steam.get_details(appid, cc)
    if not game:
        raise HTTPException(status_code=404, detail="Juego no encontrado")

    game["historical_low"] = await cheapshark.get_historical_low(game["name"], str(appid))
    return game


@app.get("/api/featured-deals")
async def featured_deals(
    request: Request,
    category: str = Query("top_sellers"),
    cc: str = Query("US"),
    start: int = Query(0, ge=0),
    tags: str = Query(""),
):
    service = SteamService(request.app.state.http_client)
    if tags:
        data = await service.search_by_tags(tags, cc, start, category)
    elif category == "specials":
        data = await service.get_specials(cc, start)
    else:
        data = await service.get_category(category, cc, start)
    return {"deals": data["results"], "total_count": data["total_count"], "count": len(data["results"]), "category": category}


@app.get("/api/deals")
async def paginated_deals(
    request: Request,
    page: int = Query(0, ge=0),
    page_size: int = Query(24, ge=1, le=48),
    cc: str = Query("US"),
):
    """Ofertas de Steam con paginacion y moneda regional."""
    steam = SteamService(request.app.state.http_client)
    data = await steam.get_specials(cc, page * page_size, page_size)
    deals = data["results"]
    return {"deals": deals, "page": page, "count": len(deals)}


@app.get("/api/genre")
async def browse_by_genre(
    request: Request,
    tags: str = Query(..., description="Comma-separated Steam tag IDs, e.g. '19' or '19,122'"),
    cc: str = Query("US"),
    start: int = Query(0, ge=0),
):
    service = SteamService(request.app.state.http_client)
    data = await service.search_by_tags(tags, cc, start)
    return {"results": data["results"], "total_count": data["total_count"], "count": len(data["results"])}


@app.get("/api/genres")
async def get_genres():
    return GENRE_SECTIONS


app.mount("/static", StaticFiles(directory="app/static"), name="static")
