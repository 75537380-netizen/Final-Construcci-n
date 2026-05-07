"""
Unit tests for SteamService.

Principle: each test exercises a single behavior of the service in isolation,
using mocked HTTP responses so no real network calls are made.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from app.services.steam import SteamService


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(mock_client):
    return SteamService(mock_client)


def make_response(json_data: dict | list, status_code: int = 200):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    return mock


# ---------------------------------------------------------------------------
# _parse_price
# ---------------------------------------------------------------------------

class TestParsePrice:
    def test_empty_dict_returns_defaults(self, service):
        result = service._parse_price({})
        assert result["discount"] == 0
        assert result["is_on_sale"] is False
        assert result["display"] == "N/A"

    def test_discounted_game_is_on_sale(self, service):
        price = {
            "currency": "USD",
            "initial": 2999,
            "final": 1499,
            "discount_percent": 50,
            "initial_formatted": "$29.99",
            "final_formatted": "$14.99",
        }
        result = service._parse_price(price)
        assert result["is_on_sale"] is True
        assert result["discount"] == 50
        assert result["final"] == pytest.approx(14.99)
        assert result["initial"] == pytest.approx(29.99)

    def test_full_price_not_on_sale(self, service):
        price = {
            "currency": "USD",
            "initial": 1999,
            "final": 1999,
            "discount_percent": 0,
            "final_formatted": "$19.99",
        }
        result = service._parse_price(price)
        assert result["is_on_sale"] is False
        assert result["discount"] == 0
        assert result["final"] == pytest.approx(19.99)

    def test_price_converts_cents_to_dollars(self, service):
        price = {"initial": 5999, "final": 5999, "discount_percent": 0}
        result = service._parse_price(price)
        assert result["final"] == pytest.approx(59.99)
        assert result["initial"] == pytest.approx(59.99)

    def test_currency_is_preserved(self, service):
        price = {"currency": "BRL", "initial": 9999, "final": 4999, "discount_percent": 50}
        result = service._parse_price(price)
        assert result["currency"] == "BRL"


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:
    @pytest.mark.asyncio
    async def test_returns_only_app_type_items(self, service, mock_client):
        mock_client.get.return_value = make_response({
            "items": [
                {"type": "app", "id": 570, "name": "Dota 2", "tiny_image": "", "price": {}},
                {"type": "bundle", "id": 99, "name": "Bundle", "tiny_image": "", "price": {}},
                {"type": "app", "id": 730, "name": "CS2", "tiny_image": "", "price": {}},
            ]
        })
        results = await service.search("dota")
        assert len(results) == 2
        assert all(r["appid"] in (570, 730) for r in results)

    @pytest.mark.asyncio
    async def test_result_contains_expected_keys(self, service, mock_client):
        mock_client.get.return_value = make_response({
            "items": [
                {
                    "type": "app",
                    "id": 730,
                    "name": "Counter-Strike 2",
                    "tiny_image": "https://cdn.example.com/img.jpg",
                    "price": {"currency": "USD", "initial": 0, "final": 0, "discount_percent": 0},
                }
            ]
        })
        results = await service.search("cs2")
        assert results[0]["appid"] == 730
        assert results[0]["name"] == "Counter-Strike 2"
        assert "price" in results[0]
        assert "image" in results[0]

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_http_error(self, service, mock_client):
        mock_client.get.side_effect = httpx.RequestError("timeout")
        results = await service.search("anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_items(self, service, mock_client):
        mock_client.get.return_value = make_response({"items": []})
        results = await service.search("xyznotexist")
        assert results == []


# ---------------------------------------------------------------------------
# get_details
# ---------------------------------------------------------------------------

class TestGetDetails:
    @pytest.mark.asyncio
    async def test_returns_none_when_success_false(self, service, mock_client):
        mock_client.get.return_value = make_response({"999999": {"success": False}})
        result = await service.get_details(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_parses_game_fields(self, service, mock_client):
        mock_client.get.return_value = make_response({
            "570": {
                "success": True,
                "data": {
                    "name": "Dota 2",
                    "steam_appid": 570,
                    "header_image": "https://cdn.example.com/header.jpg",
                    "is_free": True,
                    "genres": [{"id": "1", "description": "Action"}],
                    "developers": ["Valve"],
                    "publishers": ["Valve"],
                    "short_description": "A MOBA game.",
                    "release_date": {"date": "9 Jul, 2013"},
                }
            }
        })
        result = await service.get_details(570)
        assert result["name"] == "Dota 2"
        assert result["is_free"] is True
        assert result["genres"] == ["Action"]
        assert result["developers"] == ["Valve"]
        assert result["price"]["display"] == "Gratis"

    @pytest.mark.asyncio
    async def test_steam_url_is_constructed_correctly(self, service, mock_client):
        mock_client.get.return_value = make_response({
            "1091500": {
                "success": True,
                "data": {
                    "name": "Cyberpunk 2077",
                    "steam_appid": 1091500,
                    "header_image": "",
                    "is_free": False,
                    "genres": [],
                    "developers": ["CD PROJEKT RED"],
                    "publishers": [],
                    "short_description": "RPG game.",
                    "release_date": {"date": "10 Dec, 2020"},
                    "price_overview": {
                        "currency": "USD",
                        "initial": 5999,
                        "final": 2999,
                        "discount_percent": 50,
                        "final_formatted": "$29.99",
                    },
                }
            }
        })
        result = await service.get_details(1091500)
        assert result["steam_url"] == "https://store.steampowered.com/app/1091500/"
        assert result["price"]["discount"] == 50

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self, service, mock_client):
        mock_client.get.side_effect = httpx.RequestError("network error")
        result = await service.get_details(570)
        assert result is None


# ---------------------------------------------------------------------------
# search_by_tags
# ---------------------------------------------------------------------------

class TestSearchByTags:
    @pytest.mark.asyncio
    async def test_returns_correct_games_for_tag(self, service, mock_client):
        html = (
            '<a data-ds-appid="1234">'
            '<span class="title">Speed Racer</span>'
            '<div class="col search_price  responsive_secondrow">$14.99</div>'
            '</a>'
        )
        mock_client.get.return_value = make_response({
            "total_count": 1, "start": 0, "pagesize": 24,
            "results_html": html,
        })
        data = await service.search_by_tags("699")
        assert data["total_count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["appid"] == 1234
        assert data["results"][0]["name"] == "Speed Racer"

    @pytest.mark.asyncio
    async def test_skips_bundle_appids(self, service, mock_client):
        html = (
            '<a data-ds-appid="1,2">'
            '<span class="title">Bundle</span>'
            '</a>'
            '<a data-ds-appid="3456">'
            '<span class="title">Solo Game</span>'
            '<div class="col search_price  responsive_secondrow">$9.99</div>'
            '</a>'
        )
        mock_client.get.return_value = make_response({
            "total_count": 1, "start": 0, "pagesize": 24,
            "results_html": html,
        })
        data = await service.search_by_tags("19")
        assert len(data["results"]) == 1
        assert data["results"][0]["appid"] == 3456

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self, service, mock_client):
        mock_client.get.side_effect = httpx.RequestError("timeout")
        data = await service.search_by_tags("699")
        assert data == {"results": [], "total_count": 0}
