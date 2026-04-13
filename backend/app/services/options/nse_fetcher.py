"""
NSE India v3 API Fetcher for EOD option chain snapshots.

Fetches option chain data from NSE's public API with cookie warmup.
Used as an authoritative data source for OI/Volume when brokers
return zeros outside market hours.
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Dict

import httpx

logger = logging.getLogger(__name__)


class NSEFetchError(Exception):
    """NSE API request failed (network, timeout, blocked)."""


class NSEValidationError(Exception):
    """NSE response data failed validation checks."""


_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}

_MIN_STRIKES = 30


class NSEFetcher:
    """Fetches option chain data from NSE India's public API."""

    NSE_BASE = "https://www.nseindia.com"
    NSE_V3_URL = f"{NSE_BASE}/api/option-chain-v3"

    def _format_expiry(self, d: date) -> str:
        """Convert date to NSE format: 'DD-Mon-YYYY'."""
        dd = str(d.day).zfill(2)
        return f"{dd}-{_MONTHS[d.month - 1]}-{d.year}"

    def parse_nse_response(self, raw: dict) -> dict:
        """
        Parse raw NSE response into a structured dict.

        OI totals are summed from per-strike data (not from totCE/totPE
        which can be 0 on weekends/holidays).

        Returns:
            {
                "spot_price": Decimal,
                "total_ce_oi": int,
                "total_pe_oi": int,
                "strikes": {
                    Decimal("24000.00"): {
                        "ce_ltp": Decimal, "ce_oi": int, "ce_volume": int,
                        "ce_iv": Decimal,
                        "pe_ltp": Decimal, "pe_oi": int, "pe_volume": int,
                        "pe_iv": Decimal,
                    },
                    ...
                }
            }
        """
        records = raw.get("filtered") or raw.get("records") or {}
        spot_raw = (
            records.get("underlyingValue")
            or (raw.get("records") or {}).get("underlyingValue")
            or 0
        )
        spot_price = Decimal(str(spot_raw))

        strikes: Dict[Decimal, dict] = {}
        total_ce_oi = 0
        total_pe_oi = 0

        for row in (records.get("data") or []):
            strike = Decimal(str(row.get("strikePrice", 0)))
            ce = row.get("CE") or {}
            pe = row.get("PE") or {}

            ce_oi = int(ce.get("openInterest", 0) or 0)
            pe_oi = int(pe.get("openInterest", 0) or 0)

            strikes[strike] = {
                "ce_ltp": Decimal(str(ce.get("lastPrice", 0) or 0)),
                "ce_oi": ce_oi,
                "ce_volume": int(ce.get("totalTradedVolume", 0) or 0),
                "ce_iv": Decimal(str(ce.get("impliedVolatility", 0) or 0)),
                "pe_ltp": Decimal(str(pe.get("lastPrice", 0) or 0)),
                "pe_oi": pe_oi,
                "pe_volume": int(pe.get("totalTradedVolume", 0) or 0),
                "pe_iv": Decimal(str(pe.get("impliedVolatility", 0) or 0)),
            }
            total_ce_oi += ce_oi
            total_pe_oi += pe_oi

        return {
            "spot_price": spot_price,
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "strikes": strikes,
        }

    def validate(self, parsed: dict) -> None:
        """
        Validate parsed NSE data.

        Raises NSEValidationError if:
        - spot_price is 0
        - fewer than 30 strikes
        - all OI values are 0
        """
        if parsed["spot_price"] <= 0:
            raise NSEValidationError(
                f"NSE spot price is {parsed['spot_price']} — data may be unavailable"
            )
        if len(parsed["strikes"]) < _MIN_STRIKES:
            raise NSEValidationError(
                f"NSE returned only {len(parsed['strikes'])} strikes "
                f"(minimum {_MIN_STRIKES})"
            )
        has_oi = any(
            s["ce_oi"] > 0 or s["pe_oi"] > 0
            for s in parsed["strikes"].values()
        )
        if not has_oi:
            raise NSEValidationError(
                "All OI values are zero — NSE data may be stale"
            )

    async def fetch_option_chain(
        self, symbol: str, expiry_date: date
    ) -> dict:
        """
        Fetch option chain from NSE v3 API with cookie warmup.

        Steps:
        1. GET NSE option-chain page to obtain session cookies
        2. GET v3 API with symbol + expiry

        Returns parsed + validated dict.
        Raises NSEFetchError on network/HTTP errors.
        """
        expiry_str = self._format_expiry(expiry_date)

        try:
            async with httpx.AsyncClient(
                headers=_NSE_HEADERS,
                follow_redirects=True,
                timeout=20.0,
            ) as client:
                # Step 1: Cookie warmup
                cookie_resp = await client.get(f"{self.NSE_BASE}/option-chain")
                if cookie_resp.status_code != 200:
                    raise NSEFetchError(
                        f"Cookie warmup failed: HTTP {cookie_resp.status_code}"
                    )

                # Step 2: Fetch option chain data
                api_resp = await client.get(
                    self.NSE_V3_URL,
                    params={
                        "type": "Indices",
                        "symbol": symbol,
                        "expiry": expiry_str,
                    },
                )
                if api_resp.status_code != 200:
                    raise NSEFetchError(
                        f"NSE API returned HTTP {api_resp.status_code}"
                    )

                raw = api_resp.json()
                parsed = self.parse_nse_response(raw)
                self.validate(parsed)
                return parsed

        except httpx.TimeoutException as e:
            raise NSEFetchError(f"NSE request timed out: {e}") from e
        except NSEFetchError:
            raise
        except NSEValidationError:
            raise
        except Exception as e:
            raise NSEFetchError(f"NSE fetch failed: {e}") from e
