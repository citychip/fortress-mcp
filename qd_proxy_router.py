"""
qd_proxy_router.py — FastAPI router for QuantData proxy endpoints.

Drop this file into your fortress-api app directory and register it:

    # In main.py or app/__init__.py:
    from qd_proxy_router import router as qd_router
    app.include_router(qd_router)

Requires these env vars on the server (already in your systemd override):
    QUANTDATA_AUTH_TOKEN=<jwt>
    QUANTDATA_INSTANCE_ID=<id>

All routes require the standard Fortress bearer token (same auth as every
other /api/* endpoint). The client never sees the QuantData credentials.
"""

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ── Auth (reuse whatever your app already uses) ───────────────────────────────
# If your app has a shared `verify_token` dependency, import and use that
# instead of the inline check below.
_FORTRESS_TOKEN = os.environ.get("FORTRESS_API_TOKEN", "")
_QD_AUTH_TOKEN  = os.environ.get("QUANTDATA_AUTH_TOKEN", "")
_QD_INSTANCE_ID = os.environ.get("QUANTDATA_INSTANCE_ID", "")
_QD_BASE_URL    = "https://core-lb-prod.quantdata.us/api"

security = HTTPBearer()

def _verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != _FORTRESS_TOKEN:
        raise HTTPException(status_code=401, detail="invalid_token")

def _qd_headers() -> dict:
    if not _QD_AUTH_TOKEN or not _QD_INSTANCE_ID:
        raise HTTPException(
            status_code=503,
            detail="QuantData credentials not configured on server. "
                   "Set QUANTDATA_AUTH_TOKEN and QUANTDATA_INSTANCE_ID in the systemd env override.",
        )
    return {
        "accept":       "application/json",
        "authorization": _QD_AUTH_TOKEN,
        "x-instance-id": _QD_INSTANCE_ID,
        "x-qd-version": "1",
        "origin":       "https://v3.quantdata.us",
    }

async def _qd_get(endpoint: str, params: dict) -> Any:
    url = f"{_QD_BASE_URL}/{endpoint.lstrip('/')}"
    headers = _qd_headers()
    async with httpx.AsyncClient(timeout=15) as client:
        for attempt in range(3):
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 401:
                raise HTTPException(status_code=502, detail="QuantData authentication failed.")
            if resp.status_code == 429:
                if attempt < 2:
                    import asyncio
                    await asyncio.sleep(1.0 * (2 ** attempt))
                    continue
                raise HTTPException(status_code=429, detail="QuantData rate limit exceeded.")
            resp.raise_for_status()
            return resp.json()
    raise HTTPException(status_code=502, detail="QuantData request failed after 3 attempts.")


router = APIRouter(prefix="/api/qd", tags=["quantdata"], dependencies=[Depends(_verify_token)])


@router.get("/dark_pool_levels")
async def dark_pool_levels(
    ticker: str = Query(..., description="Uppercase ticker, e.g. MSFT"),
    session_date: str | None = Query(None, description="YYYY-MM-DD, defaults to today"),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    return await _qd_get(
        "tool/OPTIONS_DARK_POOL_LEVELS_TABLE",
        {"ticker": ticker, "sessionDate": session_date},
    )


@router.get("/order_flow")
async def order_flow(
    ticker: str = Query(...),
    session_date: str | None = Query(None),
    min_premium: float | None = Query(None),
    is_sweep: bool | None = Query(None),
    is_block: bool | None = Query(None),
    side: str | None = Query(None),
    limit: int = Query(50),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    params: dict = {"ticker": ticker, "sessionDate": session_date, "limit": limit}
    if min_premium is not None:
        params["minPremium"] = min_premium
    if is_sweep is not None:
        params["isSweep"] = str(is_sweep).lower()
    if is_block is not None:
        params["isBlock"] = str(is_block).lower()
    if side:
        params["side"] = side.upper()
    return await _qd_get("tool/OPTIONS_ORDER_FLOW_CONSOLIDATED_TABLE", params)


@router.get("/net_drift")
async def net_drift(
    ticker: str = Query(...),
    session_date: str | None = Query(None),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    return await _qd_get(
        "tool/OPTIONS_NET_DRIFT_CHART",
        {"ticker": ticker, "sessionDate": session_date},
    )


@router.get("/max_pain")
async def max_pain(
    ticker: str = Query(...),
    session_date: str | None = Query(None),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    return await _qd_get(
        "tool/OPTIONS_MAX_PAIN_CHART",
        {"ticker": ticker, "sessionDate": session_date},
    )


@router.get("/iv_rank")
async def iv_rank(
    ticker: str = Query(...),
    session_date: str | None = Query(None),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    return await _qd_get(
        "tool/OPTIONS_IV_RANK_CHART",
        {"ticker": ticker, "sessionDate": session_date},
    )


@router.get("/oi_change")
async def oi_change(
    ticker: str = Query(...),
    session_date: str | None = Query(None),
):
    from datetime import date
    if not session_date:
        session_date = date.today().isoformat()
    return await _qd_get(
        "tool/OPTIONS_OPEN_INTEREST_CHANGE_TABLE",
        {"ticker": ticker, "sessionDate": session_date},
    )
