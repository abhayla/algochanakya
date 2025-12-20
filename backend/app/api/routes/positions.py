"""
Positions API Routes

F&O Positions with live P&L, exit, and add functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
import re

from app.database import get_db
from app.models import User, BrokerConnection
from app.models.autopilot import AutoPilotOrder, AutoPilotStrategy
from app.services.kite_orders import KiteOrderService
from app.utils.dependencies import get_current_user, get_current_broker_connection
from sqlalchemy import select, and_

router = APIRouter()

# Lot sizes
LOT_SIZES = {"NIFTY": 25, "BANKNIFTY": 15, "FINNIFTY": 25, "SENSEX": 10}


class ExitOrderRequest(BaseModel):
    tradingsymbol: str
    exchange: str
    transaction_type: str  # BUY or SELL (opposite of position)
    quantity: int
    product: str = "NRML"
    order_type: str = "MARKET"
    price: Optional[float] = None


class AddPositionRequest(BaseModel):
    tradingsymbol: str
    exchange: str
    transaction_type: str
    quantity: int
    product: str = "NRML"
    order_type: str = "LIMIT"
    price: float


def parse_tradingsymbol(symbol: str) -> dict:
    """Parse trading symbol to extract underlying, expiry, strike, option type"""
    result = {
        "underlying": "",
        "expiry": "",
        "strike": 0,
        "option_type": "",
        "instrument_type": "FUT"
    }

    try:
        # Check for options (ends with CE or PE)
        if symbol.endswith("CE") or symbol.endswith("PE"):
            result["option_type"] = symbol[-2:]
            result["instrument_type"] = "OPT"

            # Find underlying (NIFTY, BANKNIFTY, etc.)
            for ul in ["BANKNIFTY", "NIFTY", "FINNIFTY", "SENSEX"]:
                if symbol.startswith(ul):
                    result["underlying"] = ul
                    remaining = symbol[len(ul):-2]  # Remove underlying and CE/PE

                    # Parse expiry and strike
                    # Format: 25D09 or 25DEC or 2512 for expiry, then strike
                    # Find the strike (last numbers before CE/PE)
                    match = re.search(r'(\d+)$', remaining)
                    if match:
                        result["strike"] = float(match.group(1))
                        result["expiry"] = remaining[:match.start()]

                    break
        else:
            # Futures
            for ul in ["BANKNIFTY", "NIFTY", "FINNIFTY", "SENSEX"]:
                if symbol.startswith(ul):
                    result["underlying"] = ul
                    result["expiry"] = symbol[len(ul):]
                    result["instrument_type"] = "FUT"
                    break
    except:
        pass

    return result


@router.get("/")
async def get_positions(
    position_type: str = Query("day", description="day or net"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """Get all F&O positions with live P&L"""

    try:
        kite_service = KiteOrderService(broker.access_token)

        # Get positions from Kite
        positions_data = await kite_service.get_positions()

        if position_type == "day":
            raw_positions = positions_data.get("day", [])
        else:
            raw_positions = positions_data.get("net", [])

        # Filter F&O positions only
        fno_positions = [
            p for p in raw_positions
            if p.get("exchange") in ["NFO", "BFO"] and p.get("quantity", 0) != 0
        ]

        if not fno_positions:
            return {
                "positions": [],
                "summary": {
                    "total_pnl": 0,
                    "total_pnl_pct": 0,
                    "realized_pnl": 0,
                    "unrealized_pnl": 0,
                    "total_positions": 0,
                    "total_quantity": 0,
                    "margin_used": 0,
                    "margin_available": 0
                }
            }

        # Get live quotes for all positions
        symbols = [f"{p['exchange']}:{p['tradingsymbol']}" for p in fno_positions]
        quotes = await kite_service.get_quote(symbols) if symbols else {}

        # Process positions
        processed_positions = []
        total_pnl = 0
        total_realized = 0
        total_unrealized = 0
        total_quantity = 0

        for pos in fno_positions:
            symbol_key = f"{pos['exchange']}:{pos['tradingsymbol']}"
            quote = quotes.get(symbol_key, {})

            ltp = quote.get("last_price", pos.get("last_price", 0))

            # Calculate P&L
            quantity = pos.get("quantity", 0)
            avg_price = pos.get("average_price", 0)

            # MTM P&L
            if quantity > 0:  # Long position
                pnl = (ltp - avg_price) * quantity
            else:  # Short position
                pnl = (avg_price - ltp) * abs(quantity)

            # Change percentage
            if avg_price > 0:
                change_pct = ((ltp - avg_price) / avg_price) * 100
                if quantity < 0:
                    change_pct = -change_pct
            else:
                change_pct = 0

            # Day's change
            day_change = quote.get("net_change", 0)
            day_change_pct = quote.get("change", 0)

            # Parse instrument details
            tradingsymbol = pos.get("tradingsymbol", "")
            instrument_details = parse_tradingsymbol(tradingsymbol)

            processed_pos = {
                "tradingsymbol": tradingsymbol,
                "exchange": pos.get("exchange", "NFO"),
                "product": pos.get("product", "NRML"),
                "quantity": quantity,
                "overnight_quantity": pos.get("overnight_quantity", 0),
                "average_price": round(avg_price, 2),
                "ltp": round(ltp, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(change_pct, 2),
                "day_change": round(day_change, 2) if day_change else 0,
                "day_change_pct": round(day_change_pct, 2) if day_change_pct else 0,
                "value": round(abs(quantity) * ltp, 2),
                "buy_value": pos.get("buy_value", 0),
                "sell_value": pos.get("sell_value", 0),
                "buy_quantity": pos.get("buy_quantity", 0),
                "sell_quantity": pos.get("sell_quantity", 0),
                "realized_pnl": pos.get("realised", 0),
                "unrealized_pnl": round(pnl, 2),
                "multiplier": pos.get("multiplier", 1),
                "instrument_token": pos.get("instrument_token"),
                **instrument_details
            }

            processed_positions.append(processed_pos)

            total_pnl += pnl
            total_realized += pos.get("realised", 0)
            total_unrealized += pnl
            total_quantity += abs(quantity)

        # Sort by underlying, then by expiry
        processed_positions.sort(key=lambda x: (x.get("underlying", ""), x.get("expiry", ""), x.get("strike", 0)))

        # Get margin info
        try:
            margins = await kite_service.get_margins()
            equity_margin = margins.get("equity", {})
            available_margin = equity_margin.get("available", {}).get("live_balance", 0)
            used_margin = equity_margin.get("utilised", {}).get("span", 0) + equity_margin.get("utilised", {}).get("exposure", 0)
        except:
            available_margin = 0
            used_margin = 0

        return {
            "positions": processed_positions,
            "summary": {
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round((total_pnl / used_margin * 100) if used_margin > 0 else 0, 2),
                "realized_pnl": round(total_realized, 2),
                "unrealized_pnl": round(total_unrealized, 2),
                "total_positions": len(processed_positions),
                "total_quantity": total_quantity,
                "margin_used": round(used_margin, 2),
                "margin_available": round(available_margin, 2)
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )


@router.post("/exit")
async def exit_position(
    request: ExitOrderRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """Exit a position (place opposite order)"""

    try:
        kite_service = KiteOrderService(broker.access_token)

        order_legs = [{
            "tradingsymbol": request.tradingsymbol,
            "exchange": request.exchange,
            "transaction_type": request.transaction_type,
            "quantity": request.quantity,
            "order_type": request.order_type,
            "price": request.price if request.order_type == "LIMIT" else None
        }]

        results = await kite_service.place_basket_order(order_legs)
        result = results[0] if results else {}

        if result.get("success"):
            return {
                "success": True,
                "order_id": result.get("order_id"),
                "message": "Exit order placed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to place exit order")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/add")
async def add_to_position(
    request: AddPositionRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """Add to existing position"""

    try:
        kite_service = KiteOrderService(broker.access_token)

        order_legs = [{
            "tradingsymbol": request.tradingsymbol,
            "exchange": request.exchange,
            "transaction_type": request.transaction_type,
            "quantity": request.quantity,
            "order_type": request.order_type,
            "price": request.price
        }]

        results = await kite_service.place_basket_order(order_legs)
        result = results[0] if results else {}

        if result.get("success"):
            return {
                "success": True,
                "order_id": result.get("order_id"),
                "message": "Order placed successfully"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to place order")
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/exit-all")
async def exit_all_positions(
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """Exit all open positions"""

    try:
        kite_service = KiteOrderService(broker.access_token)

        # Get all positions
        positions_data = await kite_service.get_positions()
        net_positions = positions_data.get("net", [])

        # Filter F&O positions with quantity
        fno_positions = [
            p for p in net_positions
            if p.get("exchange") in ["NFO", "BFO"] and p.get("quantity", 0) != 0
        ]

        if not fno_positions:
            return {"success": True, "message": "No open positions to exit", "orders_placed": [], "errors": []}

        # Build exit orders
        exit_orders = []
        for pos in fno_positions:
            quantity = pos.get("quantity", 0)

            # Determine transaction type (opposite of position)
            if quantity > 0:
                txn_type = "SELL"
            else:
                txn_type = "BUY"
                quantity = abs(quantity)

            exit_orders.append({
                "tradingsymbol": pos.get("tradingsymbol"),
                "exchange": pos.get("exchange"),
                "transaction_type": txn_type,
                "quantity": quantity,
                "order_type": "MARKET"
            })

        # Place all exit orders
        results = await kite_service.place_basket_order(exit_orders)

        orders_placed = []
        errors = []

        for i, result in enumerate(results):
            if result.get("success"):
                orders_placed.append({
                    "tradingsymbol": exit_orders[i]["tradingsymbol"],
                    "order_id": result.get("order_id")
                })
            else:
                errors.append({
                    "tradingsymbol": exit_orders[i]["tradingsymbol"],
                    "error": result.get("error")
                })

        return {
            "success": len(errors) == 0,
            "orders_placed": orders_placed,
            "errors": errors,
            "message": f"Placed {len(orders_placed)} exit orders, {len(errors)} failed"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/grouped")
async def get_grouped_positions(
    group_by: str = Query("underlying", description="underlying, expiry, or strategy"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """Get positions grouped by underlying, expiry, or strategy"""

    # Get base positions
    positions_data = await get_positions("net", user, broker, db)
    positions = positions_data["positions"]

    if not positions:
        return {"groups": [], "summary": positions_data["summary"]}

    # Group positions
    groups = {}

    for pos in positions:
        if group_by == "underlying":
            key = pos.get("underlying", "Other")
        elif group_by == "expiry":
            key = pos.get("expiry", "Other")
        else:
            key = "Custom"

        if key not in groups:
            groups[key] = {
                "name": key,
                "positions": [],
                "total_pnl": 0,
                "total_quantity": 0
            }

        groups[key]["positions"].append(pos)
        groups[key]["total_pnl"] += pos.get("pnl", 0)
        groups[key]["total_quantity"] += abs(pos.get("quantity", 0))

    # Convert to list
    grouped_list = list(groups.values())

    # Sort by P&L
    grouped_list.sort(key=lambda x: x["total_pnl"], reverse=True)

    return {
        "groups": grouped_list,
        "summary": positions_data["summary"]
    }


@router.get("/annotated")
async def get_annotated_positions(
    position_type: str = Query("day", description="day or net"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get positions annotated with AutoPilot metadata.

    Returns positions with additional fields:
    - is_autopilot: Boolean indicating if position is from AutoPilot
    - autopilot_strategy_id: ID of the strategy that created this position
    - autopilot_strategy_name: Name of the strategy
    - autopilot_trading_mode: 'live' or 'paper'
    """

    # Get base positions data
    positions_data = await get_positions(position_type, user, broker, db)
    positions = positions_data["positions"]

    if not positions:
        return positions_data

    # Get all tradingsymbols
    tradingsymbols = [pos["tradingsymbol"] for pos in positions]

    # Query AutoPilot orders that match these tradingsymbols
    # Join with strategies to get strategy info
    query = (
        select(
            AutoPilotOrder.tradingsymbol,
            AutoPilotOrder.trading_mode,
            AutoPilotStrategy.id.label("strategy_id"),
            AutoPilotStrategy.name.label("strategy_name")
        )
        .join(AutoPilotStrategy, AutoPilotOrder.strategy_id == AutoPilotStrategy.id)
        .where(
            and_(
                AutoPilotOrder.user_id == user.id,
                AutoPilotOrder.tradingsymbol.in_(tradingsymbols),
                AutoPilotOrder.status.in_(["complete"])  # Only completed orders
            )
        )
        .distinct(AutoPilotOrder.tradingsymbol)
    )

    result = await db.execute(query)
    autopilot_data = result.all()

    # Create lookup dict
    autopilot_lookup = {
        row.tradingsymbol: {
            "strategy_id": row.strategy_id,
            "strategy_name": row.strategy_name,
            "trading_mode": row.trading_mode
        }
        for row in autopilot_data
    }

    # Annotate positions
    annotated_positions = []
    for pos in positions:
        tradingsymbol = pos["tradingsymbol"]

        if tradingsymbol in autopilot_lookup:
            ap_data = autopilot_lookup[tradingsymbol]
            pos["is_autopilot"] = True
            pos["autopilot_strategy_id"] = ap_data["strategy_id"]
            pos["autopilot_strategy_name"] = ap_data["strategy_name"]
            pos["autopilot_trading_mode"] = ap_data["trading_mode"]
        else:
            pos["is_autopilot"] = False
            pos["autopilot_strategy_id"] = None
            pos["autopilot_strategy_name"] = None
            pos["autopilot_trading_mode"] = None

        annotated_positions.append(pos)

    return {
        "positions": annotated_positions,
        "summary": positions_data["summary"]
    }
