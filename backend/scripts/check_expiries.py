"""Debug option chain adapter get_instruments method."""
import asyncio
import httpx
import re
from datetime import datetime
from decimal import Decimal

# Month mappings (copied from smartapi_instruments.py)
MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
MONTH_TO_NUM = {name: i+1 for i, name in enumerate(MONTH_NAMES)}

def normalize_expiry(expiry: str):
    """Normalize expiry date to YYYY-MM-DD format."""
    if not expiry:
        return None

    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', expiry):
        return expiry

    # SmartAPI format: DDMONYYYY (e.g., "27JAN2026")
    match = re.match(r'^(\d{1,2})([A-Z]{3})(\d{4})$', expiry)
    if match:
        day, month_str, year = match.groups()
        month_num = MONTH_TO_NUM.get(month_str.upper())
        if month_num:
            return f"{year}-{month_num:02d}-{int(day):02d}"

    return None


async def debug_adapter():
    """Debug what the adapter returns for instruments."""
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    print("Downloading SmartAPI instrument master...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        raw_instruments = response.json()

    print(f"Total instruments: {len(raw_instruments)}")

    # Filter for NFO (same as adapter)
    filtered = [inst for inst in raw_instruments if inst.get("exch_seg") == "NFO"]
    print(f"NFO instruments: {len(filtered)}")

    # Mimic adapter's Instrument conversion
    target_expiry = datetime.strptime("2026-01-27", "%Y-%m-%d").date()
    matching_instruments = []

    for raw_inst in filtered:  # Check all NFO instruments
        symbol = raw_inst.get('symbol', '')
        name = raw_inst.get('name', '')
        raw_expiry = raw_inst.get('expiry', '')

        # Parse expiry
        normalized_expiry = normalize_expiry(raw_expiry)
        expiry_date = None
        if normalized_expiry:
            try:
                expiry_date = datetime.strptime(normalized_expiry, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Parse option type
        option_type = None
        if symbol.endswith("CE"):
            option_type = "CE"
        elif symbol.endswith("PE"):
            option_type = "PE"

        # Check if matches NIFTY 27JAN2026
        if name == "NIFTY" and option_type in ["CE", "PE"] and expiry_date == target_expiry:
            matching_instruments.append({
                'symbol': symbol,
                'name': name,
                'expiry': expiry_date,
                'option_type': option_type,
                'strike': raw_inst.get('strike', '')
            })

    print(f"\nMatching NIFTY options for 2026-01-27: {len(matching_instruments)}")
    if matching_instruments:
        for inst in matching_instruments[:5]:
            print(f"  {inst['symbol']} ({inst['option_type']}) strike={inst['strike']}")

    # Also check raw data for 27JAN2026
    print("\n--- Raw instrument check ---")
    nifty_jan27_raw = [
        inst for inst in raw_instruments
        if inst.get('name') == 'NIFTY'
        and inst.get('exch_seg') == 'NFO'
        and inst.get('expiry') == '27JAN2026'
        and (inst.get('symbol', '').endswith('CE') or inst.get('symbol', '').endswith('PE'))
    ]
    print(f"Raw NIFTY 27JAN2026 options: {len(nifty_jan27_raw)}")
    if nifty_jan27_raw:
        for inst in nifty_jan27_raw[:5]:
            print(f"  {inst.get('symbol')} exp={inst.get('expiry')} strike={inst.get('strike')}")

if __name__ == "__main__":
    asyncio.run(debug_adapter())
