"""
Example: Ticker Service Manager (Multiton Pattern)

This is a reference implementation showing how to refactor from multiple
singletons to a centralized manager.

DO NOT import this file - it's for documentation purposes only.
"""
import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TickerServiceManager:
    """
    Centralized manager for all broker ticker services.

    Features:
    - On-demand connection creation
    - Automatic cleanup when unused
    - Fallback support
    - Health monitoring
    - Thread-safe operations
    """

    _instance: Optional['TickerServiceManager'] = None
    _lock = asyncio.Lock()  # For thread-safe singleton creation

    def __init__(self):
        self._active_tickers: Dict[str, Any] = {}  # broker_type -> ticker instance
        self._client_counts: Dict[str, int] = {}  # broker_type -> count
        self._last_activity: Dict[str, datetime] = {}  # broker_type -> timestamp
        self._creation_locks: Dict[str, asyncio.Lock] = {}  # Per-broker locks
        self._cleanup_task: Optional[asyncio.Task] = None

    @classmethod
    async def get_instance(cls) -> 'TickerServiceManager':
        """Get singleton instance (thread-safe)."""
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:  # Double-check
                    cls._instance = cls()
                    # Start cleanup task
                    cls._instance._cleanup_task = asyncio.create_task(
                        cls._instance._cleanup_loop()
                    )
        return cls._instance

    async def get_ticker(
        self,
        broker_type: str,
        credentials: dict,
        fallback_broker: Optional[str] = None
    ) -> Any:
        """
        Get or create ticker service for broker.

        Args:
            broker_type: 'smartapi', 'kite', 'upstox', etc.
            credentials: Broker-specific auth credentials
            fallback_broker: Optional fallback if primary fails

        Returns:
            Active ticker service instance

        Raises:
            ValueError: If broker_type not supported
            ConnectionError: If connection fails (and no fallback)
        """
        # Ensure per-broker lock exists
        if broker_type not in self._creation_locks:
            self._creation_locks[broker_type] = asyncio.Lock()

        # Thread-safe creation
        async with self._creation_locks[broker_type]:
            if broker_type not in self._active_tickers:
                try:
                    ticker = self._create_ticker(broker_type)
                    await ticker.connect(**credentials)

                    self._active_tickers[broker_type] = ticker
                    self._client_counts[broker_type] = 0
                    self._last_activity[broker_type] = datetime.now()

                    logger.info(f"[TickerManager] Created {broker_type} ticker")

                except Exception as e:
                    logger.error(f"[TickerManager] Failed to create {broker_type}: {e}")

                    # Try fallback
                    if fallback_broker:
                        logger.info(f"[TickerManager] Trying fallback: {fallback_broker}")
                        return await self.get_ticker(fallback_broker, credentials)

                    raise ConnectionError(f"Failed to connect to {broker_type}: {e}")

            # Update activity timestamp
            self._last_activity[broker_type] = datetime.now()

            return self._active_tickers[broker_type]

    def _create_ticker(self, broker_type: str) -> Any:
        """
        Factory method to create broker-specific ticker.

        To add a new broker:
        1. Implement TickerServiceBase interface
        2. Add to ticker_classes dict below
        3. Done! No other code changes needed.
        """
        # Import here to avoid circular dependencies
        from app.services.legacy.smartapi_ticker import SmartAPITickerService
        from app.services.legacy.kite_ticker import KiteTickerService
        # from app.services.brokers.upstox_ticker import UpstoxTickerService
        # from app.services.brokers.dhan_ticker import DhanTickerService

        ticker_classes = {
            'smartapi': SmartAPITickerService,
            'kite': KiteTickerService,
            # Add new brokers here (just one line!)
            # 'upstox': UpstoxTickerService,
            # 'dhan': DhanTickerService,
            # 'fyers': FyersTickerService,
            # 'paytm': PaytmTickerService,
        }

        ticker_class = ticker_classes.get(broker_type)
        if not ticker_class:
            supported = ', '.join(ticker_classes.keys())
            raise ValueError(
                f"Unsupported broker: {broker_type}. "
                f"Supported brokers: {supported}"
            )

        return ticker_class()

    async def register_client(
        self,
        broker_type: str,
        user_id: str,
        websocket: Any,
        credentials: dict
    ):
        """
        Register client and increment usage count.

        Args:
            broker_type: Broker identifier
            user_id: User identifier
            websocket: User's WebSocket connection
            credentials: Broker credentials (for on-demand connection)
        """
        # Get or create ticker
        ticker = await self.get_ticker(broker_type, credentials)

        # Register with ticker
        await ticker.register_client(user_id, websocket)

        # Increment count
        self._client_counts[broker_type] = \
            self._client_counts.get(broker_type, 0) + 1

        logger.info(
            f"[TickerManager] {broker_type} clients: "
            f"{self._client_counts[broker_type]}"
        )

    async def unregister_client(self, broker_type: str, user_id: str):
        """
        Unregister client and decrement usage count.
        Schedules cleanup if count reaches 0.

        Args:
            broker_type: Broker identifier
            user_id: User identifier
        """
        if broker_type not in self._active_tickers:
            return

        # Unregister from ticker
        ticker = self._active_tickers[broker_type]
        await ticker.unregister_client(user_id)

        # Decrement count
        self._client_counts[broker_type] -= 1

        logger.info(
            f"[TickerManager] {broker_type} clients: "
            f"{self._client_counts[broker_type]}"
        )

        # Note: Cleanup happens in background _cleanup_loop()
        # with 30s grace period to avoid disconnect/reconnect thrashing

    async def _cleanup_loop(self):
        """
        Background task that cleans up unused broker connections.

        Disconnects brokers that have:
        - 0 active clients
        - No activity for 30 seconds (grace period)
        """
        GRACE_PERIOD = timedelta(seconds=30)

        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                now = datetime.now()
                brokers_to_cleanup = []

                for broker_type, count in self._client_counts.items():
                    if count <= 0:
                        last_activity = self._last_activity.get(broker_type)
                        if last_activity and (now - last_activity) > GRACE_PERIOD:
                            brokers_to_cleanup.append(broker_type)

                # Cleanup identified brokers
                for broker_type in brokers_to_cleanup:
                    await self._cleanup_broker(broker_type)

            except Exception as e:
                logger.error(f"[TickerManager] Cleanup loop error: {e}")

    async def _cleanup_broker(self, broker_type: str):
        """
        Disconnect and remove unused broker ticker.

        Args:
            broker_type: Broker to cleanup
        """
        if broker_type not in self._active_tickers:
            return

        logger.info(f"[TickerManager] Cleaning up unused {broker_type} ticker")

        ticker = self._active_tickers[broker_type]

        try:
            ticker.disconnect()
        except Exception as e:
            logger.warning(f"[TickerManager] Error disconnecting {broker_type}: {e}")

        # Remove from registry
        del self._active_tickers[broker_type]
        del self._client_counts[broker_type]
        if broker_type in self._last_activity:
            del self._last_activity[broker_type]

    def get_active_brokers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all active brokers.

        Returns:
            Dict mapping broker_type to status info

        Example:
            {
                'smartapi': {
                    'clients': 5,
                    'connected': True,
                    'last_activity': '2026-01-15 10:30:00'
                },
                'kite': {
                    'clients': 2,
                    'connected': True,
                    'last_activity': '2026-01-15 10:29:45'
                }
            }
        """
        status = {}
        for broker_type, ticker in self._active_tickers.items():
            status[broker_type] = {
                'clients': self._client_counts.get(broker_type, 0),
                'connected': ticker.is_connected,
                'last_activity': self._last_activity.get(broker_type).isoformat()
                    if broker_type in self._last_activity else None
            }
        return status

    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for monitoring.

        Returns:
            Health status with metrics
        """
        active_brokers = self.get_active_brokers()
        total_clients = sum(
            broker['clients']
            for broker in active_brokers.values()
        )

        all_connected = all(
            broker['connected']
            for broker in active_brokers.values()
        )

        return {
            'status': 'healthy' if all_connected else 'degraded',
            'active_brokers': len(active_brokers),
            'total_clients': total_clients,
            'brokers': active_brokers,
            'timestamp': datetime.now().isoformat()
        }

    async def force_reconnect(self, broker_type: str, credentials: dict):
        """
        Force reconnection of a broker (useful for credential refresh).

        Args:
            broker_type: Broker to reconnect
            credentials: New credentials
        """
        logger.info(f"[TickerManager] Force reconnecting {broker_type}")

        # Disconnect existing
        if broker_type in self._active_tickers:
            await self._cleanup_broker(broker_type)

        # Reconnect with new credentials
        await self.get_ticker(broker_type, credentials)

    async def shutdown(self):
        """Graceful shutdown - disconnect all brokers."""
        logger.info("[TickerManager] Shutting down all broker connections")

        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Disconnect all brokers
        for broker_type in list(self._active_tickers.keys()):
            await self._cleanup_broker(broker_type)


# Usage Example in WebSocket Route:
"""
from app.services.brokers.ticker_manager import TickerServiceManager

@router.websocket("/ws/ticks")
async def websocket_ticks(websocket: WebSocket, token: str = Query(...)):
    user = None
    broker_type = None
    manager = await TickerServiceManager.get_instance()

    try:
        await websocket.accept()

        # Authenticate
        async for db in get_db():
            user = await get_user_from_token(token, db)
            broker_type = await get_user_market_data_source(user.id, db)
            credentials = await get_broker_credentials(user.id, broker_type, db)
            break

        # Register with manager (auto-creates connection if needed)
        await manager.register_client(
            broker_type=broker_type,
            user_id=str(user.id),
            websocket=websocket,
            credentials=credentials
        )

        # Get ticker service (already connected by register_client)
        ticker = await manager.get_ticker(broker_type, credentials)

        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "broker": broker_type,
            "status": await manager.health_check()
        })

        # Handle messages...
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data['action'] == 'subscribe':
                await ticker.subscribe(data['tokens'], str(user.id))
            # ... other actions

    finally:
        if user and broker_type:
            await manager.unregister_client(broker_type, str(user.id))


# Monitoring Endpoint:
@router.get("/api/admin/websocket-status")
async def get_websocket_status():
    manager = await TickerServiceManager.get_instance()
    return await manager.health_check()
"""
