"""
Tests for NSEFetcher — NSE v3 API client + parser + validator.

TDD: Written FIRST, before the implementation.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.options.nse_fetcher import (
    NSEFetcher,
    NSEFetchError,
    NSEValidationError,
)


# ─── Fixture Data ──────────────────────────────────────────────────────────────

def _make_nse_v3_response(
    spot=24500.0,
    num_strikes=60,
    base_strike=24000,
    step=100,
    ce_oi=500000,
    pe_oi=300000,
):
    """Build a realistic NSE v3 API response dict."""
    data = []
    for i in range(num_strikes):
        strike = base_strike + i * step
        data.append({
            "strikePrice": strike,
            "expiryDate": "16-Apr-2026",
            "CE": {
                "openInterest": max(0, ce_oi - i * 5000) if ce_oi else 0,
                "lastPrice": max(0.05, spot - strike + 50) if strike <= spot else max(0.05, 50 - (strike - spot) * 0.5),
                "totalTradedVolume": max(0, 12000 - i * 100),
                "impliedVolatility": 18.5 + i * 0.1,
                "changeinOpenInterest": 1000,
            },
            "PE": {
                "openInterest": max(0, pe_oi + i * 3000) if pe_oi else 0,
                "lastPrice": max(0.05, strike - spot + 50) if strike >= spot else max(0.05, 50 - (spot - strike) * 0.5),
                "totalTradedVolume": max(0, 8000 + i * 50),
                "impliedVolatility": max(0, 22.1 - i * 0.05),
                "changeinOpenInterest": -500,
            },
        })
    return {
        "records": {
            "expiryDates": ["16-Apr-2026", "23-Apr-2026", "30-Apr-2026"],
            "underlyingValue": spot,
            "data": data,
        },
        "filtered": {
            "data": data,
            "underlyingValue": spot,
        },
    }


def _make_nse_response_missing_ce(spot=24500.0):
    """Response with a strike that has no CE data."""
    return {
        "records": {
            "expiryDates": ["16-Apr-2026"],
            "underlyingValue": spot,
            "data": [
                {
                    "strikePrice": 24000,
                    "CE": {"openInterest": 100000, "lastPrice": 550, "totalTradedVolume": 5000, "impliedVolatility": 18},
                    "PE": {"openInterest": 80000, "lastPrice": 50, "totalTradedVolume": 3000, "impliedVolatility": 22},
                },
                {
                    "strikePrice": 24100,
                    "CE": None,  # Missing CE
                    "PE": {"openInterest": 90000, "lastPrice": 40, "totalTradedVolume": 2000, "impliedVolatility": 21},
                },
            ] + [
                {
                    "strikePrice": 24200 + i * 100,
                    "CE": {"openInterest": 50000, "lastPrice": 100, "totalTradedVolume": 1000, "impliedVolatility": 17},
                    "PE": {"openInterest": 40000, "lastPrice": 60, "totalTradedVolume": 800, "impliedVolatility": 20},
                }
                for i in range(58)  # Pad to 60 total
            ],
        },
    }


# ─── Tests ──────────────────────────────────────────────────────────────────────

class TestFormatExpiry:

    def test_format_expiry_standard_date(self):
        fetcher = NSEFetcher()
        assert fetcher._format_expiry(date(2026, 4, 17)) == "17-Apr-2026"

    def test_format_expiry_single_digit_day(self):
        fetcher = NSEFetcher()
        assert fetcher._format_expiry(date(2026, 1, 5)) == "05-Jan-2026"

    def test_format_expiry_december(self):
        fetcher = NSEFetcher()
        assert fetcher._format_expiry(date(2026, 12, 25)) == "25-Dec-2026"


class TestParseNseResponse:

    def test_extracts_all_fields(self):
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response(spot=24500.0, num_strikes=3)
        result = fetcher.parse_nse_response(raw)

        assert result["spot_price"] == Decimal("24500")
        assert len(result["strikes"]) == 3

        # Check first strike has all fields
        first_strike = Decimal("24000")
        assert first_strike in result["strikes"]
        s = result["strikes"][first_strike]
        assert "ce_ltp" in s
        assert "ce_oi" in s
        assert "ce_volume" in s
        assert "ce_iv" in s
        assert "pe_ltp" in s
        assert "pe_oi" in s
        assert "pe_volume" in s
        assert "pe_iv" in s

    def test_handles_missing_ce(self):
        fetcher = NSEFetcher()
        raw = _make_nse_response_missing_ce()
        result = fetcher.parse_nse_response(raw)

        strike_24100 = Decimal("24100")
        assert strike_24100 in result["strikes"]
        s = result["strikes"][strike_24100]
        assert s["ce_oi"] == 0
        assert s["ce_ltp"] == Decimal("0")
        assert s["ce_volume"] == 0
        assert s["ce_iv"] == Decimal("0")
        # PE should still be populated
        assert s["pe_oi"] == 90000

    def test_handles_missing_pe(self):
        fetcher = NSEFetcher()
        raw = {
            "records": {
                "expiryDates": ["16-Apr-2026"],
                "underlyingValue": 24500.0,
                "data": [
                    {
                        "strikePrice": 24000,
                        "CE": {"openInterest": 100000, "lastPrice": 550, "totalTradedVolume": 5000, "impliedVolatility": 18},
                        "PE": None,
                    },
                ] + [
                    {
                        "strikePrice": 24100 + i * 100,
                        "CE": {"openInterest": 50000, "lastPrice": 100, "totalTradedVolume": 1000, "impliedVolatility": 17},
                        "PE": {"openInterest": 40000, "lastPrice": 60, "totalTradedVolume": 800, "impliedVolatility": 20},
                    }
                    for i in range(59)
                ],
            },
        }
        result = fetcher.parse_nse_response(raw)

        strike = Decimal("24000")
        s = result["strikes"][strike]
        assert s["pe_oi"] == 0
        assert s["pe_ltp"] == Decimal("0")
        assert s["ce_oi"] == 100000

    def test_sums_oi_from_strikes_not_totals(self):
        """OI totals must be summed from per-strike data, not from totCE/totPE."""
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response(num_strikes=3, ce_oi=100, pe_oi=200)
        result = fetcher.parse_nse_response(raw)

        total_ce = sum(s["ce_oi"] for s in result["strikes"].values())
        total_pe = sum(s["pe_oi"] for s in result["strikes"].values())
        assert result["total_ce_oi"] == total_ce
        assert result["total_pe_oi"] == total_pe
        assert total_ce > 0
        assert total_pe > 0

    def test_returns_empty_for_no_data(self):
        fetcher = NSEFetcher()
        raw = {"records": {"data": [], "underlyingValue": 0}}
        result = fetcher.parse_nse_response(raw)
        assert len(result["strikes"]) == 0
        assert result["spot_price"] == Decimal("0")


class TestValidate:

    def test_passes_valid_data(self):
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response()
        parsed = fetcher.parse_nse_response(raw)
        fetcher.validate(parsed)  # Should not raise

    def test_fails_zero_spot(self):
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response(spot=0)
        parsed = fetcher.parse_nse_response(raw)
        with pytest.raises(NSEValidationError, match="spot"):
            fetcher.validate(parsed)

    def test_fails_few_strikes(self):
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response(num_strikes=10)
        parsed = fetcher.parse_nse_response(raw)
        with pytest.raises(NSEValidationError, match="strike"):
            fetcher.validate(parsed)

    def test_fails_all_zero_oi(self):
        fetcher = NSEFetcher()
        raw = _make_nse_v3_response(ce_oi=0, pe_oi=0)
        parsed = fetcher.parse_nse_response(raw)
        with pytest.raises(NSEValidationError, match="OI"):
            fetcher.validate(parsed)


class TestFetchOptionChain:

    @pytest.mark.asyncio
    async def test_fetch_performs_cookie_warmup(self):
        """Must call NSE homepage first (cookie warmup), then API."""
        fetcher = NSEFetcher()
        valid_response = _make_nse_v3_response()

        mock_response_cookie = MagicMock()
        mock_response_cookie.status_code = 200

        mock_response_api = MagicMock()
        mock_response_api.status_code = 200
        mock_response_api.json.return_value = valid_response

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[mock_response_cookie, mock_response_api])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetcher.fetch_option_chain("NIFTY", date(2026, 4, 16))

        assert mock_client.get.call_count == 2
        # First call should be cookie warmup
        first_call_url = str(mock_client.get.call_args_list[0][0][0])
        assert "option-chain" in first_call_url.lower() or "nseindia" in first_call_url.lower()

    @pytest.mark.asyncio
    async def test_fetch_raises_on_http_error(self):
        fetcher = NSEFetcher()

        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NSEFetchError):
                await fetcher.fetch_option_chain("NIFTY", date(2026, 4, 16))

    @pytest.mark.asyncio
    async def test_fetch_raises_on_timeout(self):
        fetcher = NSEFetcher()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(NSEFetchError):
                await fetcher.fetch_option_chain("NIFTY", date(2026, 4, 16))
