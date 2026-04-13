"""
TickerPool — Adapter lifecycle manager with ref-counted subscriptions.

Responsibilities:
- Lazy adapter creation (only when first subscription arrives)
- Ref-counted subscriptions (broker subscribe on 0→1, unsubscribe on 1→0)
- Idle cleanup (disconnect adapters with 0 subs after IDLE_TIMEOUT)
- Credential loading and refresh loops
- Tick dispatch: adapter → pool → router
- Failover: migrate_subscriptions(from_broker, to_broker)

Singleton — access via TickerPool.get_instance()
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set, Type, Any

from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.models import NormalizedTick
from app.services.brokers.market_data.ticker.token_policy import can_auto_refresh
from app.services.brokers.platform_token_refresh import refresh_broker_token

# TYPE_CHECKING avoids circular import — HealthMonitor is only used for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.brokers.market_data.ticker.health import HealthMonitor

logger = logging.getLogger(__name__)

# Disconnect adapters after this many seconds with zero subscriptions
IDLE_TIMEOUT_S = 300  # 5 minutes


class TickerPool:
    """
    Manages TickerAdapter instances and aggregates subscriptions via ref-counting.

    Usage:
        pool = TickerPool.get_instance()
        await pool.initialize(on_tick_callback=router.dispatch)
        pool.register_adapter("smartapi", SmartAPITickerAdapter)
        await pool.subscribe("smartapi", [256265], mode="quote")
    """

    _instance: Optional["TickerPool"] = None

    @classmethod
    def get_instance(cls) -> "TickerPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def __init__(self) -> None:
        # Adapter registry: broker_type → adapter class
        self._adapter_classes: Dict[str, Type[TickerAdapter]] = {}

        # Live adapters: broker_type → adapter instance
        self._adapters: Dict[str, TickerAdapter] = {}

        # Ref-counted subscriptions: broker_type → {token → ref_count}
        self._subscriptions: Dict[str, Dict[int, int]] = defaultdict(dict)

        # Credentials: broker_type → credentials dict
        self._credentials: Dict[str, dict] = {}

        # Idle tracking: broker_type → timestamp of last unsubscribe that hit 0
        self._idle_since: Dict[str, datetime] = {}

        # Tick callback (set by initialize, typically TickerRouter.dispatch)
        self._on_tick: Optional[Callable[[List[NormalizedTick]], Any]] = None

        # Health monitor (set by initialize, optional)
        self._health_monitor: Optional["HealthMonitor"] = None

        # Background tasks
        self._idle_cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False

    # ═══════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════

    async def initialize(
        self,
        on_tick_callback: Callable[[List[NormalizedTick]], Any],
        health_monitor: Optional["HealthMonitor"] = None,
    ) -> None:
        """Initialize the pool with a tick dispatch callback (typically TickerRouter.dispatch)."""
        self._on_tick = on_tick_callback
        self._health_monitor = health_monitor
        self._idle_cleanup_task = asyncio.create_task(self._idle_cleanup_loop())
        self._initialized = True
        logger.info("TickerPool initialized (health_monitor=%s)", "enabled" if health_monitor else "disabled")

    async def shutdown(self) -> None:
        """Disconnect all adapters and cancel background tasks."""
        logger.info("TickerPool shutting down...")
        if self._idle_cleanup_task:
            self._idle_cleanup_task.cancel()
            try:
                await self._idle_cleanup_task
            except asyncio.CancelledError:
                pass

        for broker_type in list(self._adapters):
            await self.remove_adapter(broker_type)

        self._subscriptions.clear()
        self._idle_since.clear()
        self._initialized = False
        logger.info("TickerPool shut down")

    # ═══════════════════════════════════════════════════════════════════════
    # ADAPTER REGISTRY
    # ═══════════════════════════════════════════════════════════════════════

    def register_adapter(self, broker_type: str, adapter_class: Type[TickerAdapter]) -> None:
        """Register an adapter class for a broker type."""
        self._adapter_classes[broker_type] = adapter_class
        logger.info("Registered ticker adapter: %s", broker_type)

    def set_credentials(self, broker_type: str, credentials: dict) -> None:
        """Set credentials for a broker. Called before first subscription."""
        self._credentials[broker_type] = credentials

    def credentials_valid(self, broker_type: str) -> bool:
        """Check if cached credentials exist and are not expired.

        Returns True if credentials are set and either:
        - No token_expiry is set (static tokens, never expire)
        - token_expiry is in the future

        Returns False if:
        - No credentials set for this broker
        - token_expiry is in the past
        """
        creds = self._credentials.get(broker_type)
        if not creds:
            return False

        expiry = creds.get("token_expiry")
        if expiry is None:
            return True

        return datetime.now(timezone.utc) < expiry

    def clear_expired_credentials(self) -> list[str]:
        """Remove cached credentials that have expired.

        Returns list of broker_types that were cleared.
        """
        expired = []
        for broker_type, creds in list(self._credentials.items()):
            expiry = creds.get("token_expiry")
            if expiry is not None and datetime.now(timezone.utc) >= expiry:
                del self._credentials[broker_type]
                expired.append(broker_type)
                logger.info("[TickerPool] Cleared expired credentials for %s", broker_type)
        return expired

    # ═══════════════════════════════════════════════════════════════════════
    # ADAPTER LIFECYCLE (lazy creation)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_or_create_adapter(self, broker_type: str) -> TickerAdapter:
        """Get an existing adapter or create + connect a new one.

        If credentials are expired and the broker supports auto-refresh,
        attempts to refresh before connecting.
        """
        if broker_type in self._adapters:
            adapter = self._adapters[broker_type]
            if adapter.is_connected:
                return adapter
            # Adapter exists but disconnected — reconnect
            creds = self._credentials.get(broker_type, {})
            success = await adapter.reconnect(creds)
            if success:
                return adapter
            # Reconnect failed — remove and recreate
            await self.remove_adapter(broker_type)

        if broker_type not in self._adapter_classes:
            raise ValueError(f"No adapter registered for broker: {broker_type}")

        # Check if credentials are expired — attempt auto-refresh
        if not self.credentials_valid(broker_type) and can_auto_refresh(broker_type):
            logger.info("[TickerPool] %s credentials expired — attempting refresh", broker_type)
            refreshed = await refresh_broker_token(broker_type)
            if not refreshed:
                logger.warning("[TickerPool] %s refresh failed", broker_type)
                # Clear expired credentials so the check below raises properly
                self._credentials.pop(broker_type, None)

        creds = self._credentials.get(broker_type, {})
        if not creds:
            raise ValueError(f"No credentials set for broker: {broker_type}")

        adapter_class = self._adapter_classes[broker_type]
        adapter = adapter_class(broker_type)
        adapter.set_on_tick_callback(self._on_adapter_tick)
        adapter.set_on_error_callback(self._on_adapter_error)
        loop = asyncio.get_running_loop()
        adapter.set_event_loop(loop)
        await adapter.connect(creds)

        self._adapters[broker_type] = adapter
        self._idle_since.pop(broker_type, None)
        if self._health_monitor:
            self._health_monitor.record_connect(broker_type)
        logger.info("Created and connected adapter: %s", broker_type)
        return adapter

    async def remove_adapter(self, broker_type: str) -> None:
        """Disconnect and remove an adapter."""
        adapter = self._adapters.pop(broker_type, None)
        if adapter:
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.warning("Error disconnecting %s adapter: %s", broker_type, e)
        if self._health_monitor:
            self._health_monitor.record_disconnect(broker_type)
        self._subscriptions.pop(broker_type, None)
        self._idle_since.pop(broker_type, None)
        logger.info("Removed adapter: %s", broker_type)

    # ═══════════════════════════════════════════════════════════════════════
    # REF-COUNTED SUBSCRIPTIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, broker_type: str, tokens: List[int], mode: str = "quote") -> None:
        """
        Increment ref counts. Only calls adapter.subscribe() for tokens going 0 → 1.
        """
        adapter = await self.get_or_create_adapter(broker_type)
        refs = self._subscriptions[broker_type]

        new_tokens = []
        for token in tokens:
            prev = refs.get(token, 0)
            refs[token] = prev + 1
            if prev == 0:
                new_tokens.append(token)

        if new_tokens:
            await adapter.subscribe(new_tokens, mode)
            # No longer idle
            self._idle_since.pop(broker_type, None)
            logger.debug(
                "[%s] Subscribed %d new tokens (ref-count), %d total unique",
                broker_type, len(new_tokens), len(refs),
            )

    async def unsubscribe(self, broker_type: str, tokens: List[int]) -> None:
        """
        Decrement ref counts. Only calls adapter.unsubscribe() for tokens going 1 → 0.
        """
        refs = self._subscriptions.get(broker_type, {})
        adapter = self._adapters.get(broker_type)

        remove_tokens = []
        for token in tokens:
            count = refs.get(token, 0)
            if count <= 1:
                refs.pop(token, None)
                remove_tokens.append(token)
            else:
                refs[token] = count - 1

        if remove_tokens and adapter and adapter.is_connected:
            await adapter.unsubscribe(remove_tokens)
            logger.debug(
                "[%s] Unsubscribed %d tokens (ref-count hit 0), %d remaining",
                broker_type, len(remove_tokens), len(refs),
            )

        # If no more subscriptions, mark idle
        if not refs and broker_type in self._adapters:
            self._idle_since[broker_type] = datetime.now()
            logger.debug("[%s] No subscriptions remaining — marked idle", broker_type)

    def get_ref_count(self, broker_type: str, token: int) -> int:
        """Get current ref count for a token (for testing/debugging)."""
        return self._subscriptions.get(broker_type, {}).get(token, 0)

    def get_subscribed_tokens(self, broker_type: str) -> Set[int]:
        """Get all tokens with ref_count > 0 for a broker."""
        return set(self._subscriptions.get(broker_type, {}).keys())

    # ═══════════════════════════════════════════════════════════════════════
    # TICK DISPATCH
    # ═══════════════════════════════════════════════════════════════════════

    async def _on_adapter_tick(self, ticks: List[NormalizedTick]) -> None:
        """Called by adapters when ticks arrive. Forwards to router and records in health monitor."""
        if self._health_monitor and ticks:
            broker_type = ticks[0].broker_type
            self._health_monitor.record_ticks(broker_type, len(ticks))
        if self._on_tick:
            try:
                result = self._on_tick(ticks)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("Error dispatching ticks to router: %s", e, exc_info=True)

    def _on_adapter_error(self, broker_type: str, error_type: str, error_msg: str) -> None:
        """Called by adapters on errors. Forwards to health monitor."""
        if self._health_monitor:
            self._health_monitor.record_error(broker_type, f"{error_type}: {error_msg}")

    # ═══════════════════════════════════════════════════════════════════════
    # FAILOVER SUPPORT
    # ═══════════════════════════════════════════════════════════════════════

    async def migrate_subscriptions(self, from_broker: str, to_broker: str) -> None:
        """
        Make-before-break: subscribe on target, then unsubscribe from source.

        1. Copy all subscribed tokens from source
        2. Subscribe on target (target adapter created if needed)
        3. Wait briefly for target ticks to start flowing
        4. Unsubscribe from source
        """
        source_tokens = list(self.get_subscribed_tokens(from_broker))
        if not source_tokens:
            logger.info("No subscriptions to migrate from %s to %s", from_broker, to_broker)
            return

        logger.info(
            "Migrating %d tokens from %s → %s (make-before-break)",
            len(source_tokens), from_broker, to_broker,
        )

        # Subscribe on target first
        source_refs = dict(self._subscriptions.get(from_broker, {}))
        target_refs = self._subscriptions[to_broker]
        for token, count in source_refs.items():
            target_refs[token] = target_refs.get(token, 0) + count

        target_adapter = await self.get_or_create_adapter(to_broker)
        await target_adapter.subscribe(source_tokens)

        # Brief overlap period — both adapters sending ticks
        await asyncio.sleep(2)

        # Unsubscribe from source
        source_adapter = self._adapters.get(from_broker)
        if source_adapter and source_adapter.is_connected:
            await source_adapter.unsubscribe(source_tokens)
        self._subscriptions.pop(from_broker, None)
        self._idle_since[from_broker] = datetime.now()

        logger.info("Migration %s → %s complete", from_broker, to_broker)

    # ═══════════════════════════════════════════════════════════════════════
    # IDLE CLEANUP
    # ═══════════════════════════════════════════════════════════════════════

    async def _idle_cleanup_loop(self) -> None:
        """Background task: disconnect adapters idle for > IDLE_TIMEOUT_S."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            now = datetime.now()
            for broker_type in list(self._idle_since):
                idle_since = self._idle_since[broker_type]
                if (now - idle_since).total_seconds() >= IDLE_TIMEOUT_S:
                    logger.info("[%s] Idle for >%ds — disconnecting", broker_type, IDLE_TIMEOUT_S)
                    await self.remove_adapter(broker_type)

    # ═══════════════════════════════════════════════════════════════════════
    # DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def active_adapters(self) -> List[str]:
        """List of broker types with active (connected) adapters."""
        return [b for b, a in self._adapters.items() if a.is_connected]

    @property
    def adapter_count(self) -> int:
        return len(self._adapters)

    def get_adapter(self, broker_type: str) -> Optional[TickerAdapter]:
        """Get adapter instance (for health monitoring). May be None."""
        return self._adapters.get(broker_type)

    def stats(self) -> dict:
        """Diagnostic snapshot."""
        return {
            "adapters": {
                b: {
                    "connected": a.is_connected,
                    "subscribed_tokens": len(a.subscribed_tokens),
                    "last_tick": a.last_tick_time.isoformat() if a.last_tick_time else None,
                    "reconnects": a.reconnect_count,
                }
                for b, a in self._adapters.items()
            },
            "ref_counts": {
                b: dict(refs) for b, refs in self._subscriptions.items() if refs
            },
            "idle_adapters": list(self._idle_since.keys()),
            "registered": list(self._adapter_classes.keys()),
        }
