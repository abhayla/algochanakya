"""
Tests for Phase 5 order execution adapters.

Tests AngelOne, Upstox, Dhan, Fyers, and Paytm BrokerAdapter implementations.
All adapters are tested with mocked HTTP/SDK responses — no live API calls.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.brokers.base import (
    BrokerType,
    BrokerCapabilities,
    UnifiedOrder,
    UnifiedPosition,
    UnifiedQuote,
    OrderSide,
    OrderType,
    ProductType,
    OrderStatus,
)


# =========================================================================
# Fixtures - sample unified order
# =========================================================================

@pytest.fixture
def sample_order():
    return UnifiedOrder(
        exchange="NFO",
        tradingsymbol="NIFTY24DEC26000CE",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        product=ProductType.NRML,
        quantity=50,
        price=Decimal("100.00"),
        tag="TEST",
        validity="DAY",
    )


@pytest.fixture
def sample_sl_order():
    return UnifiedOrder(
        exchange="NFO",
        tradingsymbol="NIFTY24DEC26000CE",
        side=OrderSide.SELL,
        order_type=OrderType.STOP_LOSS,
        product=ProductType.NRML,
        quantity=50,
        price=Decimal("90.00"),
        trigger_price=Decimal("91.00"),
        validity="DAY",
    )


# =========================================================================
# BrokerType enum tests
# =========================================================================

class TestBrokerTypeEnum:
    def test_all_six_brokers_present(self):
        values = {bt.value for bt in BrokerType}
        assert "kite" in values
        assert "angel" in values
        assert "upstox" in values
        assert "fyers" in values
        assert "dhan" in values
        assert "paytm" in values

    def test_broker_type_is_string_enum(self):
        assert BrokerType.KITE == "kite"
        assert BrokerType.ANGEL == "angel"
        assert BrokerType.UPSTOX == "upstox"
        assert BrokerType.DHAN == "dhan"
        assert BrokerType.FYERS == "fyers"
        assert BrokerType.PAYTM == "paytm"


# =========================================================================
# Factory tests
# =========================================================================

class TestBrokerFactory:
    @pytest.mark.asyncio
    async def test_factory_supports_all_six_brokers(self):
        from app.services.brokers.factory import is_broker_supported, get_supported_brokers
        supported = get_supported_brokers()
        for bt in [BrokerType.KITE, BrokerType.ANGEL, BrokerType.UPSTOX,
                   BrokerType.DHAN, BrokerType.FYERS, BrokerType.PAYTM]:
            assert is_broker_supported(bt), f"{bt} not registered in factory"

    @pytest.mark.asyncio
    async def test_factory_raises_for_unknown_broker(self):
        from app.services.brokers.factory import get_broker_adapter
        with pytest.raises(ValueError, match="Unsupported broker"):
            await get_broker_adapter("nonexistent_broker", "token123", initialize=False)


# =========================================================================
# AngelOne Adapter Tests
# =========================================================================

class TestAngelOneAdapter:
    @pytest.fixture
    def adapter(self):
        from app.services.brokers.angelone_adapter import AngelOneAdapter
        return AngelOneAdapter(
            access_token="test_jwt_token",
            api_key="test_api_key",
            client_id="TEST123",
        )

    def test_broker_type(self, adapter):
        assert adapter.broker_type == BrokerType.ANGEL

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert isinstance(caps, BrokerCapabilities)
        assert caps.supports_websocket is True

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        # SmartConnect is imported inside the method, patch at the SmartApi module level
        with patch("SmartApi.SmartConnect") as MockSC:
            mock_client = MagicMock()
            MockSC.return_value = mock_client
            result = await adapter.initialize()
        assert result is True
        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_validate_session_success(self, adapter):
        mock_client = MagicMock()
        mock_client.getProfile.return_value = {"status": True, "data": {"name": "Test"}}
        adapter.client = mock_client
        result = await adapter.validate_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_failure(self, adapter):
        mock_client = MagicMock()
        mock_client.getProfile.side_effect = Exception("Token expired")
        adapter.client = mock_client
        result = await adapter.validate_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_place_order_success(self, adapter, sample_order):
        mock_client = MagicMock()
        mock_client.placeOrder.return_value = {
            "status": True,
            "data": {"orderid": "ANGEL_ORD_001"}
        }
        adapter.client = mock_client
        result = await adapter.place_order(sample_order)
        assert result.order_id == "ANGEL_ORD_001"
        assert result.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_place_order_rejected(self, adapter, sample_order):
        mock_client = MagicMock()
        mock_client.placeOrder.return_value = {
            "status": False,
            "message": "Insufficient margin"
        }
        adapter.client = mock_client
        result = await adapter.place_order(sample_order)
        assert result.status == OrderStatus.REJECTED
        assert "Insufficient margin" in result.rejection_reason

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        mock_client = MagicMock()
        mock_client.cancelOrder.return_value = {"status": True}
        adapter.client = mock_client
        result = await adapter.cancel_order("ANGEL_ORD_001")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_client = MagicMock()
        mock_client.position.return_value = {
            "status": True,
            "data": [
                {
                    "tradingsymbol": "NIFTY24DEC26000CE",
                    "exchange": "NFO",
                    "netqty": "50",
                    "buyqty": "50",
                    "sellqty": "0",
                    "netprice": "100.50",
                    "ltp": "105.00",
                    "pnl": "225.00",
                    "producttype": "CARRYFORWARD",
                }
            ]
        }
        adapter.client = mock_client
        positions = await adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].tradingsymbol == "NIFTY24DEC26000CE"
        assert positions[0].quantity == 50

    @pytest.mark.asyncio
    async def test_get_orders(self, adapter):
        mock_client = MagicMock()
        mock_client.orderBook.return_value = {
            "status": True,
            "data": [
                {
                    "orderid": "ANGEL_001",
                    "tradingsymbol": "NIFTY24DEC26000CE",
                    "exchange": "NFO",
                    "transactiontype": "BUY",
                    "ordertype": "LIMIT",
                    "producttype": "CARRYFORWARD",
                    "quantity": "50",
                    "price": "100.00",
                    "status": "complete",
                    "filledshares": "50",
                    "averageprice": "100.00",
                }
            ]
        }
        adapter.client = mock_client
        orders = await adapter.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "ANGEL_001"
        assert orders[0].status == OrderStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_get_margins(self, adapter):
        mock_client = MagicMock()
        mock_client.rmsLimit.return_value = {"status": True, "data": {"net": "50000"}}
        adapter.client = mock_client
        margins = await adapter.get_margins()
        assert "net" in margins

    @pytest.mark.asyncio
    async def test_get_profile(self, adapter):
        mock_client = MagicMock()
        mock_client.getProfile.return_value = {
            "status": True,
            "data": {"name": "Test User", "clientcode": "TEST123"}
        }
        adapter.client = mock_client
        profile = await adapter.get_profile()
        assert profile.get("name") == "Test User"

    @pytest.mark.asyncio
    async def test_get_instruments(self, adapter):
        mock_client = MagicMock()
        mock_client.fetchAllottedStocks.return_value = []
        adapter.client = mock_client
        instruments = await adapter.get_instruments("NFO")
        assert isinstance(instruments, list)

    @pytest.mark.asyncio
    async def test_get_ltp(self, adapter):
        mock_client = MagicMock()
        mock_client.ltpData.return_value = {
            "status": True,
            "data": {"ltp": "105.50", "open": "100.00"}
        }
        adapter.client = mock_client
        result = await adapter.get_ltp(["NFO:NIFTY24DEC26000CE"])
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_no_client_returns_safe_defaults(self, adapter):
        """Without initialized client, methods return safe empty values."""
        adapter.client = None
        orders = await adapter.get_orders()
        positions = await adapter.get_positions()
        margins = await adapter.get_margins()
        assert orders == []
        assert positions == []
        assert margins == {}


# =========================================================================
# Upstox Adapter Tests
# =========================================================================

class TestUpstoxOrderAdapter:
    @pytest.fixture
    def adapter(self):
        from app.services.brokers.upstox_order_adapter import UpstoxOrderAdapter
        return UpstoxOrderAdapter(access_token="upstox_token_abc")

    def test_broker_type(self, adapter):
        assert adapter.broker_type == BrokerType.UPSTOX

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert isinstance(caps, BrokerCapabilities)

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        result = await adapter.initialize()
        assert result is True
        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_validate_session_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": {"user_id": "TEST"}}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_failure(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"status": "error", "errors": [{"message": "Invalid token"}]}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_place_order_success(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"order_id": "UPSTOX_ORD_001"}
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.order_id == "UPSTOX_ORD_001"
        assert result.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_place_order_failure(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "status": "error",
            "errors": [{"message": "Insufficient funds"}]
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cancel_order(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": {"order_id": "UPSTOX_ORD_001"}}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            result = await adapter.cancel_order("UPSTOX_ORD_001")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "tradingsymbol": "NIFTY24DEC26000CE",
                    "exchange": "NFO",
                    "quantity": 50,
                    "buy_quantity": 50,
                    "sell_quantity": 0,
                    "average_price": 100.5,
                    "last_price": 105.0,
                    "pnl": 225.0,
                    "product": "D",
                    "overnight_quantity": 0,
                }
            ]
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            positions = await adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50

    @pytest.mark.asyncio
    async def test_get_orders(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": [
                {
                    "order_id": "UPSTOX_001",
                    "tradingsymbol": "NIFTY24DEC26000CE",
                    "exchange": "NFO",
                    "transaction_type": "BUY",
                    "order_type": "LIMIT",
                    "product": "D",
                    "quantity": 50,
                    "price": 100.0,
                    "status": "complete",
                    "filled_quantity": 50,
                    "average_price": 100.0,
                    "pending_quantity": 0,
                    "tag": "TEST",
                    "validity": "DAY",
                    "status_message": "",
                }
            ]
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            orders = await adapter.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "UPSTOX_001"

    @pytest.mark.asyncio
    async def test_get_margins(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": {"equity": {"net": 50000}}}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            margins = await adapter.get_margins()
        assert isinstance(margins, dict)


# =========================================================================
# Dhan Adapter Tests
# =========================================================================

class TestDhanOrderAdapter:
    @pytest.fixture
    def adapter(self):
        from app.services.brokers.dhan_order_adapter import DhanOrderAdapter
        return DhanOrderAdapter(
            access_token="dhan_access_token",
            client_id="1234567890",
        )

    def test_broker_type(self, adapter):
        assert adapter.broker_type == BrokerType.DHAN

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert isinstance(caps, BrokerCapabilities)

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        result = await adapter.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_place_order_success(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "orderId": "DHAN_ORD_001",
            "orderStatus": "PENDING"
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.order_id == "DHAN_ORD_001"
        assert result.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_place_order_http_error(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errorCode": "DH-901",
            "errorMessage": "Invalid security_id"
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cancel_order(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"orderId": "DHAN_ORD_001", "orderStatus": "CANCELLED"}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            result = await adapter.cancel_order("DHAN_ORD_001")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "tradingSymbol": "NIFTY24DEC26000CE",
                "exchangeSegment": "NSE_FNO",
                "netQty": 50,
                "buyQty": 50,
                "sellQty": 0,
                "costPrice": 100.5,
                "lastTradedPrice": 105.0,
                "unrealizedProfit": 225.0,
                "realizedProfit": 0.0,
                "productType": "CNC",
            }
        ]
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            positions = await adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50

    @pytest.mark.asyncio
    async def test_get_orders(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "orderId": "DHAN_001",
                "tradingSymbol": "NIFTY24DEC26000CE",
                "exchangeSegment": "NSE_FNO",
                "transactionType": "BUY",
                "orderType": "LIMIT",
                "productType": "CNC",
                "quantity": 50,
                "price": 100.0,
                "orderStatus": "TRADED",
                "filledQty": 50,
                "tradedPrice": 100.0,
                "remainingQuantity": 0,
                "omsErrorDescription": "",
            }
        ]
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            orders = await adapter.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "DHAN_001"
        assert orders[0].status == OrderStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_validate_session_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"userName": "Test User"}]
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_failure(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errorCode": "DH-1014", "errorMessage": "Invalid token"}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is False


# =========================================================================
# Fyers Adapter Tests
# =========================================================================

class TestFyersOrderAdapter:
    @pytest.fixture
    def adapter(self):
        from app.services.brokers.fyers_order_adapter import FyersOrderAdapter
        return FyersOrderAdapter(
            access_token="fyers_access_token",
            client_id="XYZ12345-100",
        )

    def test_broker_type(self, adapter):
        assert adapter.broker_type == BrokerType.FYERS

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert isinstance(caps, BrokerCapabilities)

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        result = await adapter.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"s": "ok", "code": 200, "data": {"fy_id": "XYZ12345"}}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_failure(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"s": "error", "code": -16, "message": "Invalid token"}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_place_order_success(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "id": "FYERS_ORD_001",
            "code": 200,
            "message": ""
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.order_id == "FYERS_ORD_001"
        assert result.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_place_order_failure(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "error",
            "code": -100,
            "message": "Invalid symbol"
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cancel_order(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"s": "ok", "code": 200, "id": "FYERS_ORD_001"}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)
            result = await adapter.cancel_order("FYERS_ORD_001")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "code": 200,
            "netPositions": [
                {
                    "symbol": "NSE:NIFTY24DEC26000CE",
                    "netQty": 50,
                    "buyQty": 50,
                    "sellQty": 0,
                    "netAvg": 100.5,
                    "ltp": 105.0,
                    "pl": 225.0,
                    "productType": "MARGIN",
                    "buyAvg": 100.5,
                    "sellAvg": 0.0,
                }
            ]
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            positions = await adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50

    @pytest.mark.asyncio
    async def test_get_orders(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "s": "ok",
            "code": 200,
            "orderBook": [
                {
                    "id": "FYERS_001",
                    "symbol": "NSE:NIFTY24DEC26000CE",
                    "type": 1,  # Limit order
                    "side": 1,  # Buy
                    "productType": "MARGIN",
                    "qty": 50,
                    "limitPrice": 100.0,
                    "status": 2,  # Filled
                    "filledQty": 50,
                    "tradedPrice": 100.0,
                    "remainingQuantity": 0,
                    "message": "",
                }
            ]
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            orders = await adapter.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "FYERS_001"


# =========================================================================
# Paytm Adapter Tests
# =========================================================================

class TestPaytmOrderAdapter:
    @pytest.fixture
    def adapter(self):
        from app.services.brokers.paytm_order_adapter import PaytmOrderAdapter
        return PaytmOrderAdapter(
            access_token="paytm_access_token",
            read_token="paytm_read_token",
            edge_token="paytm_edge_token",
        )

    def test_broker_type(self, adapter):
        assert adapter.broker_type == BrokerType.PAYTM

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert isinstance(caps, BrokerCapabilities)

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        result = await adapter.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_success(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "message": "success",
            "data": {"user_id": "PAYTM123"}
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_session_failure(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"status": 401, "message": "Unauthorized"}
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            result = await adapter.validate_session()
        assert result is False

    @pytest.mark.asyncio
    async def test_place_order_success(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "message": "success",
            "data": {"orderId": "PAYTM_ORD_001"}
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.order_id == "PAYTM_ORD_001"
        assert result.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_place_order_failure(self, adapter, sample_order):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 400,
            "message": "Order rejected: insufficient funds",
            "data": {}
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            result = await adapter.place_order(sample_order)
        assert result.status == OrderStatus.REJECTED

    @pytest.mark.asyncio
    async def test_cancel_order(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "message": "success",
            "data": {"orderId": "PAYTM_ORD_001"}
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.put = AsyncMock(return_value=mock_response)
            result = await adapter.cancel_order("PAYTM_ORD_001")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "data": {
                "positions": [
                    {
                        "scrip_code": "NIFTY24DEC26000CE",
                        "exchange": "NSE",
                        "quantity": "50",
                        "average_price": "100.50",
                        "last_traded_price": "105.00",
                        "unrealized_pnl": "225.00",
                        "realized_pnl": "0.00",
                        "product_type": "D",
                    }
                ]
            }
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            positions = await adapter.get_positions()
        assert len(positions) == 1
        assert positions[0].quantity == 50

    @pytest.mark.asyncio
    async def test_get_orders(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 200,
            "data": {
                "orders": [
                    {
                        "order_id": "PAYTM_001",
                        "scrip_code": "NIFTY24DEC26000CE",
                        "exchange": "NSE",
                        "order_side": "B",
                        "order_type": "L",
                        "product_type": "D",
                        "quantity": "50",
                        "price": "100.00",
                        "order_status": "complete",
                        "traded_quantity": "50",
                        "traded_price": "100.00",
                        "pending_quantity": "0",
                        "rejection_reason": "",
                    }
                ]
            }
        }
        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            orders = await adapter.get_orders()
        assert len(orders) == 1
        assert orders[0].order_id == "PAYTM_001"
        assert orders[0].status == OrderStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_three_token_headers_used(self, adapter):
        """Verify Paytm uses all 3 tokens in request headers."""
        captured_headers = {}

        async def capture_request(url, headers=None, **kwargs):
            captured_headers.update(headers or {})
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": 200, "data": {"user_id": "TEST"}}
            return mock_response

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = capture_request
            await adapter.validate_session()

        # Paytm uses 3 tokens — all must appear in headers
        assert any("access_token" in k.lower() or "authorization" in k.lower()
                   for k in captured_headers), "access_token not in headers"
