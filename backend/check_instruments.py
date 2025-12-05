"""Check instruments table data"""
import asyncio
from sqlalchemy import select, func, distinct
from app.database import AsyncSessionLocal
from app.models import Instrument

async def check_instruments():
    async with AsyncSessionLocal() as db:
        # Count total
        result = await db.execute(select(func.count(Instrument.id)))
        total = result.scalar()
        print(f"Total instruments: {total}")

        if total == 0:
            print("\n*** INSTRUMENTS TABLE IS EMPTY! ***")
            print("Need to download instruments from Kite.")
            return

        # Check distinct exchanges
        result = await db.execute(select(distinct(Instrument.exchange)))
        exchanges = [r[0] for r in result.fetchall()]
        print(f"\nExchanges: {exchanges}")

        # Check distinct names (underlying)
        result = await db.execute(select(distinct(Instrument.name)))
        names = [r[0] for r in result.fetchall()]
        print(f"\nNames (first 20): {names[:20]}")

        # Check NFO options
        result = await db.execute(
            select(func.count(Instrument.id)).where(
                Instrument.exchange == "NFO",
                Instrument.instrument_type.in_(["CE", "PE"])
            )
        )
        nfo_options = result.scalar()
        print(f"\nNFO Options count: {nfo_options}")

        # Check NIFTY options specifically
        result = await db.execute(
            select(func.count(Instrument.id)).where(
                Instrument.name == "NIFTY",
                Instrument.exchange == "NFO",
                Instrument.instrument_type.in_(["CE", "PE"])
            )
        )
        nifty_options = result.scalar()
        print(f"NIFTY Options count: {nifty_options}")

        # Sample NIFTY instruments
        result = await db.execute(
            select(Instrument).where(
                Instrument.name == "NIFTY",
                Instrument.exchange == "NFO"
            ).limit(5)
        )
        samples = result.scalars().all()
        print(f"\nSample NIFTY instruments:")
        for inst in samples:
            print(f"  {inst.tradingsymbol} | {inst.instrument_type} | Strike: {inst.strike} | Expiry: {inst.expiry}")

if __name__ == "__main__":
    asyncio.run(check_instruments())
