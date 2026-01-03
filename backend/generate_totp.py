"""
Generate TOTP for SmartAPI Authentication

Utility script to generate the current 6-digit TOTP code from stored SmartAPI credentials.
The TOTP secret is stored encrypted in the `smartapi_credentials` table and is decrypted
using Fernet encryption (key derived from JWT_SECRET).

Usage:
    cd backend
    venv\\Scripts\\activate  # Windows
    python generate_totp.py

Output:
    TOTP: 123456
    Client ID: ABC123

Note: TOTP codes are time-based and valid for 30 seconds.
"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.smartapi_credentials import SmartAPICredentials
from app.utils.encryption import decrypt
from sqlalchemy import select
import pyotp

async def get_and_generate_totp():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SmartAPICredentials))
        creds = result.scalar_one_or_none()
        if creds:
            totp_secret = decrypt(creds.encrypted_totp_secret)
            totp = pyotp.TOTP(totp_secret)
            current_totp = totp.now()
            print(f"TOTP: {current_totp}")
            print(f"Client ID: {creds.client_id}")
        else:
            print("No SmartAPI credentials found")

if __name__ == "__main__":
    asyncio.run(get_and_generate_totp())
