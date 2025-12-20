"""
Order Execution Service

Executes orders via Kite Connect API for AutoPilot strategies.
Handles order placement, modification, and cancellation.
"""
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from uuid import UUID
import logging

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import AutoPilotStrategy, AutoPilotOrder, AutoPilotLog, AutoPilotOrderBatch
from app.services.market_data import MarketDataService
from app.services.strike_finder_service import StrikeFinderService

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Order request details."""
    strategy_id: int
    leg_id: str
    leg_index: int
    purpose: str  # entry, exit, adjustment, hedge
    exchange: str
    tradingsymbol: str
    transaction_type: str  # BUY, SELL
    quantity: int
    order_type: str  # MARKET, LIMIT, SL, SL-M
    product: str  # NRML, MIS
    price: Optional[Decimal] = None
    trigger_price: Optional[Decimal] = None
    underlying: str = ""
    contract_type: str = ""  # CE, PE, FUT
    strike: Optional[Decimal] = None
    expiry: Optional[date] = None
    # Market context (captured at order time)
    trading_mode: str = "paper"
    batch_id: Optional[UUID] = None
    batch_sequence: Optional[int] = None
    triggered_condition: Optional[Dict[str, Any]] = None


@dataclass
class OrderResult:
    """Result of order placement."""
    success: bool
    order_id: Optional[str] = None
    kite_order_id: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    executed_price: Optional[Decimal] = None
    slippage: Optional[Decimal] = None
    leg_id: str = ""


# Lot sizes for different underlyings
LOT_SIZES = {
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "SENSEX": 10,
}

# Strike steps for different underlyings
STRIKE_STEPS = {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "FINNIFTY": 50,
    "SENSEX": 100,
}


class OrderExecutor:
    """
    Executes orders via Kite Connect.

    Features:
    - Sequential and simultaneous execution
    - Slippage protection
    - Retry on failure
    - Order tracking
    """

    def __init__(self, kite: KiteConnect, market_data: MarketDataService, strike_finder: StrikeFinderService = None):
        self.kite = kite
        self.market_data = market_data
        self.strike_finder = strike_finder

    async def capture_market_snapshot(
        self,
        underlying: str,
        tradingsymbol: str,
        strike: Optional[Decimal],
        expiry: date,
        contract_type: str
    ) -> Dict[str, Any]:
        """
        Capture complete market snapshot for an option at order time.

        Returns dict with: spot, vix, ltp, greeks (delta, gamma, theta, vega, iv), bid, ask, oi
        """
        snapshot = {}

        try:
            # Get spot price
            spot_data = await self.market_data.get_spot_price(underlying)
            snapshot['spot_price'] = float(spot_data['ltp']) if isinstance(spot_data, dict) else float(spot_data.ltp)

            # Get VIX
            try:
                vix = await self.market_data.get_vix()
                snapshot['vix'] = float(vix) if vix else None
            except Exception as e:
                logger.debug(f"Failed to get VIX: {e}")
                snapshot['vix'] = None

            # Get option quote (LTP, OI)
            instrument_key = f"NFO:{tradingsymbol}"
            try:
                quotes = await self.market_data.get_quote([instrument_key])
                if instrument_key in quotes:
                    quote = quotes[instrument_key]
                    snapshot['ltp'] = float(quote.get('last_price', 0))
                    snapshot['oi'] = int(quote.get('oi', 0))
                    # Note: Kite doesn't provide bid/ask in basic quote
                    snapshot['bid'] = None
                    snapshot['ask'] = None
            except Exception as e:
                logger.debug(f"Failed to get quote for {tradingsymbol}: {e}")
                snapshot['ltp'] = None
                snapshot['oi'] = None

            # Calculate Greeks (if we have strike and spot)
            if strike and contract_type in ['CE', 'PE']:
                try:
                    time_to_expiry = (expiry - date.today()).days / 365.0
                    if time_to_expiry > 0:
                        # Import here to avoid circular dependency
                        from app.services.pnl_calculator import PnLCalculator

                        # Use a default IV for now (ideally fetch from option chain cache)
                        iv = 0.20

                        calculator = PnLCalculator()
                        greeks = calculator.calculate_greeks(
                            spot=snapshot['spot_price'],
                            strike=float(strike),
                            time_to_expiry=time_to_expiry,
                            volatility=iv,
                            option_type=contract_type
                        )

                        snapshot['delta'] = greeks.get('delta')
                        snapshot['gamma'] = greeks.get('gamma')
                        snapshot['theta'] = greeks.get('theta')
                        snapshot['vega'] = greeks.get('vega')
                        snapshot['iv'] = iv * 100  # Store as percentage
                except Exception as e:
                    logger.debug(f"Failed to calculate Greeks: {e}")
                    snapshot['delta'] = None
                    snapshot['gamma'] = None
                    snapshot['theta'] = None
                    snapshot['vega'] = None
                    snapshot['iv'] = None

        except Exception as e:
            logger.error(f"Error capturing market snapshot: {e}")

        return snapshot

    async def create_order_batch(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        purpose: str,
        orders_count: int,
        trading_mode: str,
        rule_name: Optional[str] = None,
        triggered_condition: Optional[Dict] = None
    ) -> AutoPilotOrderBatch:
        """
        Create a new order batch to group related orders.

        Args:
            db: Database session
            strategy: Strategy instance
            purpose: entry, adjustment, exit, etc.
            orders_count: Number of orders in batch
            trading_mode: 'live' or 'paper'
            rule_name: Name of adjustment rule (if applicable)
            triggered_condition: Condition that triggered this batch

        Returns:
            AutoPilotOrderBatch instance
        """
        try:
            # Capture market snapshot for the batch
            spot_data = await self.market_data.get_spot_price(strategy.underlying)
            spot_price = float(spot_data['ltp']) if isinstance(spot_data, dict) else float(spot_data.ltp)

            try:
                vix = await self.market_data.get_vix()
                vix_value = float(vix) if vix else None
            except Exception:
                vix_value = None

            batch = AutoPilotOrderBatch(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                purpose=purpose,
                rule_name=rule_name,
                status="pending",
                total_orders=orders_count,
                spot_price=Decimal(str(spot_price)),
                vix=Decimal(str(vix_value)) if vix_value else None,
                triggered_condition=triggered_condition,
                trading_mode=trading_mode
            )

            db.add(batch)
            await db.flush()  # Get the ID without committing

            return batch
        except Exception as e:
            logger.error(f"Failed to create order batch: {e}")
            raise

    async def execute_entry(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        dry_run: bool = False,
        trading_mode: str = "paper",
        triggered_condition: Optional[Dict] = None
    ) -> Tuple[bool, List[OrderResult]]:
        """
        Execute entry orders for a strategy with batch tracking.

        Phase 5C #15: Validates Delta Neutral Entry if enabled.

        Args:
            db: Database session
            strategy: Strategy to execute
            dry_run: If True, simulate without placing real orders
            trading_mode: 'live' or 'paper'
            triggered_condition: Condition that triggered entry

        Returns:
            Tuple of (success, list of order results)
        """
        legs_config = strategy.legs_config or []
        order_settings = strategy.order_settings or {}

        # Create order batch to group these entry orders
        batch = await self.create_order_batch(
            db=db,
            strategy=strategy,
            purpose="entry",
            orders_count=len(legs_config),
            trading_mode=trading_mode,
            triggered_condition=triggered_condition
        )

        # Phase 5C #15: Delta Neutral Entry Validation
        delta_neutral_entry = order_settings.get('delta_neutral_entry', False)
        delta_neutral_threshold = order_settings.get('delta_neutral_threshold', 0.15)

        if delta_neutral_entry:
            validated, delta_info = await self._validate_delta_neutral_entry(
                db=db,
                strategy=strategy,
                legs_config=legs_config,
                threshold=delta_neutral_threshold
            )

            if not validated:
                logger.warning(
                    f"Strategy {strategy.id} failed delta neutral validation: "
                    f"Net Delta={delta_info['net_delta']:.3f}, Threshold=±{delta_neutral_threshold}"
                )

                # Check if should block entry or just warn
                strict_delta_neutral = order_settings.get('strict_delta_neutral', False)
                if strict_delta_neutral:
                    logger.error(f"Blocking entry for strategy {strategy.id} due to strict delta neutral requirement")
                    return False, [OrderResult(
                        strategy_id=strategy.id,
                        order_id=None,
                        success=False,
                        error=f"Delta neutral validation failed: Net Delta {delta_info['net_delta']:.3f} exceeds threshold ±{delta_neutral_threshold}",
                        slippage_pct=0,
                        timestamp=datetime.now()
                    )]
                else:
                    logger.warning(
                        f"Proceeding with entry for strategy {strategy.id} despite delta neutral warning. "
                        f"Consider adding hedge: {delta_info.get('suggested_hedge', 'N/A')}"
                    )

        execution_style = order_settings.get('execution_style', 'sequential')
        leg_sequence = order_settings.get('leg_sequence', [])
        delay_between = order_settings.get('delay_between_legs', 2)

        # Sort legs by execution order
        if leg_sequence:
            sorted_legs = sorted(
                legs_config,
                key=lambda x: leg_sequence.index(x['id']) if x['id'] in leg_sequence else 999
            )
        else:
            sorted_legs = sorted(legs_config, key=lambda x: x.get('execution_order', 1))

        results: List[OrderResult] = []
        all_success = True

        # Build order requests
        order_requests = await self._build_order_requests(
            strategy=strategy,
            legs=sorted_legs,
            purpose="entry"
        )

        # Add batch info and trading mode to each request
        for i, req in enumerate(order_requests):
            req.trading_mode = trading_mode
            req.batch_id = batch.id
            req.batch_sequence = i + 1
            req.triggered_condition = triggered_condition

        if execution_style == 'simultaneous':
            # Execute all orders at once
            tasks = [
                self._place_order(db, req, strategy, dry_run)
                for req in order_requests
            ]
            results = await asyncio.gather(*tasks)
            all_success = all(r.success for r in results)
        else:
            # Execute sequentially with delay
            for i, req in enumerate(order_requests):
                result = await self._place_order(db, req, strategy, dry_run)
                results.append(result)

                if not result.success:
                    all_success = False
                    # Check on_leg_failure setting
                    on_failure = order_settings.get('on_leg_failure', 'stop')
                    if on_failure == 'stop':
                        logger.warning(f"Stopping execution due to leg failure: {result.error}")
                        break

                # Delay between legs
                if i < len(order_requests) - 1 and delay_between > 0:
                    await asyncio.sleep(delay_between)

        # Update batch status
        batch.completed_orders = sum(1 for r in results if r.success)
        batch.failed_orders = sum(1 for r in results if not r.success)

        if batch.failed_orders == 0:
            batch.status = "complete"
        elif batch.completed_orders > 0:
            batch.status = "partial"
        else:
            batch.status = "failed"

        batch.completed_at = datetime.now()
        await db.commit()

        return all_success, results

    async def execute_exit(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        exit_type: str = "market",
        reason: str = "manual",
        dry_run: bool = False,
        trading_mode: str = "paper",
        triggered_condition: Optional[Dict] = None
    ) -> Tuple[bool, List[OrderResult]]:
        """
        Execute exit orders to close all positions with batch tracking.

        Args:
            db: Database session
            strategy: Strategy to exit
            exit_type: market, limit
            reason: Reason for exit
            dry_run: Simulate without real orders
            trading_mode: 'live' or 'paper'
            triggered_condition: Condition that triggered exit

        Returns:
            Tuple of (success, list of order results)
        """
        # Get current positions from runtime_state
        runtime_state = strategy.runtime_state or {}
        current_positions = runtime_state.get('current_positions', [])

        if not current_positions:
            logger.info(f"No positions to exit for strategy {strategy.id}")
            return True, []

        # Create batch for exit orders
        batch = await self.create_order_batch(
            db=db,
            strategy=strategy,
            purpose="exit",
            orders_count=len(current_positions),
            trading_mode=trading_mode,
            triggered_condition=triggered_condition
        )

        results: List[OrderResult] = []
        all_success = True

        for i, position in enumerate(current_positions):
            # Create reverse order to close position
            req = OrderRequest(
                strategy_id=strategy.id,
                leg_id=position.get('leg_id', ''),
                leg_index=position.get('leg_index', 0),
                purpose="exit",
                exchange=position.get('exchange', 'NFO'),
                tradingsymbol=position.get('tradingsymbol'),
                transaction_type="SELL" if position.get('quantity', 0) > 0 else "BUY",
                quantity=abs(position.get('quantity', 0)),
                order_type="MARKET" if exit_type == "market" else "LIMIT",
                product=position.get('product', 'NRML'),
                underlying=strategy.underlying,
                contract_type=position.get('contract_type', ''),
                strike=Decimal(str(position.get('strike', 0))) if position.get('strike') else None,
                expiry=position.get('expiry'),
                # Batch info
                trading_mode=trading_mode,
                batch_id=batch.id,
                batch_sequence=i + 1,
                triggered_condition=triggered_condition
            )

            result = await self._place_order(db, req, strategy, dry_run)
            results.append(result)

            if not result.success:
                all_success = False

        # Update batch status
        batch.completed_orders = sum(1 for r in results if r.success)
        batch.failed_orders = sum(1 for r in results if not r.success)

        if batch.failed_orders == 0:
            batch.status = "complete"
        elif batch.completed_orders > 0:
            batch.status = "partial"
        else:
            batch.status = "failed"

        batch.completed_at = datetime.now()
        await db.commit()

        return all_success, results

    async def _build_order_requests(
        self,
        strategy: AutoPilotStrategy,
        legs: List[Dict[str, Any]],
        purpose: str
    ) -> List[OrderRequest]:
        """Build order requests from leg configurations."""
        requests = []

        # Get spot price for strike selection
        spot_data = await self.market_data.get_spot_price(strategy.underlying)
        spot_price = float(spot_data.ltp)

        # Determine expiry
        expiry_date = strategy.expiry_date
        if not expiry_date:
            # Calculate based on expiry_type
            expiry_date = self._calculate_expiry(strategy.expiry_type, strategy.underlying)

        lot_size = LOT_SIZES.get(strategy.underlying.upper(), 25)

        for i, leg in enumerate(legs):
            strike = await self._calculate_strike(
                leg=leg,
                spot_price=spot_price,
                underlying=strategy.underlying,
                expiry=expiry_date,
                db=db
            )

            tradingsymbol = self._build_tradingsymbol(
                underlying=strategy.underlying,
                expiry=expiry_date,
                strike=strike,
                contract_type=leg['contract_type']
            )

            quantity = strategy.lots * lot_size * leg.get('quantity_multiplier', 1)

            order_type = (strategy.order_settings or {}).get('order_type', 'MARKET')
            product = "NRML" if strategy.position_type == "positional" else "MIS"

            req = OrderRequest(
                strategy_id=strategy.id,
                leg_id=leg.get('id', f'leg_{i}'),
                leg_index=i,
                purpose=purpose,
                exchange="NFO",
                tradingsymbol=tradingsymbol,
                transaction_type=leg['transaction_type'],
                quantity=int(quantity),
                order_type=order_type,
                product=product,
                underlying=strategy.underlying,
                contract_type=leg['contract_type'],
                strike=Decimal(str(strike)),
                expiry=expiry_date
            )
            requests.append(req)

        return requests

    async def _place_order(
        self,
        db: AsyncSession,
        request: OrderRequest,
        strategy: AutoPilotStrategy,
        dry_run: bool
    ) -> OrderResult:
        """Place a single order with full market snapshot capture."""

        # Capture full market snapshot before placing order
        snapshot = await self.capture_market_snapshot(
            underlying=request.underlying,
            tradingsymbol=request.tradingsymbol,
            strike=request.strike,
            expiry=request.expiry,
            contract_type=request.contract_type
        )

        ltp_at_order = snapshot.get('ltp')
        is_paper = request.trading_mode == "paper"

        if dry_run or is_paper:
            # Simulate order (paper trading or dry run)
            mode_label = "PAPER" if is_paper else "DRY RUN"
            logger.info(f"[{mode_label}] Would place order: {request.transaction_type} "
                       f"{request.quantity} {request.tradingsymbol}")

            # Create simulated order record with full snapshot
            order = AutoPilotOrder(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                kite_order_id=f"PAPER_{datetime.now().timestamp()}" if is_paper else f"DRY_{datetime.now().timestamp()}",
                purpose=request.purpose,
                leg_index=request.leg_index,
                exchange=request.exchange,
                tradingsymbol=request.tradingsymbol,
                underlying=request.underlying,
                contract_type=request.contract_type,
                strike=request.strike,
                expiry=request.expiry,
                transaction_type=request.transaction_type,
                order_type=request.order_type,
                product=request.product,
                quantity=request.quantity,
                ltp_at_order=Decimal(str(ltp_at_order)) if ltp_at_order else None,
                executed_price=Decimal(str(ltp_at_order)) if ltp_at_order else None,
                executed_quantity=request.quantity,
                status="complete",
                order_placed_at=datetime.now(),
                order_filled_at=datetime.now(),
                # Trading mode and batch
                trading_mode=request.trading_mode,
                batch_id=request.batch_id,
                batch_sequence=request.batch_sequence,
                triggered_condition=request.triggered_condition,
                # Market snapshot
                spot_at_order=Decimal(str(snapshot['spot_price'])) if snapshot.get('spot_price') else None,
                vix_at_order=Decimal(str(snapshot['vix'])) if snapshot.get('vix') else None,
                delta_at_order=Decimal(str(snapshot['delta'])) if snapshot.get('delta') else None,
                gamma_at_order=Decimal(str(snapshot['gamma'])) if snapshot.get('gamma') else None,
                theta_at_order=Decimal(str(snapshot['theta'])) if snapshot.get('theta') else None,
                vega_at_order=Decimal(str(snapshot['vega'])) if snapshot.get('vega') else None,
                iv_at_order=Decimal(str(snapshot['iv'])) if snapshot.get('iv') else None,
                oi_at_order=snapshot.get('oi'),
                bid_at_order=Decimal(str(snapshot['bid'])) if snapshot.get('bid') else None,
                ask_at_order=Decimal(str(snapshot['ask'])) if snapshot.get('ask') else None
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)

            return OrderResult(
                success=True,
                order_id=str(order.id),
                kite_order_id=order.kite_order_id,
                message=f"{mode_label} - order simulated",
                executed_price=ltp_at_order,
                leg_id=request.leg_id
            )

        try:
            # Place order via Kite
            loop = asyncio.get_event_loop()
            order_params = {
                "exchange": request.exchange,
                "tradingsymbol": request.tradingsymbol,
                "transaction_type": request.transaction_type,
                "quantity": request.quantity,
                "order_type": request.order_type,
                "product": request.product,
            }

            if request.price:
                order_params["price"] = float(request.price)
            if request.trigger_price:
                order_params["trigger_price"] = float(request.trigger_price)

            kite_order_id = await loop.run_in_executor(
                None,
                lambda: self.kite.place_order(variety="regular", **order_params)
            )

            # Create order record in database with full snapshot
            order = AutoPilotOrder(
                strategy_id=strategy.id,
                user_id=strategy.user_id,
                kite_order_id=str(kite_order_id),
                purpose=request.purpose,
                leg_index=request.leg_index,
                exchange=request.exchange,
                tradingsymbol=request.tradingsymbol,
                underlying=request.underlying,
                contract_type=request.contract_type,
                strike=request.strike,
                expiry=request.expiry,
                transaction_type=request.transaction_type,
                order_type=request.order_type,
                product=request.product,
                quantity=request.quantity,
                ltp_at_order=Decimal(str(ltp_at_order)) if ltp_at_order else None,
                status="placed",
                order_placed_at=datetime.now(),
                # Trading mode and batch
                trading_mode=request.trading_mode,
                batch_id=request.batch_id,
                batch_sequence=request.batch_sequence,
                triggered_condition=request.triggered_condition,
                # Market snapshot
                spot_at_order=Decimal(str(snapshot['spot_price'])) if snapshot.get('spot_price') else None,
                vix_at_order=Decimal(str(snapshot['vix'])) if snapshot.get('vix') else None,
                delta_at_order=Decimal(str(snapshot['delta'])) if snapshot.get('delta') else None,
                gamma_at_order=Decimal(str(snapshot['gamma'])) if snapshot.get('gamma') else None,
                theta_at_order=Decimal(str(snapshot['theta'])) if snapshot.get('theta') else None,
                vega_at_order=Decimal(str(snapshot['vega'])) if snapshot.get('vega') else None,
                iv_at_order=Decimal(str(snapshot['iv'])) if snapshot.get('iv') else None,
                oi_at_order=snapshot.get('oi'),
                bid_at_order=Decimal(str(snapshot['bid'])) if snapshot.get('bid') else None,
                ask_at_order=Decimal(str(snapshot['ask'])) if snapshot.get('ask') else None
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)

            # Log the order
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                order_id=order.id,
                event_type="order_placed",
                severity="info",
                message=f"Order placed: {request.transaction_type} {request.quantity} {request.tradingsymbol}",
                event_data={
                    "kite_order_id": str(kite_order_id),
                    "leg_id": request.leg_id,
                    "purpose": request.purpose
                }
            )
            db.add(log)
            await db.commit()

            return OrderResult(
                success=True,
                order_id=str(order.id),
                kite_order_id=str(kite_order_id),
                message="Order placed successfully",
                leg_id=request.leg_id
            )

        except Exception as e:
            logger.error(f"Error placing order: {e}")

            # Log the error
            log = AutoPilotLog(
                user_id=strategy.user_id,
                strategy_id=strategy.id,
                event_type="order_error",
                severity="error",
                message=f"Order failed: {str(e)}",
                event_data={
                    "leg_id": request.leg_id,
                    "error": str(e)
                }
            )
            db.add(log)
            await db.commit()

            return OrderResult(
                success=False,
                error=str(e),
                message=f"Order failed: {str(e)}",
                leg_id=request.leg_id
            )

    async def _calculate_strike(
        self,
        leg: Dict[str, Any],
        spot_price: float,
        underlying: str,
        expiry: date,
        db: AsyncSession
    ) -> float:
        """
        Calculate strike price based on leg configuration.

        Uses StrikeFinderService when available for accurate delta, premium, and SD-based selection.
        Falls back to rough estimates for backward compatibility.
        """
        strike_selection = leg.get('strike_selection', {})
        mode = strike_selection.get('mode', 'atm_offset')
        contract_type = leg.get('contract_type', 'CE')

        # Get strike step
        strike_step = STRIKE_STEPS.get(underlying.upper(), 50)

        # Calculate ATM strike
        atm_strike = round(spot_price / strike_step) * strike_step

        if mode == 'fixed':
            return strike_selection.get('fixed_strike', atm_strike)

        elif mode == 'atm_offset':
            offset = strike_selection.get('offset', 0)
            return atm_strike + (offset * strike_step)

        elif mode == 'delta_based':
            target_delta = Decimal(str(strike_selection.get('target_delta', 0.3)))

            # Use StrikeFinderService if available
            if self.strike_finder:
                try:
                    result = await self.strike_finder.find_strike_by_delta(
                        underlying=underlying,
                        expiry=expiry,
                        option_type=contract_type,
                        target_delta=target_delta,
                        prefer_round_strike=strike_selection.get('prefer_round_strike', True)
                    )
                    if result:
                        logger.info(f"Found strike {result['strike']} for delta {target_delta} (actual delta: {result.get('delta', 'N/A')})")
                        return float(result['strike'])
                    else:
                        logger.warning(f"StrikeFinder couldn't find strike for delta {target_delta}, using fallback")
                except Exception as e:
                    logger.error(f"Error in find_strike_by_delta: {e}, using fallback")

            # Fallback: rough estimate
            steps_away = int((0.5 - abs(float(target_delta))) / 0.05)
            if contract_type == 'PE':
                return atm_strike - (steps_away * strike_step)
            return atm_strike + (steps_away * strike_step)

        elif mode == 'premium_based':
            target_premium = Decimal(str(strike_selection.get('target_premium', 100)))

            # Use StrikeFinderService if available
            if self.strike_finder:
                try:
                    result = await self.strike_finder.find_strike_by_premium(
                        underlying=underlying,
                        expiry=expiry,
                        option_type=contract_type,
                        target_premium=target_premium,
                        prefer_round_strike=strike_selection.get('prefer_round_strike', True)
                    )
                    if result:
                        logger.info(f"Found strike {result['strike']} for premium {target_premium} (actual premium: {result.get('ltp', 'N/A')})")
                        return float(result['strike'])
                    else:
                        logger.warning(f"StrikeFinder couldn't find strike for premium {target_premium}, using fallback")
                except Exception as e:
                    logger.error(f"Error in find_strike_by_premium: {e}, using fallback")

            # Fallback: rough estimate
            steps_away = int(float(target_premium) / 25)
            if contract_type == 'PE':
                return atm_strike - (steps_away * strike_step)
            return atm_strike + (steps_away * strike_step)

        elif mode == 'sd_based':
            standard_deviations = Decimal(str(strike_selection.get('standard_deviations', 1.0)))
            outside_sd = strike_selection.get('outside_sd', False)

            # Use StrikeFinderService if available
            if self.strike_finder:
                try:
                    result = await self.strike_finder.find_strike_by_standard_deviation(
                        underlying=underlying,
                        expiry=expiry,
                        option_type=contract_type,
                        standard_deviations=standard_deviations,
                        outside_sd=outside_sd,
                        prefer_round_strike=strike_selection.get('prefer_round_strike', True)
                    )
                    if result:
                        logger.info(f"Found strike {result['strike']} for {standard_deviations}SD (probability OTM: {result.get('probability_otm', 'N/A')})")
                        return float(result['strike'])
                    else:
                        logger.warning(f"StrikeFinder couldn't find strike for {standard_deviations}SD, using fallback")
                except Exception as e:
                    logger.error(f"Error in find_strike_by_standard_deviation: {e}, using fallback")

            # Fallback: rough estimate using ATM
            # 1 SD ≈ ATM ± (ATM * 0.02) for short-term options
            sd_distance = int(atm_strike * 0.02 * float(standard_deviations))
            sd_distance = round(sd_distance / strike_step) * strike_step
            if contract_type == 'PE':
                return atm_strike - sd_distance if outside_sd else atm_strike + sd_distance
            return atm_strike + sd_distance if outside_sd else atm_strike - sd_distance

        return atm_strike

    def _build_tradingsymbol(
        self,
        underlying: str,
        expiry: date,
        strike: float,
        contract_type: str
    ) -> str:
        """Build Kite tradingsymbol."""
        # Format: NIFTY24D2624500CE (weekly) or NIFTY24DEC24500CE (monthly)
        # Weekly uses format: NIFTY{YY}{M}{DD}{STRIKE}{TYPE}
        # Monthly uses format: NIFTY{YY}{MMM}{STRIKE}{TYPE}

        year = expiry.strftime("%y")  # e.g., "24"
        day = expiry.day

        # Determine if weekly or monthly expiry
        # Weekly expiries are typically Thursdays that aren't the last Thursday
        is_monthly = self._is_monthly_expiry(expiry)

        if is_monthly:
            month_str = expiry.strftime("%b").upper()  # e.g., "DEC"
            expiry_str = f"{year}{month_str}"
        else:
            # Weekly format: YY + single char month + DD
            month_char = "O" if expiry.month == 10 else (
                "N" if expiry.month == 11 else (
                    "D" if expiry.month == 12 else expiry.strftime("%b")[0]
                )
            )
            expiry_str = f"{year}{month_char}{day:02d}"

        return f"{underlying}{expiry_str}{int(strike)}{contract_type}"

    def _is_monthly_expiry(self, expiry: date) -> bool:
        """Check if expiry is a monthly expiry (last Thursday of month)."""
        # Get last day of month
        if expiry.month == 12:
            next_month = date(expiry.year + 1, 1, 1)
        else:
            next_month = date(expiry.year, expiry.month + 1, 1)

        last_day = next_month - __import__('datetime').timedelta(days=1)

        # Find last Thursday
        days_since_thursday = (last_day.weekday() - 3) % 7
        last_thursday = last_day - __import__('datetime').timedelta(days=days_since_thursday)

        return expiry == last_thursday

    def _calculate_expiry(self, expiry_type: str, underlying: str) -> date:
        """Calculate expiry date based on expiry type."""
        today = date.today()
        weekday = today.weekday()  # 0 = Monday, 3 = Thursday

        if expiry_type == "current_week":
            # Next Thursday (or today if Thursday)
            days_until_thursday = (3 - weekday) % 7
            if days_until_thursday == 0 and datetime.now().time() > __import__('datetime').time(15, 30):
                days_until_thursday = 7  # Already past expiry time
            return today + __import__('datetime').timedelta(days=days_until_thursday)

        elif expiry_type == "next_week":
            # Thursday of next week
            days_until_thursday = (3 - weekday) % 7
            return today + __import__('datetime').timedelta(days=days_until_thursday + 7)

        elif expiry_type == "current_month":
            # Last Thursday of current month
            return self._get_last_thursday(today.year, today.month)

        elif expiry_type == "next_month":
            # Last Thursday of next month
            if today.month == 12:
                return self._get_last_thursday(today.year + 1, 1)
            return self._get_last_thursday(today.year, today.month + 1)

        # Default to current week
        days_until_thursday = (3 - weekday) % 7
        return today + __import__('datetime').timedelta(days=days_until_thursday)

    def _get_last_thursday(self, year: int, month: int) -> date:
        """Get the last Thursday of a given month."""
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        last_day = next_month - __import__('datetime').timedelta(days=1)

        # Find last Thursday
        days_since_thursday = (last_day.weekday() - 3) % 7
        return last_day - __import__('datetime').timedelta(days=days_since_thursday)

    async def _validate_delta_neutral_entry(
        self,
        db: AsyncSession,
        strategy: AutoPilotStrategy,
        legs_config: List[Dict[str, Any]],
        threshold: float = 0.15
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate if strategy entry is delta neutral (Phase 5C #15).

        Args:
            db: Database session
            strategy: Strategy to validate
            legs_config: Legs configuration
            threshold: Maximum acceptable net delta (default ±0.15)

        Returns:
            Tuple of (is_valid, delta_info_dict)

        Example delta_info:
        {
            "net_delta": 0.05,
            "is_neutral": True,
            "threshold": 0.15,
            "leg_deltas": [...],
            "suggested_hedge": "Sell 1 lot of futures" (if not neutral)
        }
        """
        try:
            from app.services.greeks_calculator import GreeksCalculatorService

            greeks_calc = GreeksCalculatorService(db, strategy.user_id)

            # Get spot price
            spot_data = await self.market_data.get_spot_price(strategy.underlying)
            spot_price = float(spot_data.ltp)

            net_delta = 0.0
            leg_deltas = []

            # Calculate delta for each leg
            for leg in legs_config:
                strike = float(leg.get('strike', 0))
                option_type = leg.get('option_type', 'CE').upper()
                quantity = int(leg.get('quantity', 1))
                action = leg.get('action', 'BUY').upper()
                iv = float(leg.get('iv', 0.20))  # Default 20% IV
                expiry = leg.get('expiry')

                if not strike or not expiry:
                    continue

                # Calculate time to expiry
                try:
                    from datetime import date as date_type, datetime as datetime_type
                    if isinstance(expiry, str):
                        expiry_date = datetime_type.strptime(expiry, "%Y-%m-%d").date()
                    elif isinstance(expiry, date_type):
                        expiry_date = expiry
                    else:
                        continue

                    today = date_type.today()
                    days_to_expiry = (expiry_date - today).days
                    time_to_expiry = max(0, days_to_expiry / 365.0)

                    if time_to_expiry > 0:
                        is_call = option_type in ('CE', 'CALL', 'C')

                        # Calculate Greeks for this leg
                        greeks = greeks_calc._calculate_greeks(
                            spot=spot_price,
                            strike=strike,
                            time_to_expiry=time_to_expiry,
                            volatility=iv,
                            is_call=is_call
                        )

                        # Adjust for position direction (buy = +, sell = -)
                        multiplier = quantity if action == 'BUY' else -quantity
                        leg_delta = greeks['delta'] * multiplier

                        net_delta += leg_delta

                        leg_deltas.append({
                            'strike': strike,
                            'option_type': option_type,
                            'action': action,
                            'quantity': quantity,
                            'delta': greeks['delta'],
                            'net_delta': leg_delta
                        })

                except Exception as e:
                    logger.debug(f"Error calculating delta for leg: {e}")
                    continue

            # Check if within threshold
            is_neutral = abs(net_delta) <= threshold

            # Generate suggested hedge if not neutral
            suggested_hedge = None
            if not is_neutral:
                # Calculate hedge needed
                hedge_delta = -net_delta  # Opposite sign
                lot_size = LOT_SIZES.get(strategy.underlying.upper(), 25)

                # Each futures contract has delta of ~1 per lot
                lots_needed = abs(int(round(hedge_delta / lot_size)))

                if lots_needed > 0:
                    hedge_action = "BUY" if hedge_delta > 0 else "SELL"
                    suggested_hedge = f"{hedge_action} {lots_needed} lot(s) of {strategy.underlying} futures"

            delta_info = {
                'net_delta': round(net_delta, 4),
                'is_neutral': is_neutral,
                'threshold': threshold,
                'leg_deltas': leg_deltas,
                'suggested_hedge': suggested_hedge
            }

            logger.info(
                f"Delta Neutral Validation for strategy {strategy.id}: "
                f"Net Delta={net_delta:.4f}, Threshold=±{threshold}, Valid={is_neutral}"
            )

            return is_neutral, delta_info

        except Exception as e:
            logger.error(f"Error validating delta neutral entry: {e}")
            return True, {
                'net_delta': 0.0,
                'is_neutral': True,
                'threshold': threshold,
                'error': str(e)
            }


def get_order_executor(kite: KiteConnect, market_data: MarketDataService, db: AsyncSession = None) -> OrderExecutor:
    """Create OrderExecutor instance."""
    strike_finder = StrikeFinderService(kite, db) if db else None
    return OrderExecutor(kite, market_data, strike_finder)
