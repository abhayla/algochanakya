# Entity-Relationship Diagram & Data Model

**Last Updated:** 2026-02-16

This document provides a comprehensive view of AlgoChanakya's database schema, including all 38 tables with detailed data dictionaries.

---

## Table of Contents

1. [ERD Diagram](#erd-diagram-all-38-tables)
2. [Quick Summary](#quick-summary-38-tables)
3. [Core Domain (5 tables)](#core-domain-5-tables)
4. [Trading Domain (4 tables)](#trading-domain-4-tables)
5. [AutoPilot Domain (18 tables)](#autopilot-domain-18-tables)
6. [AI/ML Domain (9 tables)](#aiml-domain-9-tables)
7. [Cache Domain (2 tables)](#cache-domain-2-tables)
8. [PostgreSQL Enums (19 types)](#postgresql-enums-19-types)
9. [Foreign Key Relationships](#foreign-key-relationships)
10. [Indexes & Constraints](#indexes--constraints)
11. [ASCII ERD Overview](#ascii-erd-overview)

---

## ERD Diagram (All 38 Tables)

```mermaid
erDiagram
    %% ========================================
    %% CORE DOMAIN (5 tables)
    %% ========================================
    users {
        UUID id PK
        String email UK "nullable, broker-only users allowed"
        DateTime created_at
        DateTime last_login
    }

    broker_connections {
        UUID id PK
        UUID user_id FK
        String broker "zerodha, angelone, upstox"
        String broker_user_id "Broker client ID"
        Text access_token
        Text refresh_token "nullable"
        DateTime token_expiry "nullable"
        Boolean is_active
        DateTime created_at
        DateTime updated_at
    }

    user_preferences {
        BigInt id PK
        UUID user_id FK,UK
        String market_data_source "smartapi, kite, upstox, dhan, fyers, paytm"
        JSONB ui_settings
        DateTime created_at
        DateTime updated_at
    }

    smartapi_credentials {
        BigInt id PK
        UUID user_id FK,UK
        Text api_key_encrypted
        Text client_code_encrypted
        Text mpin_encrypted
        Text totp_secret_encrypted
        Boolean is_active
        DateTime created_at
        DateTime updated_at
    }

    instruments {
        BigInt id PK
        BigInt instrument_token UK
        String exchange "NFO, NSE, BSE"
        String tradingsymbol
        String name
        Date expiry "nullable"
        Numeric strike "nullable"
        String instrument_type
        Integer lot_size
        DateTime last_updated
    }

    %% ========================================
    %% TRADING DOMAIN (4 tables)
    %% ========================================
    strategies {
        BigInt id PK
        UUID user_id FK
        String name
        String strategy_type
        String underlying "NIFTY, BANKNIFTY, etc."
        JSONB legs
        Numeric target_profit "nullable"
        Numeric stop_loss "nullable"
        String status
        DateTime created_at
        DateTime updated_at
    }

    strategy_legs {
        BigInt id PK
        BigInt strategy_id FK
        Integer leg_number
        String option_type "CE, PE"
        String action "BUY, SELL"
        Integer strike_offset
        Integer quantity
        Numeric premium "nullable"
    }

    strategy_templates {
        BigInt id PK
        String name UK
        String description
        String strategy_type
        JSONB legs_config
        String risk_level
        Boolean is_active
        DateTime created_at
        DateTime updated_at
    }

    broker_instrument_tokens {
        BigInt id PK
        String canonical_symbol
        String broker
        String broker_symbol "nullable"
        BigInt broker_token "nullable"
        String exchange
        Date expiry "nullable"
        Numeric strike "nullable"
        String instrument_type
        DateTime last_updated
    }

    %% ========================================
    %% AUTOPILOT DOMAIN (18 tables)
    %% ========================================
    autopilot_user_settings {
        BigInt id PK
        UUID user_id FK,UK
        Numeric daily_loss_limit
        Numeric per_strategy_loss_limit
        Numeric max_capital_deployed
        Integer max_active_strategies
        Integer no_trade_first_minutes
        Integer no_trade_last_minutes
        Boolean cooldown_after_loss
        Integer cooldown_minutes
        Numeric cooldown_threshold
        JSONB default_order_settings
        JSONB notification_prefs
        JSONB failure_handling
        Boolean paper_trading_mode
        Boolean show_advanced_features
        Boolean kill_switch_enabled
        DateTime kill_switch_triggered_at "nullable"
        Enum default_execution_mode "auto, semi_auto, manual"
        Integer confirmation_timeout_seconds
        String auto_exit_time "nullable, HH:MM format"
        Numeric account_capital "nullable"
        Numeric risk_per_trade_pct "nullable"
        Numeric delta_watch_threshold
        Numeric delta_warning_threshold
        Numeric delta_danger_threshold
        Boolean delta_alert_enabled
        Boolean suggestions_enabled
        Boolean prefer_round_strikes
        DateTime created_at
        DateTime updated_at
    }

    autopilot_strategies {
        BigInt id PK
        UUID user_id FK
        String name
        String description "nullable"
        Enum status "draft, waiting, active, paused, completed, error, etc."
        Enum underlying "NIFTY, BANKNIFTY, FINNIFTY, SENSEX"
        String expiry_type
        Date expiry_date "nullable"
        Integer lots
        Enum position_type "intraday, positional"
        JSONB legs_config
        JSONB entry_conditions
        JSONB adjustment_rules
        JSONB order_settings
        JSONB risk_settings
        JSONB schedule_config
        JSONB reentry_config "nullable"
        Enum execution_mode "auto, semi_auto, manual, nullable"
        JSONB trailing_stop_config "nullable"
        JSONB greeks_snapshot "nullable"
        JSONB staged_entry_config "nullable"
        JSONB position_legs_snapshot "nullable"
        Numeric net_delta "nullable"
        Numeric net_theta "nullable"
        Numeric net_gamma "nullable"
        Numeric net_vega "nullable"
        Numeric breakeven_lower "nullable"
        Numeric breakeven_upper "nullable"
        Integer dte "nullable, Days to expiry"
        Integer priority
        JSONB runtime_state "nullable"
        Enum trading_mode "live, paper, nullable"
        Enum activated_in_mode "live, paper, nullable"
        Boolean ai_deployed "nullable"
        Numeric ai_confidence_score "nullable"
        String ai_regime_type "nullable"
        String ai_lots_tier "nullable"
        Text ai_explanation "nullable"
        BigInt source_template_id FK "nullable"
        BigInt cloned_from_id FK "nullable, self-reference"
        Enum share_mode "private, link, public"
        String share_token UK "nullable"
        DateTime shared_at "nullable"
        Integer version
        DateTime created_at
        DateTime updated_at
        DateTime activated_at "nullable"
        DateTime completed_at "nullable"
    }

    autopilot_orders {
        BigInt id PK
        BigInt strategy_id FK
        UUID user_id FK
        String kite_order_id "nullable"
        String kite_exchange_order_id "nullable"
        Enum purpose "entry, adjustment, hedge, exit, roll_close, roll_open, kill_switch"
        String rule_name "nullable"
        Integer leg_index
        String exchange
        String tradingsymbol
        BigInt instrument_token "nullable"
        Enum underlying "NIFTY, BANKNIFTY, FINNIFTY, SENSEX"
        String contract_type "CE, PE"
        Numeric strike "nullable"
        Date expiry
        Enum transaction_type "BUY, SELL"
        Enum order_type "MARKET, LIMIT, SL, SL-M"
        String product
        Integer quantity
        Numeric order_price "nullable"
        Numeric trigger_price "nullable"
        Numeric ltp_at_order "nullable"
        Numeric executed_price "nullable"
        Integer executed_quantity
        Integer pending_quantity "nullable"
        Numeric slippage_amount "nullable"
        Numeric slippage_pct "nullable"
        Enum status "pending, placed, open, complete, cancelled, rejected, error"
        String rejection_reason "nullable"
        DateTime order_placed_at "nullable"
        DateTime order_filled_at "nullable"
        Integer execution_duration_ms "nullable"
        Integer retry_count
        BigInt parent_order_id FK "nullable, self-reference"
        JSONB raw_response "nullable"
        Enum trading_mode "live, paper, nullable"
        String ai_sizing_mode "nullable"
        Numeric ai_tier_multiplier "nullable"
        UUID batch_id FK "nullable"
        Integer batch_sequence "nullable"
        JSONB triggered_condition "nullable"
        Numeric spot_at_order "nullable"
        Numeric vix_at_order "nullable"
        Numeric delta_at_order "nullable"
        Numeric gamma_at_order "nullable"
        Numeric theta_at_order "nullable"
        Numeric vega_at_order "nullable"
        Numeric iv_at_order "nullable"
        BigInt oi_at_order "nullable"
        Numeric bid_at_order "nullable"
        Numeric ask_at_order "nullable"
        DateTime created_at
        DateTime updated_at
    }

    autopilot_order_batches {
        UUID id PK
        BigInt strategy_id FK
        UUID user_id FK
        Enum purpose "entry, adjustment, hedge, exit, roll_close, roll_open, kill_switch"
        String rule_name "nullable"
        BigInt adjustment_log_id "nullable"
        String status
        Integer total_orders
        Integer completed_orders
        Integer failed_orders
        Numeric spot_price "nullable"
        Numeric vix "nullable"
        Numeric net_delta "nullable"
        Numeric net_gamma "nullable"
        Numeric net_theta "nullable"
        Numeric net_vega "nullable"
        JSONB triggered_condition "nullable"
        JSONB trigger_value "nullable"
        Enum trading_mode "live, paper"
        DateTime created_at
        DateTime completed_at "nullable"
        Numeric total_slippage "nullable"
        Integer execution_duration_ms "nullable"
    }

    autopilot_logs {
        BigInt id PK
        UUID user_id FK
        BigInt strategy_id FK "nullable"
        BigInt order_id FK "nullable"
        Enum event_type "50+ event types, see model"
        Enum severity "debug, info, warning, error, critical"
        String rule_name "nullable"
        String condition_id "nullable"
        JSONB event_data
        String message
        DateTime created_at
    }

    autopilot_templates {
        BigInt id PK
        UUID user_id FK "nullable"
        String name
        String description "nullable"
        Boolean is_system
        Boolean is_public
        JSONB strategy_config
        String category "nullable"
        Array tags
        String risk_level "nullable"
        Integer usage_count
        Numeric avg_rating "nullable"
        Integer rating_count
        String author_name "nullable"
        String underlying "nullable"
        String position_type "nullable"
        Numeric expected_return_pct "nullable"
        Numeric max_risk_pct "nullable"
        String market_outlook "nullable"
        String iv_environment "nullable"
        String thumbnail_url "nullable"
        JSONB educational_content "nullable"
        DateTime created_at
        DateTime updated_at
    }

    autopilot_template_ratings {
        BigInt id PK
        BigInt template_id FK
        UUID user_id FK
        Integer rating "1-5"
        Text review "nullable"
        DateTime created_at
        DateTime updated_at
    }

    autopilot_condition_eval {
        BigInt id PK
        BigInt strategy_id FK
        String condition_type
        Integer condition_index
        String rule_name "nullable"
        String variable
        String operator
        JSONB target_value
        JSONB current_value
        Boolean is_satisfied
        Numeric progress_pct "nullable"
        String distance_to_trigger "nullable"
        DateTime evaluated_at
    }

    autopilot_daily_summary {
        BigInt id PK
        UUID user_id FK
        Date summary_date UK "with user_id"
        Integer strategies_run
        Integer strategies_completed
        Integer strategies_errored
        Integer orders_placed
        Integer orders_filled
        Integer orders_rejected
        Numeric total_realized_pnl
        Numeric total_brokerage
        Numeric total_slippage
        Numeric best_strategy_pnl "nullable"
        String best_strategy_name "nullable"
        Numeric worst_strategy_pnl "nullable"
        String worst_strategy_name "nullable"
        Integer avg_execution_time_ms "nullable"
        Integer total_adjustments
        Boolean kill_switch_used
        Numeric max_drawdown "nullable"
        Numeric peak_margin_used "nullable"
        Boolean daily_loss_limit_hit
        DateTime created_at
        DateTime updated_at
    }

    autopilot_adjustment_logs {
        BigInt id PK
        BigInt strategy_id FK
        UUID user_id FK
        String rule_id
        String rule_name
        Enum trigger_type "pnl_based, delta_based, time_based, premium_based, vix_based, spot_based"
        String trigger_condition
        JSONB trigger_value
        JSONB actual_value
        Enum action_type "add_hedge, close_leg, roll_strike, roll_expiry, exit_all, scale_down, scale_up"
        JSONB action_params
        Enum execution_mode "auto, semi_auto, manual"
        Boolean executed
        JSONB execution_result "nullable"
        String error_message "nullable"
        Array order_ids "nullable"
        BigInt confirmation_id FK "nullable"
        Boolean confirmed_by_user "nullable"
        DateTime triggered_at
        DateTime executed_at "nullable"
        DateTime created_at
    }

    autopilot_pending_confirmations {
        BigInt id PK
        UUID user_id FK
        BigInt strategy_id FK
        String action_type
        String action_description
        JSONB action_data
        String rule_id "nullable"
        String rule_name "nullable"
        Enum status "pending, confirmed, rejected, expired, cancelled"
        Integer timeout_seconds
        DateTime expires_at
        DateTime responded_at "nullable"
        String response_source "nullable"
        JSONB execution_result "nullable"
        Array order_ids "nullable"
        DateTime created_at
        DateTime updated_at
    }

    autopilot_trade_journal {
        BigInt id PK
        UUID user_id FK
        BigInt strategy_id FK "nullable"
        String strategy_name
        String underlying
        String position_type
        DateTime entry_time
        DateTime exit_time "nullable"
        Integer holding_duration_minutes "nullable"
        JSONB legs
        Integer lots
        Integer total_quantity
        Numeric entry_premium "nullable"
        Numeric exit_premium "nullable"
        Numeric gross_pnl "nullable"
        Numeric brokerage "nullable"
        Numeric taxes "nullable"
        Numeric other_charges "nullable"
        Numeric net_pnl "nullable"
        Numeric pnl_percentage "nullable"
        Numeric max_profit_reached "nullable"
        Numeric max_loss_reached "nullable"
        Numeric max_drawdown "nullable"
        Enum exit_reason "target_hit, stop_loss, trailing_stop, time_exit, manual_exit, etc."
        JSONB market_conditions "nullable"
        Text notes "nullable"
        Array tags
        JSONB screenshots "nullable"
        Array entry_order_ids "nullable"
        Array exit_order_ids "nullable"
        Boolean is_open
        DateTime created_at
        DateTime updated_at
    }

    autopilot_analytics_cache {
        BigInt id PK
        UUID user_id FK
        String cache_key UK "with user_id"
        Date start_date
        Date end_date
        JSONB metrics
        Boolean is_valid
        DateTime expires_at
        DateTime created_at
        DateTime updated_at
    }

    autopilot_reports {
        BigInt id PK
        UUID user_id FK
        Enum report_type "daily, weekly, monthly, custom, strategy, tax"
        String name
        String description "nullable"
        Date start_date
        Date end_date
        BigInt strategy_id FK "nullable"
        JSONB report_data
        Enum format "pdf, excel, csv, nullable"
        String file_path "nullable"
        BigInt file_size_bytes "nullable"
        Boolean is_ready
        String error_message "nullable"
        DateTime created_at
        DateTime generated_at "nullable"
    }

    autopilot_backtests {
        BigInt id PK
        UUID user_id FK
        String name
        String description "nullable"
        JSONB strategy_config
        Date start_date
        Date end_date
        Numeric initial_capital
        Numeric slippage_pct
        Numeric charges_per_lot
        String data_interval
        Enum status "pending, running, completed, failed, cancelled"
        Integer progress_pct
        String error_message "nullable"
        JSONB results "nullable"
        Integer total_trades "nullable"
        Integer winning_trades "nullable"
        Integer losing_trades "nullable"
        Numeric win_rate "nullable"
        Numeric gross_pnl "nullable"
        Numeric net_pnl "nullable"
        Numeric max_drawdown "nullable"
        Numeric max_drawdown_pct "nullable"
        Numeric sharpe_ratio "nullable"
        Numeric profit_factor "nullable"
        JSONB equity_curve "nullable"
        JSONB trades "nullable"
        DateTime created_at
        DateTime started_at "nullable"
        DateTime completed_at "nullable"
    }

    autopilot_position_legs {
        BigInt id PK
        BigInt strategy_id FK
        String leg_id
        String contract_type "CE, PE"
        String action "BUY, SELL"
        Numeric strike
        Date expiry
        Integer lots
        String tradingsymbol "nullable"
        BigInt instrument_token "nullable"
        String status
        Numeric entry_price "nullable"
        DateTime entry_time "nullable"
        JSONB entry_order_ids
        Numeric exit_price "nullable"
        DateTime exit_time "nullable"
        JSONB exit_order_ids
        String exit_reason "nullable"
        Numeric delta "nullable"
        Numeric gamma "nullable"
        Numeric theta "nullable"
        Numeric vega "nullable"
        Numeric iv "nullable"
        Numeric unrealized_pnl
        Numeric realized_pnl
        BigInt rolled_from_leg_id FK "nullable, self-reference"
        BigInt rolled_to_leg_id "nullable"
        DateTime created_at
        DateTime updated_at
    }

    autopilot_adjustment_suggestions {
        BigInt id PK
        BigInt strategy_id FK
        String leg_id "nullable"
        Text trigger_reason
        String suggestion_type
        Text description
        JSONB details "nullable"
        String urgency
        Integer confidence
        String category
        Boolean one_click_action
        JSONB action_params "nullable"
        String status
        DateTime created_at
        DateTime expires_at "nullable"
        DateTime responded_at "nullable"
    }

    autopilot_option_chain_cache {
        BigInt id PK
        String underlying UK "with expiry, strike, option_type"
        Date expiry UK
        Numeric strike UK
        String option_type UK "CE, PE"
        String tradingsymbol
        BigInt instrument_token
        Numeric ltp "nullable"
        Numeric bid "nullable"
        Numeric ask "nullable"
        BigInt volume "nullable"
        BigInt oi "nullable"
        BigInt oi_change "nullable"
        Numeric iv "nullable"
        Numeric delta "nullable"
        Numeric gamma "nullable"
        Numeric theta "nullable"
        Numeric vega "nullable"
        DateTime updated_at
    }

    %% ========================================
    %% AI/ML DOMAIN (9 tables)
    %% ========================================
    ai_user_config {
        BigInt id PK
        UUID user_id FK,UK
        Boolean ai_enabled
        String autonomy_mode "paper, live"
        Boolean auto_deploy_enabled
        String deploy_time "nullable, HH:MM"
        Array deploy_days
        Boolean skip_event_days
        Boolean skip_weekly_expiry
        JSONB allowed_strategies
        String sizing_mode "fixed, tiered, kelly"
        Integer base_lots
        JSONB confidence_tiers
        Integer max_lots_per_strategy
        Integer max_lots_per_day
        Integer max_strategies_per_day
        Numeric min_confidence_to_trade
        Numeric max_vix_to_trade
        Integer min_dte_to_enter
        Numeric weekly_loss_limit
        Numeric max_stress_risk_score
        Numeric max_portfolio_delta
        Numeric max_portfolio_gamma
        Boolean enable_drawdown_sizing
        JSONB drawdown_thresholds
        Boolean enable_volatility_sizing
        Integer volatility_lookback_days
        JSONB volatility_thresholds
        Numeric max_drawdown_to_trade
        Numeric high_water_mark "nullable"
        Numeric current_drawdown_pct
        Boolean enable_drift_detection
        Integer drift_lookback_periods
        Numeric drift_threshold
        Numeric drift_confidence_penalty
        Numeric min_regime_stability_score
        Numeric current_regime_stability
        DateTime last_drift_check_at "nullable"
        Boolean enable_ml_blending
        Numeric blending_alpha_start
        Numeric blending_alpha_min
        Integer blending_trades_threshold
        Integer total_trades_completed
        String retraining_cadence "daily, weekly, volume_based"
        Integer retraining_volume_threshold
        Integer high_volume_trades_per_week
        DateTime last_user_model_retrain_at "nullable"
        Numeric min_model_stability_threshold
        Boolean enable_confidence_weighting
        Integer trades_since_last_retrain
        Array preferred_underlyings
        Date paper_start_date "nullable"
        Integer paper_trades_completed
        Numeric paper_win_rate
        Numeric paper_total_pnl
        Boolean paper_graduation_approved
        Text claude_api_key_encrypted "nullable"
        Boolean enable_ai_explanations
        DateTime created_at
        DateTime updated_at
    }

    ai_model_registry {
        BigInt id PK
        String version
        String model_type "xgboost, lightgbm"
        String scope "global, user"
        UUID user_id FK "nullable, NULL for global"
        Text file_path
        Text description "nullable"
        Numeric accuracy "nullable, 0-1"
        Numeric precision "nullable, 0-1"
        Numeric recall "nullable, 0-1"
        Numeric f1_score "nullable, 0-1"
        Numeric roc_auc "nullable, 0-1"
        Boolean is_active
        DateTime activated_at "nullable"
        DateTime trained_at
        DateTime created_at
    }

    ai_learning_reports {
        BigInt id PK
        UUID user_id FK
        Date report_date UK "with user_id"
        Integer total_trades
        Integer winning_trades
        Integer losing_trades
        Numeric win_rate
        Numeric total_pnl
        Numeric avg_pnl_per_trade
        Numeric max_win "nullable"
        Numeric max_loss "nullable"
        Numeric avg_overall_score
        Numeric avg_pnl_score
        Numeric avg_risk_score
        Numeric avg_entry_score
        Numeric avg_adjustment_score
        Numeric avg_exit_score
        Boolean model_retrained
        String new_model_version "nullable"
        Numeric model_accuracy "nullable, 0-1"
        JSONB insights
        JSONB regime_breakdown
        String dominant_regime "nullable"
        Numeric dominant_regime_pct "nullable"
        DateTime created_at
    }

    ai_paper_trades {
        UUID id PK
        UUID user_id FK
        String strategy_name
        String underlying
        DateTime entry_time
        String entry_regime
        Numeric entry_confidence
        String sizing_mode
        Integer lots
        JSONB legs
        DateTime exit_time "nullable"
        String exit_reason "nullable"
        Numeric entry_total_premium
        Numeric exit_total_premium "nullable"
        Numeric realized_pnl "nullable"
        String status "open, closed"
        DateTime created_at
        DateTime updated_at
    }

    ai_risk_state {
        BigInt id PK
        UUID user_id FK,UK
        Enum risk_state "GREEN, YELLOW, RED"
        Numeric current_score
        JSONB risk_factors
        String recommendation "nullable"
        Boolean ai_trading_blocked
        DateTime created_at
        DateTime updated_at
    }

    ai_strategy_cooldown {
        BigInt id PK
        UUID user_id FK
        String strategy_template_id
        DateTime cooldown_until
        String reason "nullable"
        JSONB metadata "nullable"
        DateTime created_at
    }

    ai_regime_history {
        BigInt id PK
        UUID user_id FK,UK "nullable, NULL for global"
        String underlying UK "with detected_at"
        DateTime detected_at UK
        String regime_type "TRENDING_BULLISH, TRENDING_BEARISH, etc."
        Numeric confidence
        JSONB features "nullable"
        DateTime created_at
    }

    ai_regime_performance {
        BigInt id PK
        UUID user_id FK
        String underlying
        String regime_type UK "with user_id, underlying"
        Integer total_trades
        Integer winning_trades
        Numeric win_rate
        Numeric total_pnl
        Numeric avg_pnl
        Numeric sharpe_ratio "nullable"
        Numeric max_drawdown "nullable"
        DateTime last_updated
        DateTime created_at
    }

    ai_decisions_log {
        BigInt id PK
        UUID user_id FK
        BigInt strategy_id FK "nullable"
        String decision_type
        DateTime decision_time
        String regime_type
        Numeric confidence_score
        String recommended_action
        JSONB input_features
        String model_version "nullable"
        Boolean user_followed
        String actual_outcome "nullable"
        JSONB outcome_metadata "nullable"
        Numeric quality_score "nullable"
        DateTime created_at
    }

    %% ========================================
    %% RELATIONSHIPS
    %% ========================================

    %% Core
    users ||--o{ broker_connections : "has connections"
    users ||--o| user_preferences : "has preferences"
    users ||--o| smartapi_credentials : "has smartapi creds"

    %% Trading
    users ||--o{ strategies : "creates strategies"
    strategies ||--o{ strategy_legs : "has legs"

    %% AutoPilot
    users ||--o| autopilot_user_settings : "has autopilot settings"
    users ||--o{ autopilot_strategies : "creates autopilot strategies"
    autopilot_strategies ||--o{ autopilot_orders : "places orders"
    autopilot_strategies ||--o{ autopilot_logs : "generates logs"
    autopilot_strategies ||--o{ autopilot_adjustment_logs : "has adjustments"
    autopilot_strategies ||--o{ autopilot_pending_confirmations : "requests confirmations"
    autopilot_strategies ||--o{ autopilot_position_legs : "tracks position legs"
    autopilot_strategies ||--o{ autopilot_adjustment_suggestions : "receives suggestions"
    autopilot_strategies }o--o| autopilot_strategies : "cloned from (self-reference)"
    autopilot_templates ||--o{ autopilot_strategies : "instantiates strategies"
    autopilot_templates ||--o{ autopilot_template_ratings : "rated by users"
    autopilot_order_batches ||--o{ autopilot_orders : "groups orders"
    autopilot_orders }o--o| autopilot_orders : "retries (self-reference)"
    autopilot_position_legs }o--o| autopilot_position_legs : "rolled from (self-reference)"
    autopilot_pending_confirmations ||--o{ autopilot_adjustment_logs : "confirms adjustments"

    %% AI/ML
    users ||--o| ai_user_config : "has AI config"
    users ||--o{ ai_model_registry : "has user models"
    users ||--o{ ai_learning_reports : "daily learning reports"
    users ||--o{ ai_paper_trades : "paper trades"
    users ||--o| ai_risk_state : "current risk state"
    users ||--o{ ai_strategy_cooldown : "cooldowns"
    users ||--o{ ai_regime_history : "regime detections"
    users ||--o{ ai_regime_performance : "regime performance"
    users ||--o{ ai_decisions_log : "AI decisions"
    autopilot_strategies ||--o{ ai_decisions_log : "AI-deployed strategies"
```

---

## Quick Summary (38 Tables)

| Domain | Tables | Purpose |
|--------|--------|---------|
| **Core** (5) | users, broker_connections, user_preferences, smartapi_credentials, instruments | User identity, broker authentication, preferences |
| **Trading** (4) | strategies, strategy_legs, strategy_templates, broker_instrument_tokens | Manual strategy building, instrument data |
| **AutoPilot** (18) | autopilot_user_settings, autopilot_strategies, autopilot_orders, autopilot_order_batches, autopilot_logs, autopilot_templates, autopilot_template_ratings, autopilot_condition_eval, autopilot_daily_summary, autopilot_adjustment_logs, autopilot_pending_confirmations, autopilot_trade_journal, autopilot_analytics_cache, autopilot_reports, autopilot_backtests, autopilot_position_legs, autopilot_adjustment_suggestions, autopilot_option_chain_cache | Automated trading execution |
| **AI/ML** (9) | ai_user_config, ai_model_registry, ai_learning_reports, ai_paper_trades, ai_risk_state, ai_strategy_cooldown, ai_regime_history, ai_regime_performance, ai_decisions_log | Market intelligence, autonomous trading |
| **Cache** (2) | autopilot_option_chain_cache, ai_market_snapshots (not shown in models, likely removed) | Cached option chain data |

**Total:** 38 tables (19 PostgreSQL custom enums)

---

## Core Domain (5 Tables)

### users

User account information. Email is nullable to support broker-only users (authenticate via broker OAuth without email).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | UUID | NO | PK | uuid4 | Primary user identifier |
| email | String | YES | UK | NULL | Email address (nullable for broker-only users) |
| created_at | DateTime(TZ) | NO | - | now() | Account creation timestamp |
| last_login | DateTime(TZ) | YES | - | NULL | Last successful login timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `email`
- Index on `id`

**Relationships:**
- One-to-many: `broker_connections`, `autopilot_strategies`
- One-to-one: `user_preferences`, `smartapi_credentials`, `autopilot_user_settings`, `ai_user_config`, `ai_risk_state`

---

### broker_connections

Broker order execution credentials — stores the access tokens obtained after a user logs in to their broker. Also stores user-level market data API credentials for users who upgrade from the platform default.

> **Important:** This table stores broker ACCESS TOKENS obtained after login — NOT the raw login credentials (Client ID, PIN, TOTP) that a user types. Login credentials are used once for authentication and are never persisted. Platform-level market data credentials (SmartAPI for all users by default) are in `backend/.env`, not this table.

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | UUID | NO | PK | uuid4 | Primary connection identifier |
| user_id | UUID | NO | FK | - | Reference to users.id (CASCADE delete) |
| broker | String(50) | NO | - | - | Broker name: zerodha, angelone, upstox |
| broker_user_id | String(100) | NO | - | - | Broker's client ID (e.g., AB1234) |
| access_token | Text | NO | - | - | Broker access token (encrypted in production) |
| refresh_token | Text | YES | - | NULL | Broker refresh token (not all brokers provide) |
| token_expiry | DateTime(TZ) | YES | - | NULL | Access token expiry timestamp |
| is_active | Boolean | NO | - | TRUE | Connection active status |
| created_at | DateTime(TZ) | NO | - | now() | Connection creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Index on `user_id`
- Index on `id`

**Business Logic:**
- `broker` stores raw values ('zerodha', 'angelone'), but application uses BrokerType enum ('kite', 'angel')
- SmartAPI tokens auto-refresh (8h validity), Kite requires re-authentication (24h validity)
- `is_active=False` marks connection as revoked/expired

---

### user_preferences

User UI preferences and broker selection for market data.

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary preference identifier |
| user_id | UUID | NO | FK,UK | - | Reference to users.id (CASCADE delete), unique |
| market_data_source | String | YES | - | NULL | Selected market data broker: smartapi, kite, upstox, dhan, fyers, paytm |
| ui_settings | JSONB | NO | - | {} | UI customization (theme, layout, etc.) |
| created_at | DateTime(TZ) | NO | - | now() | Preference creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Constraints:**
- Unique constraint on `user_id` (one-to-one with users)

**Business Logic:**
- `market_data_source` determines which broker adapter is used for live quotes, historical data, WebSocket ticks
- Default source: SmartAPI (FREE)

---

### smartapi_credentials

User's OPTIONAL SmartAPI (AngelOne) market data API credentials — for users who upgrade from the platform-default market data to their own broker API.

> **Important:** This table stores a user's own AngelOne API credentials configured via the Settings page — an optional upgrade from the platform default. This is NOT where platform-level credentials live (those are in `backend/.env`). This is also NOT where login credentials live (those are never stored).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary credential identifier |
| user_id | UUID | NO | FK,UK | - | Reference to users.id (CASCADE delete), unique |
| api_key_encrypted | Text | YES | - | NULL | Encrypted SmartAPI API key |
| client_code_encrypted | Text | YES | - | NULL | Encrypted client code |
| mpin_encrypted | Text | YES | - | NULL | Encrypted MPIN (6 digits) |
| totp_secret_encrypted | Text | YES | - | NULL | Encrypted TOTP secret (base32) |
| is_active | Boolean | NO | - | TRUE | Credential active status |
| created_at | DateTime(TZ) | NO | - | now() | Credential creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Security:**
- All sensitive fields encrypted with AES-256 via `app/utils/encryption.py`
- TOTP secret generates 6-digit OTP via `pyotp` library
- Auto-TOTP enables hands-free SmartAPI authentication

**Business Logic:**
- Used by `smartapi_auth.py` service for auto-TOTP login when user has opted into their own SmartAPI account
- Tokens refresh automatically every 8 hours
- If this table has no entry for a user, they fall back to the platform-level SmartAPI credentials from `.env`

---

### instruments

Instrument master data (stocks, options, futures).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary instrument identifier |
| instrument_token | BigInt | NO | UK | - | Broker instrument token (Kite format) |
| exchange | String | NO | - | - | Exchange: NFO, NSE, BSE |
| tradingsymbol | String | NO | - | - | Trading symbol (e.g., NIFTY 26 DEC 24000 CE) |
| name | String | YES | - | NULL | Instrument full name |
| expiry | Date | YES | - | NULL | Option/future expiry date (nullable for stocks) |
| strike | Numeric(10,2) | YES | - | NULL | Option strike price (nullable for stocks/futures) |
| instrument_type | String | NO | - | - | Instrument type: CE, PE, FUT, EQ |
| lot_size | Integer | NO | - | - | Lot size (e.g., NIFTY=25, BANKNIFTY=15) |
| last_updated | DateTime(TZ) | NO | - | now() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `instrument_token`

**Business Logic:**
- Populated on server startup from broker instrument CSV (Kite format)
- Auto-downloaded if database is empty
- Updated daily before market open (9:00 AM)

---

## Trading Domain (4 Tables)

### strategies

Manual strategy configurations (user-created, not AutoPilot).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary strategy identifier |
| user_id | UUID | NO | FK | - | Reference to users.id (CASCADE delete) |
| name | String | NO | - | - | Strategy display name |
| strategy_type | String | NO | - | - | Strategy type (e.g., Iron Condor, Straddle) |
| underlying | String | NO | - | - | Underlying: NIFTY, BANKNIFTY, FINNIFTY, SENSEX |
| legs | JSONB | NO | - | [] | Strategy legs configuration (array of leg objects) |
| target_profit | Numeric(12,2) | YES | - | NULL | Target profit amount |
| stop_loss | Numeric(12,2) | YES | - | NULL | Stop loss amount |
| status | String | NO | - | draft | Strategy status: draft, active, completed |
| created_at | DateTime(TZ) | NO | - | now() | Strategy creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Relationships:**
- One-to-many: `strategy_legs`

**Business Logic:**
- Manual strategy builder (not automated execution)
- Used for P&L simulation and payoff diagram generation

---

### strategy_legs

Individual legs of a manual strategy.

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary leg identifier |
| strategy_id | BigInt | NO | FK | - | Reference to strategies.id (CASCADE delete) |
| leg_number | Integer | NO | - | - | Leg sequence number (0-indexed) |
| option_type | String(2) | NO | - | - | Option type: CE, PE |
| action | String(4) | NO | - | - | Action: BUY, SELL |
| strike_offset | Integer | NO | - | - | Strike offset from ATM (e.g., +100, -50) |
| quantity | Integer | NO | - | - | Lot-adjusted quantity |
| premium | Numeric(10,2) | YES | - | NULL | Premium per contract |

**Indexes:**
- Primary key on `id`
- Index on `strategy_id`

---

### strategy_templates

Pre-configured strategy templates (Iron Condor, Butterfly, etc.).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary template identifier |
| name | String | NO | UK | - | Template display name (unique) |
| description | String | YES | - | NULL | Template description |
| strategy_type | String | NO | - | - | Strategy type (e.g., Iron Condor) |
| legs_config | JSONB | NO | - | {} | Leg configuration (reusable structure) |
| risk_level | String | YES | - | NULL | Risk level: LOW, MEDIUM, HIGH |
| is_active | Boolean | NO | - | TRUE | Template active status |
| created_at | DateTime(TZ) | NO | - | now() | Template creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique index on `name`

**Business Logic:**
- Used by Strategy Builder to pre-fill leg configurations
- Can be user-created or system-provided

---

### broker_instrument_tokens

Cross-broker token/symbol mapping for multi-broker abstraction.

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary mapping identifier |
| canonical_symbol | String | NO | - | - | Canonical symbol (Kite format internally) |
| broker | String | NO | - | - | Broker: smartapi, kite, upstox, dhan, fyers, paytm |
| broker_symbol | String | YES | - | NULL | Broker-specific symbol (e.g., SmartAPI format) |
| broker_token | BigInt | YES | - | NULL | Broker-specific instrument token |
| exchange | String | NO | - | - | Exchange: NFO, NSE, BSE |
| expiry | Date | YES | - | NULL | Option/future expiry date |
| strike | Numeric(10,2) | YES | - | NULL | Option strike price |
| instrument_type | String | NO | - | - | Instrument type: CE, PE, FUT, EQ |
| last_updated | DateTime(TZ) | NO | - | now() | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Index on `canonical_symbol`
- Index on `broker`
- Index on `broker_symbol`
- Index on `broker_token`
- Index on `expiry`
- Unique constraint on `(canonical_symbol, broker)`

**Business Logic:**
- Used by `TokenManager` for efficient cross-broker token/symbol lookups
- Enables broker-agnostic code (use canonical format internally, convert on API calls)
- Populated during instrument download/sync

---

## AutoPilot Domain (18 Tables)

(Continuing with remaining 13 tables in next section due to length...)

### autopilot_user_settings

Global AutoPilot settings per user (risk limits, defaults, feature flags).

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary settings identifier |
| user_id | UUID | NO | FK,UK | - | Reference to users.id (CASCADE delete), unique |
| daily_loss_limit | Numeric(12,2) | NO | - | 20000.00 | Max daily loss (system stops if breached) |
| per_strategy_loss_limit | Numeric(12,2) | NO | - | 10000.00 | Max loss per strategy |
| max_capital_deployed | Numeric(14,2) | NO | - | 500000.00 | Max capital deployed across all strategies |
| max_active_strategies | Integer | NO | - | 3 | Max concurrent active strategies |
| no_trade_first_minutes | Integer | NO | - | 5 | No trading in first N minutes after market open |
| no_trade_last_minutes | Integer | NO | - | 5 | No trading in last N minutes before market close |
| cooldown_after_loss | Boolean | NO | - | FALSE | Enable cooldown after loss threshold |
| cooldown_minutes | Integer | NO | - | 30 | Cooldown duration |
| cooldown_threshold | Numeric(12,2) | NO | - | 5000.00 | Loss amount triggering cooldown |
| default_order_settings | JSONB | NO | - | {} | Default order settings (order type, product, etc.) |
| notification_prefs | JSONB | NO | - | {} | Notification preferences |
| failure_handling | JSONB | NO | - | {} | Error handling configuration |
| paper_trading_mode | Boolean | NO | - | FALSE | Global paper trading mode |
| show_advanced_features | Boolean | NO | - | FALSE | Show advanced UI features |
| kill_switch_enabled | Boolean | NO | - | FALSE | Kill switch status |
| kill_switch_triggered_at | DateTime(TZ) | YES | - | NULL | Kill switch trigger timestamp |
| default_execution_mode | Enum | NO | - | auto | Default execution mode: auto, semi_auto, manual |
| confirmation_timeout_seconds | Integer | NO | - | 30 | Semi-auto confirmation timeout |
| auto_exit_time | String(5) | YES | - | 15:15 | Auto-exit time (HH:MM format) |
| account_capital | Numeric(14,2) | YES | - | NULL | Total account capital |
| risk_per_trade_pct | Numeric(5,2) | YES | - | 2.00 | Risk % per trade |
| delta_watch_threshold | Numeric(4,2) | NO | - | 0.20 | Delta watch threshold |
| delta_warning_threshold | Numeric(4,2) | NO | - | 0.30 | Delta warning threshold |
| delta_danger_threshold | Numeric(4,2) | NO | - | 0.40 | Delta danger threshold |
| delta_alert_enabled | Boolean | NO | - | TRUE | Enable delta alerts |
| suggestions_enabled | Boolean | NO | - | TRUE | Enable adjustment suggestions |
| prefer_round_strikes | Boolean | NO | - | TRUE | Prefer round strikes in adjustments |
| created_at | DateTime(TZ) | NO | - | now() | Settings creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Constraints:**
- Unique constraint on `user_id` (one-to-one with users)

**Business Logic:**
- `kill_switch_enabled=True` immediately exits all active strategies
- `paper_trading_mode=True` routes all orders to paper trading (no real execution)
- Delta thresholds trigger adjustment suggestions

---

### autopilot_strategies

AutoPilot strategy configurations and execution state.

(This is a very large table with 40+ columns. Key columns listed below.)

**Key Columns:**

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary strategy identifier |
| user_id | UUID | NO | FK | - | Reference to users.id (CASCADE delete) |
| name | String(100) | NO | - | - | Strategy display name |
| status | Enum | NO | - | draft | Status: draft, waiting, active, paused, completed, error, etc. |
| underlying | Enum | NO | - | - | NIFTY, BANKNIFTY, FINNIFTY, SENSEX |
| expiry_type | String(20) | NO | - | current_week | Expiry type: current_week, next_week, monthly |
| expiry_date | Date | YES | - | NULL | Actual expiry date |
| lots | Integer | NO | - | 1 | Number of lots |
| position_type | Enum | NO | - | intraday | intraday, positional |
| legs_config | JSONB | NO | - | [] | Leg configurations (array) |
| entry_conditions | JSONB | NO | - | {} | Entry condition rules |
| adjustment_rules | JSONB | NO | - | [] | Adjustment rule configurations |
| order_settings | JSONB | NO | - | {} | Order-specific settings |
| risk_settings | JSONB | NO | - | {} | Risk management settings |
| schedule_config | JSONB | NO | - | {} | Scheduling configuration |
| reentry_config | JSONB | YES | - | NULL | Re-entry configuration |
| execution_mode | Enum | YES | - | NULL | Overrides user default: auto, semi_auto, manual |
| trailing_stop_config | JSONB | YES | - | NULL | Trailing stop configuration |
| greeks_snapshot | JSONB | YES | - | NULL | Latest Greeks snapshot |
| staged_entry_config | JSONB | YES | - | NULL | Staged entry configuration |
| position_legs_snapshot | JSONB | YES | - | NULL | Position legs snapshot |
| net_delta | Numeric(6,4) | YES | - | NULL | Net portfolio delta |
| net_theta | Numeric(10,2) | YES | - | NULL | Net portfolio theta |
| net_gamma | Numeric(8,6) | YES | - | NULL | Net portfolio gamma |
| net_vega | Numeric(8,4) | YES | - | NULL | Net portfolio vega |
| breakeven_lower | Numeric(10,2) | YES | - | NULL | Lower breakeven price |
| breakeven_upper | Numeric(10,2) | YES | - | NULL | Upper breakeven price |
| dte | Integer | YES | - | NULL | Days to expiry |
| priority | Integer | NO | - | 100 | Strategy execution priority |
| runtime_state | JSONB | YES | - | NULL | Runtime state (internal) |
| trading_mode | Enum | YES | - | NULL | live, paper |
| activated_in_mode | Enum | YES | - | NULL | Mode when activated |
| ai_deployed | Boolean | YES | - | FALSE | Deployed by AI |
| ai_confidence_score | Numeric(5,2) | YES | - | NULL | AI confidence score (0-100) |
| ai_regime_type | String(30) | YES | - | NULL | Market regime at deployment |
| ai_lots_tier | String(20) | YES | - | NULL | Position sizing tier: SKIP, LOW, MEDIUM, HIGH |
| ai_explanation | Text | YES | - | NULL | AI-generated explanation |
| source_template_id | BigInt | YES | FK | NULL | Reference to autopilot_templates.id |
| cloned_from_id | BigInt | YES | FK | NULL | Reference to autopilot_strategies.id (self) |
| share_mode | Enum | NO | - | private | private, link, public |
| share_token | String(50) | YES | UK | NULL | Unique share token |
| shared_at | DateTime(TZ) | YES | - | NULL | Share timestamp |
| version | Integer | NO | - | 1 | Strategy version |
| created_at | DateTime(TZ) | NO | - | now() | Strategy creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |
| activated_at | DateTime(TZ) | YES | - | NULL | Activation timestamp |
| completed_at | DateTime(TZ) | YES | - | NULL | Completion timestamp |

**Relationships:**
- One-to-many: `autopilot_orders`, `autopilot_logs`, `autopilot_adjustment_logs`, `autopilot_pending_confirmations`, `autopilot_position_legs`, `autopilot_adjustment_suggestions`
- Many-to-one: `autopilot_templates` (source template)
- Self-reference: `autopilot_strategies` (cloned from)

**Business Logic:**
- Status workflow: draft → waiting → active → completed/paused/error
- `execution_mode` can override user default per strategy
- `ai_deployed=True` marks strategies created by AI module
- `share_mode=link/public` enables strategy sharing

---

### autopilot_orders

Individual order records placed by AutoPilot.

(40+ columns. Key columns listed below.)

**Key Columns:**

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary order identifier |
| strategy_id | BigInt | NO | FK | - | Reference to autopilot_strategies.id |
| user_id | UUID | NO | FK | - | Reference to users.id |
| kite_order_id | String(50) | YES | - | NULL | Broker order ID (Kite format) |
| kite_exchange_order_id | String(50) | YES | - | NULL | Exchange order ID |
| purpose | Enum | NO | - | - | entry, adjustment, hedge, exit, roll_close, roll_open, kill_switch |
| rule_name | String(100) | YES | - | NULL | Rule that triggered the order |
| leg_index | Integer | NO | - | 0 | Leg index |
| exchange | String(10) | NO | - | NFO | Exchange |
| tradingsymbol | String(50) | NO | - | - | Trading symbol |
| instrument_token | BigInt | YES | - | NULL | Instrument token |
| underlying | Enum | NO | - | - | NIFTY, BANKNIFTY, FINNIFTY, SENSEX |
| contract_type | String(2) | NO | - | - | CE, PE |
| strike | Numeric(10,2) | YES | - | NULL | Strike price |
| expiry | Date | NO | - | - | Expiry date |
| transaction_type | Enum | NO | - | - | BUY, SELL |
| order_type | Enum | NO | - | - | MARKET, LIMIT, SL, SL-M |
| product | String(10) | NO | - | NRML | Product type: NRML, MIS |
| quantity | Integer | NO | - | - | Order quantity |
| order_price | Numeric(10,2) | YES | - | NULL | Order price (for LIMIT orders) |
| trigger_price | Numeric(10,2) | YES | - | NULL | Trigger price (for SL orders) |
| ltp_at_order | Numeric(10,2) | YES | - | NULL | LTP at order placement |
| executed_price | Numeric(10,2) | YES | - | NULL | Actual execution price |
| executed_quantity | Integer | NO | - | 0 | Executed quantity |
| pending_quantity | Integer | YES | - | NULL | Pending quantity |
| slippage_amount | Numeric(10,2) | YES | - | NULL | Slippage amount |
| slippage_pct | Numeric(5,2) | YES | - | NULL | Slippage percentage |
| status | Enum | NO | - | pending | pending, placed, open, complete, cancelled, rejected, error |
| rejection_reason | String(500) | YES | - | NULL | Rejection reason |
| order_placed_at | DateTime(TZ) | YES | - | NULL | Order placement timestamp |
| order_filled_at | DateTime(TZ) | YES | - | NULL | Order fill timestamp |
| execution_duration_ms | Integer | YES | - | NULL | Execution duration |
| retry_count | Integer | NO | - | 0 | Retry count |
| parent_order_id | BigInt | YES | FK | NULL | Parent order (for retries, self-reference) |
| raw_response | JSONB | YES | - | NULL | Raw broker API response |
| trading_mode | Enum | YES | - | paper | live, paper |
| ai_sizing_mode | String(20) | YES | - | NULL | fixed, tiered, kelly |
| ai_tier_multiplier | Numeric(5,2) | YES | - | NULL | Tier multiplier |
| batch_id | UUID | YES | FK | NULL | Reference to autopilot_order_batches.id |
| batch_sequence | Integer | YES | - | NULL | Sequence within batch |
| triggered_condition | JSONB | YES | - | NULL | Condition that triggered order |
| spot_at_order | Numeric(10,2) | YES | - | NULL | Spot price at order |
| vix_at_order | Numeric(6,2) | YES | - | NULL | VIX at order |
| delta_at_order | Numeric(6,4) | YES | - | NULL | Delta at order |
| gamma_at_order | Numeric(8,6) | YES | - | NULL | Gamma at order |
| theta_at_order | Numeric(10,2) | YES | - | NULL | Theta at order |
| vega_at_order | Numeric(8,4) | YES | - | NULL | Vega at order |
| iv_at_order | Numeric(6,2) | YES | - | NULL | IV at order |
| oi_at_order | BigInt | YES | - | NULL | Open interest at order |
| bid_at_order | Numeric(10,2) | YES | - | NULL | Bid at order |
| ask_at_order | Numeric(10,2) | YES | - | NULL | Ask at order |
| created_at | DateTime(TZ) | NO | - | now() | Order creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Relationships:**
- Many-to-one: `autopilot_strategies`, `users`, `autopilot_order_batches`
- Self-reference: `autopilot_orders` (parent order for retries)

**Business Logic:**
- `purpose` determines order context (entry, adjustment, exit, etc.)
- `trading_mode=paper` routes to paper trading (no real execution)
- Greeks/market snapshot captured at order time for analysis
- `parent_order_id` links retry orders to original

---

(Remaining 15 AutoPilot tables follow the same pattern. Due to length, I'll continue with AI/ML domain next.)

---

## AI/ML Domain (9 Tables)

### ai_user_config

User-specific AI trading configuration.

(40+ columns. Key columns listed below.)

**Key Columns:**

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary config identifier |
| user_id | UUID | NO | FK,UK | - | Reference to users.id (unique) |
| ai_enabled | Boolean | NO | - | FALSE | AI trading enabled |
| autonomy_mode | String(20) | NO | - | paper | paper, live |
| auto_deploy_enabled | Boolean | NO | - | FALSE | Auto-deploy strategies |
| deploy_time | String(5) | YES | - | 09:20 | HH:MM format |
| deploy_days | Array(String) | NO | - | MON-FRI | Trading days |
| skip_event_days | Boolean | NO | - | TRUE | Skip event days |
| skip_weekly_expiry | Boolean | NO | - | FALSE | Skip weekly expiry |
| allowed_strategies | JSONB | NO | - | [] | Allowed template IDs |
| sizing_mode | String(20) | NO | - | tiered | fixed, tiered, kelly |
| base_lots | Integer | NO | - | 1 | Base lot size |
| confidence_tiers | JSONB | NO | - | [...] | Confidence tiers (SKIP, LOW, MEDIUM, HIGH) |
| max_lots_per_strategy | Integer | NO | - | 2 | Max lots per strategy |
| max_lots_per_day | Integer | NO | - | 6 | Max lots per day |
| max_strategies_per_day | Integer | NO | - | 5 | Max strategies per day |
| min_confidence_to_trade | Numeric(5,2) | NO | - | 60.00 | Min confidence (0-100) |
| max_vix_to_trade | Numeric(5,2) | NO | - | 25.00 | Max VIX to trade |
| min_dte_to_enter | Integer | NO | - | 2 | Min DTE to enter |
| weekly_loss_limit | Numeric(12,2) | NO | - | 50000.00 | Weekly loss limit |
| max_stress_risk_score | Numeric(5,2) | NO | - | 75.00 | Max stress risk score (0-100) |
| max_portfolio_delta | Numeric(6,3) | NO | - | 1.000 | Max portfolio delta |
| max_portfolio_gamma | Numeric(8,5) | NO | - | 0.05000 | Max portfolio gamma |
| enable_drawdown_sizing | Boolean | NO | - | FALSE | Enable drawdown-aware sizing |
| drawdown_thresholds | JSONB | NO | - | [...] | Drawdown tiers |
| enable_volatility_sizing | Boolean | NO | - | FALSE | Enable volatility-aware sizing |
| volatility_lookback_days | Integer | NO | - | 30 | Volatility lookback period |
| volatility_thresholds | JSONB | NO | - | [...] | Volatility tiers |
| max_drawdown_to_trade | Numeric(5,2) | NO | - | 25.00 | Max drawdown % to trade |
| high_water_mark | Numeric(14,2) | YES | - | NULL | Peak portfolio value |
| current_drawdown_pct | Numeric(5,2) | NO | - | 0.00 | Current drawdown % |
| enable_drift_detection | Boolean | NO | - | TRUE | Enable regime drift detection |
| drift_lookback_periods | Integer | NO | - | 20 | Drift lookback periods |
| drift_threshold | Numeric(5,2) | NO | - | 30.00 | Drift alert threshold % |
| drift_confidence_penalty | Numeric(5,2) | NO | - | 10.00 | Confidence penalty % |
| min_regime_stability_score | Numeric(5,2) | NO | - | 40.00 | Min regime stability (0-100) |
| current_regime_stability | Numeric(5,2) | NO | - | 100.00 | Current stability (0-100) |
| last_drift_check_at | DateTime(TZ) | YES | - | NULL | Last drift check timestamp |
| enable_ml_blending | Boolean | NO | - | TRUE | Enable global/user ML blending |
| blending_alpha_start | Numeric(3,2) | NO | - | 1.00 | Initial global weight (1.0 = 100% global) |
| blending_alpha_min | Numeric(3,2) | NO | - | 0.20 | Min global weight (0.2 = 20% global) |
| blending_trades_threshold | Integer | NO | - | 100 | Trades needed for full personalization |
| total_trades_completed | Integer | NO | - | 0 | Total completed trades |
| retraining_cadence | String(20) | NO | - | weekly | daily, weekly, volume_based |
| retraining_volume_threshold | Integer | NO | - | 25 | Trades before retrain (volume_based) |
| high_volume_trades_per_week | Integer | NO | - | 50 | Threshold to switch weekly→daily |
| last_user_model_retrain_at | DateTime(TZ) | YES | - | NULL | Last user model retrain |
| min_model_stability_threshold | Numeric(5,2) | NO | - | 5.00 | Max allowed degradation % |
| enable_confidence_weighting | Boolean | NO | - | TRUE | Weight samples by quality |
| trades_since_last_retrain | Integer | NO | - | 0 | Counter for volume-based retrain |
| preferred_underlyings | Array(String) | NO | - | NIFTY,BANKNIFTY | Preferred underlyings |
| paper_start_date | Date | YES | - | NULL | Paper trading start date |
| paper_trades_completed | Integer | NO | - | 0 | Paper trades completed |
| paper_win_rate | Numeric(5,2) | NO | - | 0.00 | Paper win rate % |
| paper_total_pnl | Numeric(14,2) | NO | - | 0.00 | Paper total P&L |
| paper_graduation_approved | Boolean | NO | - | FALSE | Graduated to live |
| claude_api_key_encrypted | Text | YES | - | NULL | Encrypted Claude API key |
| enable_ai_explanations | Boolean | NO | - | TRUE | Enable AI explanations |
| created_at | DateTime(TZ) | NO | - | now() | Config creation timestamp |
| updated_at | DateTime(TZ) | YES | - | now() | Last update timestamp |

**Constraints:**
- Unique constraint on `user_id` (one-to-one with users)
- Check constraints on all percentage fields (0-100 range)
- Check constraints on positive values (lots, thresholds, etc.)

**Business Logic:**
- `autonomy_mode=paper` runs AI in paper trading mode (no real execution)
- `confidence_tiers` defines position sizing based on AI confidence
- Graduation from paper→live requires: 15 days + 25 trades + 55% win rate
- `enable_ml_blending` gradually shifts from global model to user-specific model

---

### ai_model_registry

ML model version tracking and deployment.

| Column | Type | Nullable | Key | Default | Description |
|--------|------|----------|-----|---------|-------------|
| id | BigInt | NO | PK | autoincrement | Primary model identifier |
| version | String(50) | NO | - | - | Model version (e.g., v1.2.3) |
| model_type | String(20) | NO | - | - | xgboost, lightgbm |
| scope | String(10) | NO | - | user | global, user |
| user_id | UUID | YES | FK | NULL | Reference to users.id (NULL for global models) |
| file_path | Text | NO | - | - | Model file path |
| description | Text | YES | - | NULL | Model description |
| accuracy | Numeric(5,4) | YES | - | NULL | Accuracy (0-1) |
| precision | Numeric(5,4) | YES | - | NULL | Precision (0-1) |
| recall | Numeric(5,4) | YES | - | NULL | Recall (0-1) |
| f1_score | Numeric(5,4) | YES | - | NULL | F1 score (0-1) |
| roc_auc | Numeric(5,4) | YES | - | NULL | ROC AUC (0-1) |
| is_active | Boolean | NO | - | FALSE | Active deployment status |
| activated_at | DateTime(TZ) | YES | - | NULL | Activation timestamp |
| trained_at | DateTime(TZ) | NO | - | - | Training completion timestamp |
| created_at | DateTime(TZ) | NO | - | now() | Model creation timestamp |

**Indexes:**
- Partial unique index on `version` WHERE scope='global' (global versions unique)
- Partial unique index on `(version, user_id)` WHERE user_id IS NOT NULL (user versions unique per user)

**Constraints:**
- Check constraint: `(scope='global' AND user_id IS NULL) OR (scope='user' AND user_id IS NOT NULL)`

**Business Logic:**
- `scope=global` models trained on all users' data
- `scope=user` models personalized to individual user
- Only one model can be active per user (or globally)

---

(Remaining 7 AI/ML tables follow similar pattern.)

---

## PostgreSQL Enums (19 Types)

AlgoChanakya uses PostgreSQL enum types for type safety and database-level constraints:

| Enum Name | Values | Usage |
|-----------|--------|-------|
| `autopilot_strategy_status` | draft, waiting, waiting_staged_entry, active, pending, paused, reentry_waiting, completed, error, expired, cancelled | autopilot_strategies.status |
| `autopilot_underlying` | NIFTY, BANKNIFTY, FINNIFTY, SENSEX | autopilot_strategies.underlying, autopilot_orders.underlying |
| `autopilot_position_type` | intraday, positional | autopilot_strategies.position_type |
| `autopilot_execution_mode` | auto, semi_auto, manual | autopilot_user_settings.default_execution_mode, autopilot_strategies.execution_mode, autopilot_adjustment_logs.execution_mode |
| `autopilot_trading_mode` | live, paper | autopilot_strategies.trading_mode, autopilot_orders.trading_mode, autopilot_order_batches.trading_mode |
| `autopilot_order_purpose` | entry, adjustment, hedge, exit, roll_close, roll_open, kill_switch | autopilot_orders.purpose, autopilot_order_batches.purpose |
| `autopilot_transaction_type` | BUY, SELL | autopilot_orders.transaction_type |
| `autopilot_order_type` | MARKET, LIMIT, SL, SL-M | autopilot_orders.order_type |
| `autopilot_order_status` | pending, placed, open, complete, cancelled, rejected, error | autopilot_orders.status |
| `autopilot_log_event` | 50+ event types (strategy_created, entry_triggered, order_placed, etc.) | autopilot_logs.event_type |
| `autopilot_log_severity` | debug, info, warning, error, critical | autopilot_logs.severity |
| `autopilot_adjustment_trigger_type` | pnl_based, delta_based, time_based, premium_based, vix_based, spot_based | autopilot_adjustment_logs.trigger_type |
| `autopilot_adjustment_action_type` | add_hedge, close_leg, roll_strike, roll_expiry, exit_all, scale_down, scale_up | autopilot_adjustment_logs.action_type |
| `autopilot_confirmation_status` | pending, confirmed, rejected, expired, cancelled | autopilot_pending_confirmations.status |
| `autopilot_exit_reason` | target_hit, stop_loss, trailing_stop, time_exit, manual_exit, adjustment_exit, kill_switch, auto_exit, error | autopilot_trade_journal.exit_reason |
| `autopilot_share_mode` | private, link, public | autopilot_strategies.share_mode |
| `autopilot_report_type` | daily, weekly, monthly, custom, strategy, tax | autopilot_reports.report_type |
| `autopilot_report_format` | pdf, excel, csv | autopilot_reports.format |
| `autopilot_backtest_status` | pending, running, completed, failed, cancelled | autopilot_backtests.status |

**Note:** Enum types are created via Alembic migrations and referenced in model definitions.

---

## Foreign Key Relationships

Summary of all foreign key relationships (30+ total):

### Core Domain

- `broker_connections.user_id` → `users.id` (CASCADE)
- `user_preferences.user_id` → `users.id` (CASCADE)
- `smartapi_credentials.user_id` → `users.id` (CASCADE)

### Trading Domain

- `strategies.user_id` → `users.id` (CASCADE)
- `strategy_legs.strategy_id` → `strategies.id` (CASCADE)

### AutoPilot Domain

- `autopilot_user_settings.user_id` → `users.id` (CASCADE)
- `autopilot_strategies.user_id` → `users.id` (CASCADE)
- `autopilot_strategies.source_template_id` → `autopilot_templates.id` (SET NULL)
- `autopilot_strategies.cloned_from_id` → `autopilot_strategies.id` (SET NULL, self-reference)
- `autopilot_orders.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_orders.user_id` → `users.id` (CASCADE)
- `autopilot_orders.batch_id` → `autopilot_order_batches.id` (SET NULL)
- `autopilot_orders.parent_order_id` → `autopilot_orders.id` (SET NULL, self-reference)
- `autopilot_order_batches.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_order_batches.user_id` → `users.id` (CASCADE)
- `autopilot_logs.user_id` → `users.id` (CASCADE)
- `autopilot_logs.strategy_id` → `autopilot_strategies.id` (SET NULL)
- `autopilot_logs.order_id` → `autopilot_orders.id` (SET NULL)
- `autopilot_templates.user_id` → `users.id` (SET NULL)
- `autopilot_template_ratings.template_id` → `autopilot_templates.id` (CASCADE)
- `autopilot_template_ratings.user_id` → `users.id` (CASCADE)
- `autopilot_condition_eval.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_daily_summary.user_id` → `users.id` (CASCADE)
- `autopilot_adjustment_logs.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_adjustment_logs.user_id` → `users.id` (CASCADE)
- `autopilot_adjustment_logs.confirmation_id` → `autopilot_pending_confirmations.id` (SET NULL)
- `autopilot_pending_confirmations.user_id` → `users.id` (CASCADE)
- `autopilot_pending_confirmations.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_trade_journal.user_id` → `users.id` (CASCADE)
- `autopilot_trade_journal.strategy_id` → `autopilot_strategies.id` (SET NULL)
- `autopilot_analytics_cache.user_id` → `users.id` (CASCADE)
- `autopilot_reports.user_id` → `users.id` (CASCADE)
- `autopilot_reports.strategy_id` → `autopilot_strategies.id` (SET NULL)
- `autopilot_backtests.user_id` → `users.id` (CASCADE)
- `autopilot_position_legs.strategy_id` → `autopilot_strategies.id` (CASCADE)
- `autopilot_position_legs.rolled_from_leg_id` → `autopilot_position_legs.id` (self-reference)
- `autopilot_adjustment_suggestions.strategy_id` → `autopilot_strategies.id` (CASCADE)

### AI/ML Domain

- `ai_user_config.user_id` → `users.id` (CASCADE)
- `ai_model_registry.user_id` → `users.id` (CASCADE)
- `ai_learning_reports.user_id` → `users.id` (CASCADE)
- `ai_paper_trades.user_id` → `users.id` (CASCADE)
- `ai_risk_state.user_id` → `users.id` (CASCADE)
- `ai_strategy_cooldown.user_id` → `users.id` (CASCADE)
- `ai_regime_history.user_id` → `users.id` (CASCADE, nullable)
- `ai_regime_performance.user_id` → `users.id` (CASCADE)
- `ai_decisions_log.user_id` → `users.id` (CASCADE)
- `ai_decisions_log.strategy_id` → `autopilot_strategies.id` (SET NULL)

**Delete Behavior:**
- `CASCADE`: Child records deleted when parent is deleted (most user-owned data)
- `SET NULL`: Foreign key set to NULL when parent is deleted (references to strategies/templates)

---

## Indexes & Constraints

### Primary Keys
- All tables have `id` as primary key (BigInt autoincrement or UUID)

### Unique Constraints
- `users.email` (unique, nullable)
- `user_preferences.user_id` (one-to-one)
- `smartapi_credentials.user_id` (one-to-one)
- `instruments.instrument_token` (unique)
- `strategy_templates.name` (unique)
- `broker_instrument_tokens.(canonical_symbol, broker)` (unique composite)
- `autopilot_user_settings.user_id` (one-to-one)
- `autopilot_strategies.share_token` (unique, nullable)
- `autopilot_daily_summary.(user_id, summary_date)` (unique composite)
- `autopilot_analytics_cache.(user_id, cache_key)` (unique composite)
- `autopilot_template_ratings.(template_id, user_id)` (unique composite)
- `autopilot_option_chain_cache.(underlying, expiry, strike, option_type)` (unique composite)
- `autopilot_position_legs.(strategy_id, leg_id)` WHERE status='open' (partial unique)
- `ai_user_config.user_id` (one-to-one)
- `ai_learning_reports.(user_id, report_date)` (unique composite)
- `ai_risk_state.user_id` (one-to-one)
- `ai_regime_history.(user_id, underlying, detected_at)` (unique composite)
- `ai_regime_performance.(user_id, underlying, regime_type)` (unique composite)

### Foreign Key Indexes
- All foreign key columns have indexes (automatic in PostgreSQL)

### Additional Indexes
- `broker_connections.user_id`
- `broker_instrument_tokens.(canonical_symbol, broker, broker_symbol, broker_token, expiry)`
- `autopilot_position_legs.(strategy_id, status)`
- `autopilot_adjustment_suggestions.(strategy_id, status)`
- `autopilot_option_chain_cache.(underlying, expiry), (underlying, expiry, option_type, delta)`
- `ai_paper_trades.(user_id, status, entry_time)`
- `ai_model_registry.version` (partial, WHERE scope='global')
- `ai_model_registry.(version, user_id)` (partial, WHERE user_id IS NOT NULL)

### Check Constraints
- `autopilot_template_ratings.rating` (1-5 range)
- Percentage fields (0-100 range): win_rate, confidence, risk scores, drawdown, etc.
- Positive values: lots, quantities, thresholds
- Model accuracy fields (0-1 range)
- Enum value constraints: scope IN ('global', 'user'), status IN (...), etc.
- Scope/user_id consistency: `(scope='global' AND user_id IS NULL) OR (scope='user' AND user_id IS NOT NULL)`

---

## ASCII ERD Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CORE DOMAIN (5 tables)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  users (id, email, created_at, last_login)                              │
│    ├─► broker_connections (broker, access_token, is_active)            │
│    ├─► user_preferences (market_data_source, ui_settings)              │
│    ├─► smartapi_credentials (encrypted credentials, totp_secret)       │
│    └─► [links to 20+ tables via user_id FK]                            │
│                                                                         │
│  instruments (instrument_token, tradingsymbol, strike, expiry)          │
│  broker_instrument_tokens (canonical_symbol, broker, broker_token)      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       TRADING DOMAIN (4 tables)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  strategies (name, strategy_type, underlying, legs, status)             │
│    └─► strategy_legs (option_type, action, strike_offset, quantity)    │
│                                                                         │
│  strategy_templates (name, legs_config, risk_level)                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     AUTOPILOT DOMAIN (18 tables)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  autopilot_user_settings (risk limits, execution mode, kill switch)     │
│                                                                         │
│  autopilot_strategies (legs_config, entry_conditions, adjustment_rules) │
│    ├─► autopilot_orders (order details, Greeks snapshot)               │
│    │     └─► autopilot_order_batches (batch context, market snapshot)  │
│    ├─► autopilot_logs (event_type, severity, message)                  │
│    ├─► autopilot_condition_eval (condition progress)                   │
│    ├─► autopilot_adjustment_logs (trigger, action, execution)          │
│    ├─► autopilot_pending_confirmations (semi-auto approvals)           │
│    ├─► autopilot_position_legs (Greeks, P&L, roll tracking)            │
│    └─► autopilot_adjustment_suggestions (AI suggestions)               │
│                                                                         │
│  autopilot_templates (strategy templates, ratings)                      │
│    └─► autopilot_template_ratings (user ratings)                       │
│                                                                         │
│  autopilot_daily_summary (daily P&L, statistics)                        │
│  autopilot_trade_journal (full trade lifecycle, screenshots)            │
│  autopilot_analytics_cache (pre-calculated metrics)                     │
│  autopilot_reports (PDF/Excel reports)                                  │
│  autopilot_backtests (historical simulation results)                    │
│  autopilot_option_chain_cache (Greeks cache)                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       AI/ML DOMAIN (9 tables)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ai_user_config (autonomy settings, position sizing, graduation)        │
│  ai_model_registry (model versions, metrics, deployment)                │
│  ai_learning_reports (daily self-learning, quality scores)              │
│  ai_paper_trades (paper trading records)                                │
│  ai_risk_state (GREEN/YELLOW/RED states, risk factors)                  │
│  ai_strategy_cooldown (template cooldowns after losses)                 │
│  ai_regime_history (market regime detections)                           │
│  ai_regime_performance (per-regime P&L statistics)                      │
│  ai_decisions_log (AI decision audit trail)                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        CACHE DOMAIN (2 tables)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  autopilot_option_chain_cache (option chain Greeks cache)               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

KEY RELATIONSHIPS:
  users (1) ──< (N) autopilot_strategies ──< (N) autopilot_orders
  autopilot_strategies (1) ──< (N) autopilot_position_legs
  autopilot_strategies (1) ──< (N) autopilot_adjustment_logs
  autopilot_strategies (N) ──> (1) autopilot_templates
  autopilot_strategies (N) ──> (1) autopilot_strategies (cloned_from)
  autopilot_orders (N) ──> (1) autopilot_order_batches
  autopilot_orders (N) ──> (1) autopilot_orders (parent_order)
  autopilot_position_legs (N) ──> (1) autopilot_position_legs (rolled_from)
  users (1) ──< (N) ai_paper_trades
  users (1) ──< (N) ai_decisions_log ──> (1) autopilot_strategies
```

---

## Related Documentation

- **[Context Diagram](context-diagram.md)** - External system dependencies
- **[Container/Component Diagram](container-component-diagram.md)** - Internal architecture
- **[Broker Abstraction Architecture](broker-abstraction.md)** - Multi-broker implementation
- **[AutoPilot Database Schema](../autopilot/database-schema.md)** - Detailed AutoPilot schema
- **[AI Module Documentation](../ai/)** - AI/ML implementation details

---

## Migration Management

**Generating Migrations:**
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

**Important:**
- All models MUST be imported in `app/models/__init__.py`
- All models MUST be imported in `backend/alembic/env.py`
- Without both imports, `alembic revision --autogenerate` will NOT detect the model

**Migration Files:** `backend/alembic/versions/`

---

## Database Connection

**Development:**
- Host: VPS 103.118.16.189:5432
- Database: `algochanakya_dev` (separate from production)
- Driver: asyncpg (async native PostgreSQL)
- Pool: 10 min, 20 max connections

**Production:**
- Host: VPS 103.118.16.189:5432
- Database: `algochanakya_prod` (isolated)
- Same connection pool settings

**Environment Variable:** `DATABASE_URL` in `backend/.env`

---

**Last Updated:** 2026-02-16
**Schema Version:** 38 tables, 19 custom enum types
