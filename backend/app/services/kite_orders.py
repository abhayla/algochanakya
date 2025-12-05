"""
Kite Orders Service

Handles basket orders and position management via Kite Connect API.
"""
import logging
from typing import List, Dict, Optional
from kiteconnect import KiteConnect
from decimal import Decimal

from app.config import settings

logger = logging.getLogger(__name__)


class KiteOrderService:
    """
    Service for placing orders and managing positions via Kite Connect.
    """

    def __init__(self, access_token: str):
        """
        Initialize Kite order service.

        Args:
            access_token: Kite access token from OAuth
        """
        self.kite = KiteConnect(api_key=settings.KITE_API_KEY)
        self.kite.set_access_token(access_token)

    async def place_basket_order(self, legs: List[dict]) -> List[dict]:
        """
        Place multiple orders as a basket.

        Args:
            legs: List of leg dictionaries with:
                - tradingsymbol: Trading symbol
                - transaction_type: BUY or SELL
                - quantity: Order quantity
                - price: Limit price (optional for market orders)
                - order_type: LIMIT or MARKET

        Returns:
            List of order results with success status and order_id or error
        """
        results = []

        for leg in legs:
            try:
                # Determine order type
                order_type = leg.get("order_type", "LIMIT").upper()
                if order_type == "LIMIT":
                    kite_order_type = self.kite.ORDER_TYPE_LIMIT
                else:
                    kite_order_type = self.kite.ORDER_TYPE_MARKET

                # Build order params
                order_params = {
                    "variety": self.kite.VARIETY_REGULAR,
                    "exchange": leg.get("exchange", self.kite.EXCHANGE_NFO),
                    "tradingsymbol": leg["tradingsymbol"],
                    "transaction_type": self.kite.TRANSACTION_TYPE_BUY if leg["transaction_type"].upper() == "BUY" else self.kite.TRANSACTION_TYPE_SELL,
                    "quantity": int(leg["quantity"]),
                    "product": self.kite.PRODUCT_NRML,  # Normal for F&O
                    "order_type": kite_order_type,
                }

                # Add price for limit orders
                if order_type == "LIMIT" and leg.get("price"):
                    order_params["price"] = float(leg["price"])

                # Place order
                order_id = self.kite.place_order(**order_params)

                results.append({
                    "tradingsymbol": leg["tradingsymbol"],
                    "success": True,
                    "order_id": order_id,
                    "error": None
                })

                logger.info(f"Order placed successfully: {order_id} for {leg['tradingsymbol']}")

            except Exception as e:
                logger.error(f"Order failed for {leg.get('tradingsymbol')}: {str(e)}")
                results.append({
                    "tradingsymbol": leg.get("tradingsymbol"),
                    "success": False,
                    "order_id": None,
                    "error": str(e)
                })

        return results

    async def get_positions(self) -> Dict:
        """
        Get current positions from Kite.

        Returns:
            Dictionary with net and day positions
        """
        try:
            positions = self.kite.positions()
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            raise

    async def get_holdings(self) -> List[Dict]:
        """
        Get current holdings from Kite.

        Returns:
            List of holdings
        """
        try:
            holdings = self.kite.holdings()
            return holdings
        except Exception as e:
            logger.error(f"Failed to get holdings: {str(e)}")
            raise

    async def get_orders(self) -> List[Dict]:
        """
        Get today's orders from Kite.

        Returns:
            List of orders
        """
        try:
            orders = self.kite.orders()
            return orders
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            raise

    async def get_order_history(self, order_id: str) -> List[Dict]:
        """
        Get order history for a specific order.

        Args:
            order_id: Kite order ID

        Returns:
            List of order state changes
        """
        try:
            history = self.kite.order_history(order_id)
            return history
        except Exception as e:
            logger.error(f"Failed to get order history: {str(e)}")
            raise

    async def cancel_order(self, order_id: str, variety: str = "regular") -> str:
        """
        Cancel an order.

        Args:
            order_id: Kite order ID
            variety: Order variety (regular, amo, etc.)

        Returns:
            Cancelled order ID
        """
        try:
            result = self.kite.cancel_order(
                variety=variety,
                order_id=order_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            raise

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        variety: str = "regular"
    ) -> str:
        """
        Modify an existing order.

        Args:
            order_id: Kite order ID
            quantity: New quantity
            price: New price
            order_type: New order type
            variety: Order variety

        Returns:
            Modified order ID
        """
        try:
            params = {"variety": variety, "order_id": order_id}

            if quantity is not None:
                params["quantity"] = quantity
            if price is not None:
                params["price"] = price
            if order_type is not None:
                params["order_type"] = order_type

            result = self.kite.modify_order(**params)
            return result
        except Exception as e:
            logger.error(f"Failed to modify order: {str(e)}")
            raise

    async def get_margins(self) -> Dict:
        """
        Get account margins.

        Returns:
            Dictionary with equity and commodity margins
        """
        try:
            margins = self.kite.margins()
            return margins
        except Exception as e:
            logger.error(f"Failed to get margins: {str(e)}")
            raise

    async def get_ltp(self, instruments: List[str]) -> Dict:
        """
        Get LTP for instruments.

        Args:
            instruments: List of instruments in format "EXCHANGE:TRADINGSYMBOL"

        Returns:
            Dictionary with LTP data
        """
        try:
            ltp = self.kite.ltp(instruments)
            return ltp
        except Exception as e:
            logger.error(f"Failed to get LTP: {str(e)}")
            raise

    async def get_quote(self, instruments: List[str]) -> Dict:
        """
        Get full quote for instruments.

        Args:
            instruments: List of instruments in format "EXCHANGE:TRADINGSYMBOL"

        Returns:
            Dictionary with full quote data
        """
        try:
            quote = self.kite.quote(instruments)
            return quote
        except Exception as e:
            logger.error(f"Failed to get quote: {str(e)}")
            raise


def parse_positions_to_legs(positions: Dict, underlying: str = None) -> List[dict]:
    """
    Parse Kite positions into strategy leg format.

    Args:
        positions: Kite positions response
        underlying: Optional filter for specific underlying

    Returns:
        List of leg dictionaries
    """
    legs = []
    net_positions = positions.get("net", [])

    for pos in net_positions:
        # Skip if no quantity
        if pos.get("quantity", 0) == 0:
            continue

        # Filter by underlying if specified
        tradingsymbol = pos.get("tradingsymbol", "")
        if underlying:
            if underlying.upper() not in tradingsymbol.upper():
                continue

        # Parse position into leg format
        quantity = pos.get("quantity", 0)
        transaction_type = "BUY" if quantity > 0 else "SELL"

        leg = {
            "tradingsymbol": tradingsymbol,
            "instrument_token": pos.get("instrument_token"),
            "exchange": pos.get("exchange", "NFO"),
            "quantity": abs(quantity),
            "transaction_type": transaction_type,
            "entry_price": Decimal(str(pos.get("average_price", 0))),
            "last_price": pos.get("last_price", 0),
            "pnl": pos.get("pnl", 0),
            "product": pos.get("product", "NRML"),
        }

        legs.append(leg)

    return legs
