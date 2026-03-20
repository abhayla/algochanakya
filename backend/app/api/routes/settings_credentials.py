"""
Settings Credentials OAuth Callbacks (Gap N)

Separate OAuth callback endpoints for the Settings page.
These store tokens in broker_api_credentials (for market data),
NOT in broker_connections (for order execution).
They do NOT create JWT sessions or overwrite login state.

Supports: Zerodha, Upstox, Fyers, Paytm (OAuth brokers).
AngelOne uses direct auth via /api/smartapi/authenticate.
Dhan uses static token via /api/dhan-credentials/credentials.
"""
import hashlib
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User
from app.models.broker_api_credentials import BrokerAPICredentials
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _settings_redirect_url(broker: str) -> str:
    """Build the Settings OAuth redirect URL for a broker.

    Uses the same base as the login redirect but with /api/settings/{broker}/connect-callback path.
    """
    base = settings.FRONTEND_URL.rstrip("/")
    backend_base = f"http://localhost:{getattr(settings, 'PORT', 8001)}"
    return f"{backend_base}/api/settings/{broker}/connect-callback"


async def _upsert_broker_credential(
    db: AsyncSession, user_id, broker: str, access_token: str, **extra_fields
) -> BrokerAPICredentials:
    """Upsert broker_api_credentials row with the new access token."""
    result = await db.execute(
        select(BrokerAPICredentials).where(
            BrokerAPICredentials.user_id == user_id,
            BrokerAPICredentials.broker == broker,
        )
    )
    cred = result.scalar_one_or_none()

    if cred:
        cred.access_token = access_token
        cred.is_active = True
        cred.last_auth_at = datetime.now(timezone.utc)
        cred.last_error = None
        for k, v in extra_fields.items():
            if hasattr(cred, k):
                setattr(cred, k, v)
    else:
        cred = BrokerAPICredentials(
            user_id=user_id,
            broker=broker,
            access_token=access_token,
            is_active=True,
            last_auth_at=datetime.now(timezone.utc),
            **extra_fields,
        )
        db.add(cred)

    await db.commit()
    return cred


# ============================================================================
# Zerodha (Kite Connect)
# ============================================================================

@router.get("/zerodha/connect")
async def zerodha_settings_connect(
    user: User = Depends(get_current_user),
):
    """Return Kite OAuth URL for Settings credential connection."""
    if not settings.KITE_API_KEY:
        raise HTTPException(status_code=503, detail="Kite API key not configured")

    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    login_url = kite.login_url()
    # Replace the login redirect with settings redirect
    redirect_url = _settings_redirect_url("zerodha")
    login_url = login_url.replace(
        settings.KITE_REDIRECT_URL, redirect_url
    ) if settings.KITE_REDIRECT_URL else login_url

    return {"login_url": login_url}


@router.get("/zerodha/connect-callback")
async def zerodha_settings_callback(
    request_token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Handle Kite OAuth callback for Settings — stores in broker_api_credentials only."""
    try:
        kite = KiteConnect(api_key=settings.KITE_API_KEY)
        data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
        access_token = data["access_token"]

        await _upsert_broker_credential(db, user.id, "zerodha", access_token)

        logger.info(f"[Settings/Zerodha] Credentials stored for user {user.id}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?broker=zerodha&status=connected",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Settings/Zerodha] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=zerodha&message={e}",
            status_code=302,
        )


# ============================================================================
# Upstox
# ============================================================================

@router.get("/upstox/connect")
async def upstox_settings_connect(
    user: User = Depends(get_current_user),
):
    """Return Upstox OAuth URL for Settings credential connection."""
    if not settings.UPSTOX_API_KEY:
        raise HTTPException(status_code=503, detail="Upstox API key not configured")

    redirect_url = _settings_redirect_url("upstox")
    login_url = (
        "https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={settings.UPSTOX_API_KEY}"
        f"&redirect_uri={redirect_url}"
    )
    return {"login_url": login_url}


@router.get("/upstox/connect-callback")
async def upstox_settings_callback(
    code: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Handle Upstox OAuth callback for Settings — stores in broker_api_credentials only."""
    try:
        redirect_url = _settings_redirect_url("upstox")

        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://api.upstox.com/v2/login/authorization/token",
                data={
                    "code": code,
                    "client_id": settings.UPSTOX_API_KEY,
                    "client_secret": settings.UPSTOX_API_SECRET,
                    "redirect_uri": redirect_url,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if token_resp.status_code != 200:
            logger.error(f"[Settings/Upstox] Token exchange failed: {token_resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=upstox",
                status_code=302,
            )

        access_token = token_resp.json()["access_token"]
        await _upsert_broker_credential(db, user.id, "upstox", access_token)

        logger.info(f"[Settings/Upstox] Credentials stored for user {user.id}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?broker=upstox&status=connected",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Settings/Upstox] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=upstox&message={e}",
            status_code=302,
        )


# ============================================================================
# Fyers
# ============================================================================

@router.get("/fyers/connect")
async def fyers_settings_connect(
    user: User = Depends(get_current_user),
):
    """Return Fyers OAuth URL for Settings credential connection."""
    if not settings.FYERS_APP_ID:
        raise HTTPException(status_code=503, detail="Fyers App ID not configured")

    redirect_url = _settings_redirect_url("fyers")
    login_url = (
        "https://api-t1.fyers.in/api/v3/generate-authcode"
        f"?client_id={settings.FYERS_APP_ID}"
        f"&redirect_uri={redirect_url}"
        f"&response_type=code"
        f"&state=settings"
    )
    return {"login_url": login_url}


@router.get("/fyers/connect-callback")
async def fyers_settings_callback(
    auth_code: str,
    s: str = "ok",
    state: str = "",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Handle Fyers OAuth callback for Settings — stores in broker_api_credentials only."""
    if s != "ok":
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=auth_denied&broker=fyers",
            status_code=302,
        )

    try:
        app_id_hash = hashlib.sha256(
            f"{settings.FYERS_APP_ID}:{settings.FYERS_SECRET_KEY}".encode()
        ).hexdigest()

        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://api-t1.fyers.in/api/v3/validate-authcode",
                json={
                    "grant_type": "authorization_code",
                    "appIdHash": app_id_hash,
                    "code": auth_code,
                },
            )

        token_data = token_resp.json()
        if token_data.get("code") != 200 and token_data.get("s") != "ok":
            logger.error(f"[Settings/Fyers] Token exchange failed: {token_data}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=fyers",
                status_code=302,
            )

        access_token = token_data.get("access_token", "")
        await _upsert_broker_credential(
            db, user.id, "fyers", access_token,
            client_id=settings.FYERS_APP_ID,
        )

        logger.info(f"[Settings/Fyers] Credentials stored for user {user.id}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?broker=fyers&status=connected",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Settings/Fyers] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=fyers&message={e}",
            status_code=302,
        )


# ============================================================================
# Paytm
# ============================================================================

@router.get("/paytm/connect")
async def paytm_settings_connect(
    user: User = Depends(get_current_user),
):
    """Return Paytm OAuth URL for Settings credential connection."""
    if not settings.PAYTM_API_KEY:
        raise HTTPException(status_code=503, detail="Paytm API key not configured")

    redirect_url = _settings_redirect_url("paytm")
    login_url = (
        "https://login.paytmmoney.com/merchant-login"
        f"?apiKey={settings.PAYTM_API_KEY}"
        f"&state=settings"
    )
    return {"login_url": login_url}


@router.get("/paytm/connect-callback")
async def paytm_settings_callback(
    requestToken: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Handle Paytm OAuth callback for Settings — stores in broker_api_credentials only."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_resp = await client.post(
                "https://developer.paytmmoney.com/accounts/v2/gettoken",
                json={
                    "api_key": settings.PAYTM_API_KEY,
                    "api_secret_key": settings.PAYTM_API_SECRET,
                    "request_token": requestToken,
                },
            )

        if token_resp.status_code != 200:
            logger.error(f"[Settings/Paytm] Token exchange failed: {token_resp.text[:300]}")
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=paytm",
                status_code=302,
            )

        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")
        public_access_token = token_data.get("public_access_token", "")

        await _upsert_broker_credential(
            db, user.id, "paytm", access_token,
            feed_token=public_access_token,
            broker_metadata={"public_access_token": public_access_token},
        )

        logger.info(f"[Settings/Paytm] Credentials stored for user {user.id}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?broker=paytm&status=connected",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"[Settings/Paytm] Callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/settings?error=auth_failed&broker=paytm&message={e}",
            status_code=302,
        )
