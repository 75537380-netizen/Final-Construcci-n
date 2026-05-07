from pydantic import BaseModel
from typing import Optional


class PriceInfo(BaseModel):
    currency: str = "USD"
    initial: float = 0.0
    final: float = 0.0
    discount: int = 0
    is_on_sale: bool = False
    initial_formatted: str = ""
    final_formatted: str = ""
    display: str = "N/A"
    is_free: bool = False


class HistoricalLow(BaseModel):
    price: float
    formatted: str
    date: Optional[int] = None


class GameSummary(BaseModel):
    appid: int
    name: str
    image: str = ""
    price: PriceInfo


class GameDetail(BaseModel):
    appid: int
    name: str
    header_image: str = ""
    short_description: str = ""
    is_free: bool = False
    genres: list[str] = []
    developers: list[str] = []
    steam_url: str = ""
    metacritic: Optional[int] = None
    price: PriceInfo
    historical_low: Optional[HistoricalLow] = None
