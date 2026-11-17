"""
ALPHA-RADAR MARKET-CAP CLASSIFIER & LIQUIDITY SHIELDS
Categorizes assets into 4 Microstructure Tiers and eliminates illiquid traps.
"""
import pandas as pd

def classify_tier(symbol: str, close: float, market_cap_cr: float, is_india: bool = True) -> str:
    """
    Classifies equities into 4 Distinct Microstructure Tiers:
    - TIER_4_PENNY: Speculative lotteries (< ₹35 in IN / < $5 in US or < ₹500 Cr cap)
    - TIER_1_LARGE: Mega Giants (> ₹25,000 Cr in IN / > $15B in US)
    - TIER_3_SMALL: High-Beta Supply Shock (₹500 - ₹5,000 Cr in IN / $300M - $2B in US)
    - TIER_2_MID: The Sweet Spot Multi-Baggers (Everything in between)
    """
    if is_india:
        if close < 35.0 or market_cap_cr < 500.0:
            return "TIER_4_PENNY"
        elif market_cap_cr >= 25000.0:
            return "TIER_1_LARGE"
        elif 500.0 <= market_cap_cr < 5000.0:
            return "TIER_3_SMALL"
        else:
            return "TIER_2_MID"
    else:
        # US Primary Markets ($ Millions)
        if close < 5.0 or market_cap_cr < 300.0:
            return "TIER_4_PENNY"
        elif market_cap_cr >= 15000.0:
            return "TIER_1_LARGE"
        elif 300.0 <= market_cap_cr < 2000.0:
            return "TIER_3_SMALL"
        else:
            return "TIER_2_MID"

def validate_liquidity_floor(df: pd.DataFrame, is_india: bool = True) -> bool:
    """
    Strict Liquidity Floor:
    - India: 20-Day Average Daily Turnover >= ₹1.5 Crore
    - US: 20-Day Average Daily Turnover >= $500,000
    Eliminates lower-circuit death traps permanently.
    """
    turnover_20d = (df['Close'] * df['Volume']).rolling(20).mean().iloc[-1]
    floor = 15_000_000.0 if is_india else 500_000.0
    return turnover_20d >= floor