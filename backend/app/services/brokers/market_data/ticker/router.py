"""
TickerRouter — User WebSocket fan-out and tick dispatch.

Responsibilities:
- Track user → websocket + broker mapping
- Track token → set[user_ids] for fan-out
- Hot-path dispatch: fan out NormalizedTick to all subscribed users
- Cached ticks: send last known tick immediately on subscribe (instant UI)
- Failover routing: switch users between brokers without reconnect

Singleton — access via TickerRouter.get_instance()
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from starlette.websockets import WebSocket, WebSocketState

from app.services.brokers.market_data.ticker.models import NormalizedTick

logger = logging.getLogger(__name__)


class TickerRouter:
    """
    Fan-out normalized ticks to subscribed WebSocket clients.

    Usage:
        router = TickerRouter.get_instance()
        await router.register_user("user-1", websocket, "smartapi")
        await router.subscribe("user-1", [256265])
        # ... ticks dispatched automatically via dispatch()
    """

    _instance: Optional["TickerRouter"] = None

    @classmethod
    def get_instance(cls) -> "TickerRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def __init__(self) -> None:
        # user_id → {websocket, broker_type, subscribed_tokens}
        self._users: Dict[str, Dict[str, Any]] = {}

        # token → set of user_ids subscribed to that token
        self._token_subscriptions: Dict[int, Set[str]] = {}

        # token → last NormalizedTick (for instant delivery on subscribe)
        self._cached_ticks: Dict[int, NormalizedTick] = {}

        # Reference to pool (set via set_pool)
        self._pool: Any = None  # TickerPool — avoid circular import

    # ═══════════════════════════════════════════════════════════════════════
    # POOL INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════

    def set_pool(self, pool: Any) -> None:
        """Set the TickerPool reference for forwarding subscription requests."""
        self._pool = pool

    # ═══════════════════════════════════════════════════════════════════════
    # USER MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    async def register_user(self, user_id: str, websocket: WebSocket, broker_type: str) -> None:
        """Register a user's WebSocket connection with their preferred broker."""
        self._users[user_id] = {
            "websocket": websocket,
            "broker_type": broker_type,
            "subscribed_tokens": set(),
        }
        logger.debug("User %s registered (broker: %s)", user_id, broker_type)

    async def unregister_user(self, user_id: str) -> None:
        """Unregister user and clean up all their subscriptions."""
        user = self._users.pop(user_id, None)
        if not user:
            return

        tokens = user.get("subscribed_tokens", set())
        broker_type = user.get("broker_type", "")

        # Remove from token→user mappings
        for token in tokens:
            subs = self._token_subscriptions.get(token)
            if subs:
                subs.discard(user_id)
                if not subs:
                    del self._token_subscriptions[token]

        # Decrement pool ref counts
        if tokens and self._pool and broker_type:
            try:
                await self._pool.unsubscribe(broker_type, list(tokens))
            except Exception as e:
                logger.warning("Error unsubscribing user %s tokens: %s", user_id, e)

        logger.debug("User %s unregistered (%d tokens cleaned up)", user_id, len(tokens))

    # ═══════════════════════════════════════════════════════════════════════
    # SUBSCRIPTIONS
    # ═══════════════════════════════════════════════════════════════════════

    async def subscribe(self, user_id: str, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe a user to tokens. Forwards to pool and sends cached ticks.
        """
        user = self._users.get(user_id)
        if not user:
            logger.warning("Cannot subscribe — user %s not registered", user_id)
            return

        broker_type = user["broker_type"]
        user_tokens: Set[int] = user["subscribed_tokens"]

        new_tokens = [t for t in tokens if t not in user_tokens]
        if not new_tokens:
            return

        # Update token → user mappings
        for token in new_tokens:
            if token not in self._token_subscriptions:
                self._token_subscriptions[token] = set()
            self._token_subscriptions[token].add(user_id)
        user_tokens.update(new_tokens)

        # Forward to pool (ref counting)
        if self._pool:
            await self._pool.subscribe(broker_type, new_tokens, mode)

        # Send cached ticks immediately (instant UI)
        cached = [self._cached_ticks[t] for t in new_tokens if t in self._cached_ticks]
        if cached:
            await self._send_to_user(user_id, cached)

        logger.debug("User %s subscribed to %d tokens", user_id, len(new_tokens))

    async def unsubscribe(self, user_id: str, tokens: List[int]) -> None:
        """Unsubscribe a user from tokens."""
        user = self._users.get(user_id)
        if not user:
            return

        broker_type = user["broker_type"]
        user_tokens: Set[int] = user["subscribed_tokens"]

        active = [t for t in tokens if t in user_tokens]
        if not active:
            return

        # Remove from token → user mappings
        for token in active:
            subs = self._token_subscriptions.get(token)
            if subs:
                subs.discard(user_id)
                if not subs:
                    del self._token_subscriptions[token]
        user_tokens.difference_update(active)

        # Forward to pool (ref counting)
        if self._pool:
            await self._pool.unsubscribe(broker_type, active)

        logger.debug("User %s unsubscribed from %d tokens", user_id, len(active))

    # ═══════════════════════════════════════════════════════════════════════
    # TICK DISPATCH (HOT PATH)
    # ═══════════════════════════════════════════════════════════════════════

    async def dispatch(self, ticks: List[NormalizedTick]) -> None:
        """
        Fan out ticks to all subscribed users. Called by TickerPool.

        Optimized for throughput:
        - Single pass to group ticks by user
        - Concurrent sends via asyncio.gather
        - No locks (GIL protects dict reads on single-writer patterns)
        """
        if not ticks:
            return

        # Update tick cache
        for tick in ticks:
            self._cached_ticks[tick.token] = tick

        # Group ticks by user
        user_ticks: Dict[str, List[NormalizedTick]] = {}
        for tick in ticks:
            subscribers = self._token_subscriptions.get(tick.token)
            if not subscribers:
                continue
            for user_id in subscribers:
                if user_id not in user_ticks:
                    user_ticks[user_id] = []
                user_ticks[user_id].append(tick)

        if not user_ticks:
            return

        # Send concurrently
        tasks = [
            self._send_to_user(uid, uticks)
            for uid, uticks in user_ticks.items()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_user(self, user_id: str, ticks: List[NormalizedTick]) -> None:
        """Send ticks to a single user's WebSocket."""
        user = self._users.get(user_id)
        if not user:
            return

        ws: WebSocket = user["websocket"]
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                payload = json.dumps({
                    "type": "ticks",
                    "data": [t.to_dict() for t in ticks],
                })
                await ws.send_text(payload)
        except Exception:
            # WebSocket broken — unregister user
            logger.debug("WebSocket send failed for user %s — unregistering", user_id)
            await self.unregister_user(user_id)

    # ═══════════════════════════════════════════════════════════════════════
    # FAILOVER
    # ═══════════════════════════════════════════════════════════════════════

    async def switch_user_broker(self, user_id: str, to_broker: str) -> None:
        """
        Switch a single user's broker live — called when user changes market data source preference.

        Unsubscribes existing tokens from old broker, re-subscribes on new broker,
        and sends a "source_changed" WebSocket message to update the frontend badge.
        """
        user = self._users.get(user_id)
        if not user:
            return  # User not connected — preference will be applied on next connect

        old_broker = user["broker_type"]
        if old_broker == to_broker:
            return  # Already on the right broker

        tokens = list(user.get("subscribed_tokens", set()))
        mode = "quote"

        # Unsubscribe from old broker
        if tokens and self._pool:
            try:
                await self._pool.unsubscribe(old_broker, tokens)
            except Exception as e:
                logger.warning("switch_user_broker: unsubscribe from %s failed: %s", old_broker, e)

        # Update broker in-place
        user["broker_type"] = to_broker

        # Re-subscribe on new broker
        if tokens and self._pool:
            try:
                await self._pool.subscribe(to_broker, tokens, mode)
            except Exception as e:
                logger.warning("switch_user_broker: subscribe to %s failed: %s", to_broker, e)

        # Notify frontend so badge updates immediately
        ws: WebSocket = user["websocket"]
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(json.dumps({
                    "type": "source_changed",
                    "data": {
                        "from_broker": old_broker,
                        "to_broker": to_broker,
                    },
                }))
        except Exception:
            pass

        logger.info("User %s switched broker %s → %s", user_id, old_broker, to_broker)

    async def switch_users_broker(self, from_broker: str, to_broker: str) -> None:
        """
        Switch all users on from_broker to to_broker.
        Called by FailoverController after pool.migrate_subscriptions().
        """
        switched = 0
        for user_id, user in self._users.items():
            if user["broker_type"] == from_broker:
                user["broker_type"] = to_broker
                switched += 1

        if switched:
            logger.info("Switched %d users from %s → %s", switched, from_broker, to_broker)
            await self._broadcast_failover_notification(from_broker, to_broker)

    async def _broadcast_failover_notification(self, from_broker: str, to_broker: str) -> None:
        """Notify affected users about broker switch."""
        payload = json.dumps({
            "type": "failover",
            "data": {
                "from_broker": from_broker,
                "to_broker": to_broker,
                "timestamp": datetime.now().isoformat(),
                "message": f"Data source switched from {from_broker} to {to_broker}",
            },
        })
        for user_id, user in self._users.items():
            if user["broker_type"] == to_broker:
                ws: WebSocket = user["websocket"]
                try:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_text(payload)
                except Exception:
                    pass

    # ═══════════════════════════════════════════════════════════════════════
    # QUERY HELPERS
    # ═══════════════════════════════════════════════════════════════════════

    def get_user_broker(self, user_id: str) -> Optional[str]:
        """Get the broker type for a user."""
        user = self._users.get(user_id)
        return user["broker_type"] if user else None

    def get_subscribed_tokens_for_broker(self, broker_type: str) -> Set[int]:
        """Get all tokens subscribed by users on a specific broker."""
        tokens: Set[int] = set()
        for user in self._users.values():
            if user["broker_type"] == broker_type:
                tokens.update(user["subscribed_tokens"])
        return tokens

    def get_cached_tick(self, token: int) -> Optional[NormalizedTick]:
        """Get the last cached tick for a token."""
        return self._cached_ticks.get(token)

    # ═══════════════════════════════════════════════════════════════════════
    # DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def connected_users(self) -> int:
        return len(self._users)

    @property
    def total_token_subscriptions(self) -> int:
        return len(self._token_subscriptions)

    @property
    def cached_tick_count(self) -> int:
        return len(self._cached_ticks)

    def stats(self) -> dict:
        return {
            "connected_users": self.connected_users,
            "total_token_subscriptions": self.total_token_subscriptions,
            "cached_ticks": self.cached_tick_count,
            "users_by_broker": self._count_users_by_broker(),
        }

    def _count_users_by_broker(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for user in self._users.values():
            b = user["broker_type"]
            counts[b] = counts.get(b, 0) + 1
        return counts
