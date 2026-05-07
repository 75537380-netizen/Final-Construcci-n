"""
Unit tests for CheapSharkService.

Validates historical-low lookups, appid matching, price formatting,
and graceful degradation on API errors.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

import httpx

from app.services.cheapshark import CheapSharkService


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(mock_client):
    return CheapSharkService(mock_client)


def make_response(json_data):
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.return_value = json_data
    return mock


# ---------------------------------------------------------------------------
# get_historical_low
# ---------------------------------------------------------------------------

class TestGetHistoricalLow:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_games_found(self, service, mock_client):
        mock_client.get.return_value = make_response([])
        result = await service.get_historical_low("Unknown Game XYZ 12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_request_error(self, service, mock_client):
        mock_client.get.side_effect = httpx.RequestError("connection refused")
        result = await service.get_historical_low("Some Game")
        assert result is None

    @pytest.mark.asyncio
    async def test_prefers_match_by_steam_appid(self, service, mock_client):
        search_resp = make_response([
            {"gameID": "1", "steamAppID": "111", "external": "Other Game"},
            {"gameID": "2", "steamAppID": "570", "external": "Dota 2"},
        ])
        details_resp = make_response({
            "info": {"title": "Dota 2"},
            "cheapestPriceEver": {"price": "0.00", "date": 1424289600},
            "deals": [],
        })
        mock_client.get.side_effect = [search_resp, details_resp]

        result = await service.get_historical_low("Dota 2", "570")
        # Verify the second API call used gameID "2" (the Dota 2 match)
        second_call_params = mock_client.get.call_args_list[1][1]["params"]
        assert second_call_params == {"id": "2"}

    @pytest.mark.asyncio
    async def test_formats_price_correctly(self, service, mock_client):
        mock_client.get.side_effect = [
            make_response([{"gameID": "42", "steamAppID": "1091500", "external": "Cyberpunk 2077"}]),
            make_response({
                "cheapestPriceEver": {"price": "17.99", "date": 1670000000},
                "deals": [],
            }),
        ]
        result = await service.get_historical_low("Cyberpunk 2077", "1091500")
        assert result["price"] == pytest.approx(17.99)
        assert result["formatted"] == "$17.99"
        assert result["date"] == 1670000000

    @pytest.mark.asyncio
    async def test_free_game_historical_low_is_zero(self, service, mock_client):
        mock_client.get.side_effect = [
            make_response([{"gameID": "99", "steamAppID": "730", "external": "CS2"}]),
            make_response({
                "cheapestPriceEver": {"price": "0.00", "date": 1400000000},
                "deals": [],
            }),
        ]
        result = await service.get_historical_low("Counter-Strike 2", "730")
        assert result["price"] == pytest.approx(0.0)
        assert result["formatted"] == "$0.00"

    @pytest.mark.asyncio
    async def test_returns_none_when_cheapest_price_missing(self, service, mock_client):
        mock_client.get.side_effect = [
            make_response([{"gameID": "77", "steamAppID": "12345", "external": "Some Game"}]),
            make_response({"cheapestPriceEver": {}, "deals": []}),
        ]
        result = await service.get_historical_low("Some Game", "12345")
        assert result is None

    @pytest.mark.asyncio
    async def test_falls_back_to_first_result_when_no_appid_match(self, service, mock_client):
        mock_client.get.side_effect = [
            make_response([
                {"gameID": "10", "steamAppID": "111", "external": "First Game"},
                {"gameID": "20", "steamAppID": "222", "external": "Second Game"},
            ]),
            make_response({
                "cheapestPriceEver": {"price": "4.99", "date": 1500000000},
                "deals": [],
            }),
        ]
        result = await service.get_historical_low("First Game")
        second_call_params = mock_client.get.call_args_list[1][1]["params"]
        assert second_call_params == {"id": "10"}
        assert result["price"] == pytest.approx(4.99)


# ---------------------------------------------------------------------------
# _best_match (unit)
# ---------------------------------------------------------------------------

class TestBestMatch:
    def test_matches_by_steam_appid(self, service):
        games = [
            {"gameID": "1", "steamAppID": "100"},
            {"gameID": "2", "steamAppID": "200"},
        ]
        result = service._best_match(games, "200")
        assert result["gameID"] == "2"

    def test_returns_first_when_no_appid_given(self, service):
        games = [
            {"gameID": "1", "steamAppID": "100"},
            {"gameID": "2", "steamAppID": "200"},
        ]
        result = service._best_match(games, None)
        assert result["gameID"] == "1"

    def test_falls_back_to_first_when_appid_not_found(self, service):
        games = [{"gameID": "1", "steamAppID": "100"}]
        result = service._best_match(games, "999")
        assert result["gameID"] == "1"

    def test_returns_none_for_empty_list(self, service):
        result = service._best_match([], "570")
        assert result is None
