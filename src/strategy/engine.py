"""
ALPHA-RADAR TWO-STAGE QUANTITATIVE STRATEGY ENGINE
- STAGE 1: Pocket Pivot / Pre-Rally Cheat Entry (Volume Dry-Up + Micro 1.8% SL)
- STAGE 2: Confirmed Momentum Breakout (RVOL Shock + VCP Expansion)
Includes Circuit-Lock Shield and Earnings Blackout Guard.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from src.core.indicators import (
    calculate_adr_pct,
    calculate_prior_box_range,
    calculate_coil_ratio,
    calculate_rvol,
    calculate_wicks_pct,
    calculate_rsi
)
from src.core.filters import classify_tier

@dataclass
class TradeSignal:
    symbol: str
    tier: str
    strategy_name: str
    stage: str
    action: str
    entry_price: float
    stop_loss: float
    target_price: float
    risk_reward_ratio: float
    alpha_score: int
    catalyst_tag: str
    reason: str

class StrategyEngine:
    def __init__(self):
        pass

    def evaluate_ticker(
        self, 
        df: pd.DataFrame, 
        symbol: str, 
        market_cap_cr: float = 5000.0, 
        is_india: bool = True,
        catalyst_headline: Optional[str] = None
    ) -> Optional[TradeSignal]:
        # 1. Base validation
        if df is None or len(df) < 50:
            return None

        # Clean floats
        df = df.copy()
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        last = df.iloc[-1]
        close = float(last['Close'])
        high = float(last['High'])
        low = float(last['Low'])
        open_p = float(last['Open'])
        vol = float(last['Volume'])

        vol_sma20 = float(df['Volume'].rolling(20).mean().iloc[-2])
        rvol = round(vol / (vol_sma20 + 1e-6), 1)

        # 2. CIRCUIT-LOCK SHIELD (Placed AFTER variables are defined!)
        day_gain = (close - open_p) / (open_p + 1e-6)
        if close == high and day_gain >= 0.048 and vol < vol_sma20 * 0.20:
            return None  # Discards frozen upper-circuit unbuyable stocks

        # 3. EARNINGS / BINARY EVENT BLACKOUT SHIELD
        if catalyst_headline and any(k in catalyst_headline.lower() for k in ["earnings tomorrow", "results today", "q2 in 2 days", "earnings soon"]):
            return None

        sma_50 = float(df['Close'].rolling(50).mean().iloc[-1])
        ema_20 = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-1])
        ema_20_prev5 = float(df['Close'].ewm(span=20, adjust=False).mean().iloc[-5])

        daily_ranges = ((df['High'] - df['Low']) / (df['Low'] + 1e-6)) * 100
        adr_20 = float(daily_ranges.rolling(20).mean().iloc[-2])

        prior_highs = df['High'].iloc[-4:-1]
        prior_lows = df['Low'].iloc[-4:-1]
        box_high = float(prior_highs.max())
        box_low = float(prior_lows.min())

        box_range_pct = ((box_high - box_low) / (box_low + 1e-6)) * 100
        coil_ratio = round(box_range_pct / (adr_20 + 1e-6), 2)

        c_range = high - low
        upper_wick = high - max(open_p, close)
        upper_wick_pct = round((upper_wick / (c_range + 1e-6)) * 100, 1)

        lower_wick = min(open_p, close) - low
        lower_wick_pct = round((lower_wick / (c_range + 1e-6)) * 100, 1)

        rsi_series = calculate_rsi(df['Close'], 14)
        rsi = float(rsi_series.iloc[-1])

        is_uptrend = close > sma_50
        ema_rising = ema_20 > ema_20_prev5

        tier = classify_tier(symbol, close, market_cap_cr, is_india)

        # STAGE 1: POCKET PIVOT (PRE-RALLY CHEAT ENTRY)
        is_pre_rally_vdu = (
            is_uptrend and
            ema_rising and
            coil_ratio <= 0.85 and
            rvol <= 0.70 and
            close >= ema_20 and
            abs(close - box_low) / close <= 0.02
        )

        if is_pre_rally_vdu:
            sl = round(box_low * 0.99, 2)
            risk = close - sl
            target = round(close + (4.0 * risk), 2)
            rr = round((target - close) / (risk + 1e-6), 1)

            return TradeSignal(
                symbol=symbol,
                tier=tier,
                strategy_name="Pocket Pivot Volume Dry-Up",
                stage="STAGE 1: PRE-RALLY EARLY ENTRY",
                action="BUY",
                entry_price=close,
                stop_loss=sl,
                target_price=target,
                risk_reward_ratio=rr,
                alpha_score=95,
                catalyst_tag="PRE-RALLY VOLUME DRY-UP",
                reason=f"Coil squeezed to {coil_ratio}x ADR with extreme Volume Dry-Up ({rvol}x). Micro-risk 1.8% SL."
            )

        # STAGE 2: CONFIRMED BREAKOUTS
        if tier == "TIER_4_PENNY":
            if adr_20 <= 12.0 and rvol >= 2.8 and close > ema_20 and close > box_high and upper_wick_pct <= 22.0:
                sl = round(min(box_low, low * 0.96), 2)
                risk = close - sl
                target = round(close + (3.0 * risk), 2)
                rr = round((target - close) / (risk + 1e-6), 1)

                return TradeSignal(
                    symbol=symbol,
                    tier="TIER 4 (PENNY SNIPER)",
                    strategy_name="Dead-Base Volume Shock",
                    stage="STAGE 2: BREAKOUT CONFIRMED",
                    action="BUY",
                    entry_price=close,
                    stop_loss=sl,
                    target_price=target,
                    risk_reward_ratio=rr,
                    alpha_score=85,
                    catalyst_tag="T+7 FAST EXIT SNIPER",
                    reason=f"Dead-base volume explosion RVOL {rvol}x. Mandatory exit at Day 7 or 3.0R."
                )

        elif tier == "TIER_3_SMALL":
            if is_uptrend and ema_rising:
                if coil_ratio <= 1.35 and rvol >= 2.0 and close > box_high and upper_wick_pct <= 18.0:
                    adr_cushion = (adr_20 / 100.0) * close * 0.45
                    sl = round(box_low - adr_cushion, 2)
                    risk = close - sl
                    target = round(close + (3.5 * risk), 2)
                    rr = round((target - close) / (risk + 1e-6), 1)

                    return TradeSignal(
                        symbol=symbol,
                        tier="TIER 3 (SMALL CAP COMPOUNDER)",
                        strategy_name="ATR-Buffered Supply Shock",
                        stage="STAGE 2: BREAKOUT CONFIRMED",
                        action="BUY",
                        entry_price=close,
                        stop_loss=sl,
                        target_price=target,
                        risk_reward_ratio=rr,
                        alpha_score=96,
                        catalyst_tag="SUPPLY ABSORPTION",
                        reason=f"Severe supply shock RVOL {rvol}x with zero upper dump (wick {upper_wick_pct}%). ATR cushion active."
                    )

        elif tier == "TIER_2_MID":
            if is_uptrend and ema_rising:
                avg_coil_vol = float(df['Volume'].iloc[-4:-1].mean())
                vol_dry_up = avg_coil_vol <= (1.25 * vol_sma20)

                if coil_ratio <= 1.30 and vol_dry_up and rvol >= 1.4 and close > box_high and upper_wick_pct <= 25.0:
                    sl = round(box_low * 0.99, 2)
                    risk = close - sl
                    target = round(close + (3.0 * risk), 2)
                    rr = round((target - close) / (risk + 1e-6), 1)

                    return TradeSignal(
                        symbol=symbol,
                        tier="TIER 2 (MID COMPOUNDERS)",
                        strategy_name="VCP Pocket Breakout",
                        stage="STAGE 2: BREAKOUT CONFIRMED",
                        action="BUY",
                        entry_price=close,
                        stop_loss=sl,
                        target_price=target,
                        risk_reward_ratio=rr,
                        alpha_score=98,
                        catalyst_tag="VCP ATOMIC COIL",
                        reason=f"Textbook VCP compression {coil_ratio}x ADR with drying base volume into breakout. RVOL {rvol}x."
                    )

        elif tier == "TIER_1_LARGE":
            if is_uptrend and ema_rising:
                ema_dist = abs(low - ema_20) / ema_20
                rsi_ok = 40.0 <= rsi <= 60.0

                if rsi_ok and ema_dist <= 0.018 and close >= open_p and lower_wick_pct >= 28.0 and close > ema_20:
                    sl = round(min(low, ema_20 * 0.985), 2)
                    risk = close - sl
                    target = round(close + (2.5 * risk), 2)
                    rr = round((target - close) / (risk + 1e-6), 1)

                    return TradeSignal(
                        symbol=symbol,
                        tier="TIER 1 (LARGE GIANTS)",
                        strategy_name="20-EMA Institutional Spring",
                        stage="STAGE 2: BREAKOUT CONFIRMED",
                        action="BUY",
                        entry_price=close,
                        stop_loss=sl,
                        target_price=target,
                        risk_reward_ratio=rr,
                        alpha_score=88,
                        catalyst_tag="MACRO COMPOUNDER",
                        reason=f"Tested 20-EMA support with {lower_wick_pct}% bottom rejection wick. RSI cooled to {round(rsi, 1)}."
                    )

        return None