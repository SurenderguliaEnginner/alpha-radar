"""
ALPHA-RADAR CORE QUANTITATIVE INDICATORS
Pure NumPy & Pandas Vectorized Math. Zero API Dependencies.
"""
import numpy as np
import pandas as pd

def calculate_adr_pct(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Average Daily Range %: Mean of (High - Low) / Low over 20 sessions."""
    daily_range_pct = ((df['High'] - df['Low']) / (df['Low'] + 1e-6)) * 100
    return daily_range_pct.rolling(window=window).mean()

def calculate_prior_box_range(df: pd.DataFrame, window: int = 3) -> tuple:
    """Calculates highest high and lowest low of the prior 3 sessions (Days i-3 to i-1)."""
    box_high = df['High'].shift(1).rolling(window=window).max()
    box_low = df['Low'].shift(1).rolling(window=window).min()
    box_range_pct = ((box_high - box_low) / (box_low + 1e-6)) * 100
    return box_high, box_low, box_range_pct

def calculate_coil_ratio(box_range_pct: pd.Series, adr_pct: pd.Series) -> pd.Series:
    """Atomic Spring Coil: Ratio of 3-Day Consolidation to 20-Day Baseline ADR."""
    return box_range_pct / (adr_pct.shift(1) + 1e-6)

def calculate_rvol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Relative Volume: Current Volume vs 20-day Baseline Volume (shifted to avoid lookahead)."""
    vol_sma = df['Volume'].shift(1).rolling(window=window).mean()
    return df['Volume'] / (vol_sma + 1e-6)

def calculate_wicks_pct(df: pd.DataFrame) -> tuple:
    """Calculates Upper Wick % and Lower Wick % of the total daily candle range."""
    c_range = df['High'] - df['Low']
    body_top = df[['Open', 'Close']].max(axis=1)
    body_bottom = df[['Open', 'Close']].min(axis=1)
    
    upper_wick = df['High'] - body_top
    lower_wick = body_bottom - df['Low']
    
    upper_wick_pct = (upper_wick / (c_range + 1e-6)) * 100
    lower_wick_pct = (lower_wick / (c_range + 1e-6)) * 100
    return upper_wick_pct, lower_wick_pct

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's Standard Relative Strength Index (RSI 14)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-6)
    return 100 - (100 / (1 + rs))
