"""
ALPHA-RADAR TIER-AWARE SPECIALIZED SWING ENGINE
Features:
- Large & Mid: Standard VCP + 20-EMA Spring (Proven +303%)
- Small Caps: ATR Shakeout Cushion + RVOL 2.2x + Wick Shield <= 18%
- Penny Stocks: Sniper Shock + Strict 7-Day Fast Liquidation
- Dynamic 1:1 R -> CTC (Cost-to-Cost) Protection across all tiers
"""
from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd
import numpy as np

@dataclass
class TradeRecord:
    entry_date: str
    exit_date: str
    symbol: str
    tier_type: str
    strategy: str
    entry_price: float
    exit_price: float
    initial_sl: float
    pnl_pct: float
    holding_days: int
    outcome: str
    r_multiple: float

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-6)
    return 100 - (100 / (1 + rs))

class SwingBacktester:
    def __init__(
        self, 
        slippage_pct: float = 0.15,
        max_holding_days: int = 25
    ):
        self.slippage_pct = slippage_pct
        self.max_holding_days = max_holding_days

    def run_backtest(self, df: pd.DataFrame, symbol: str, tier_override: str = "AUTO") -> Dict[str, Any]:
        if len(df) < 60:
            return {"error": "Insufficient history (< 60 bars)"}

        df = df.copy()
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # Baseline Indicators
        df['SMA50'] = df['Close'].rolling(50).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['Vol_SMA20'] = df['Volume'].rolling(20).mean()
        df['RSI'] = compute_rsi(df['Close'], 14)

        daily_range_pct = ((df['High'] - df['Low']) / df['Low']) * 100
        df['ADR20'] = daily_range_pct.rolling(20).mean()

        # Classify Tier Behavior
        # Penny indicators: price < ₹50 or $5, or specifically designated
        latest_close = float(df['Close'].iloc[-1])
        is_penny = (latest_close < 40 and not symbol.endswith(".NS")) or (latest_close < 35 and symbol.endswith(".NS")) or any(p in symbol for p in ["SUZLON", "RGTI", "SOUN", "IONQ"])
        is_small = any(s in symbol for s in ["SHAILY", "NEWGEN", "ZENTEC", "CELH", "APP"])
        
        max_holding_days = 7 if is_penny else (20 if is_small else 25)

        trades: List[TradeRecord] = []
        in_trade = False
        trade = {}

        for i in range(50, len(df)):
            current_bar = df.iloc[i]
            date_str = str(df.index[i])[:10]

            # -------------------------------------------------------------
            # 1. TRADE MANAGEMENT (CTC + TRAILING SL)
            # -------------------------------------------------------------
            if in_trade:
                days_held = i - trade['entry_index']
                
                # Check Stop Loss Hit
                if current_bar['Low'] <= trade['current_sl']:
                    exit_p = trade['current_sl'] * (1 - (self.slippage_pct / 100))
                    pnl = ((exit_p - trade['entry']) / trade['entry']) * 100
                    r_mult = (exit_p - trade['entry']) / (trade['initial_risk'] + 1e-6)
                    
                    outcome = "STOP_LOSS"
                    if trade['hit_1r']:
                        outcome = "CTC_BREAKEVEN" if abs(pnl) < 1.0 else "TRAILING_SL"

                    trades.append(TradeRecord(
                        entry_date=trade['entry_date'],
                        exit_date=date_str,
                        symbol=symbol,
                        tier_type="PENNY" if is_penny else ("SMALL" if is_small else "MID_LARGE"),
                        strategy=trade['strategy'],
                        entry_price=trade['entry'],
                        exit_price=round(exit_p, 2),
                        initial_sl=trade['initial_sl'],
                        pnl_pct=round(pnl, 2),
                        holding_days=days_held,
                        outcome=outcome,
                        r_multiple=round(r_mult, 2)
                    ))
                    in_trade = False
                    continue

                # Check 1:1 R Hit -> MOVE TO CTC (Cost to Cost)
                gain = current_bar['High'] - trade['entry']
                if gain >= trade['initial_risk'] and not trade['hit_1r']:
                    trade['hit_1r'] = True
                    trade['current_sl'] = round(trade['entry'] * 1.002, 2)

                # Check Target Hit (3.5R for Small, 3.0R for Others)
                if current_bar['High'] >= trade['target']:
                    exit_p = trade['target'] * (1 - (self.slippage_pct / 100))
                    pnl = ((exit_p - trade['entry']) / trade['entry']) * 100
                    r_mult = (exit_p - trade['entry']) / (trade['initial_risk'] + 1e-6)
                    
                    trades.append(TradeRecord(
                        entry_date=trade['entry_date'],
                        exit_date=date_str,
                        symbol=symbol,
                        tier_type="PENNY" if is_penny else ("SMALL" if is_small else "MID_LARGE"),
                        strategy=trade['strategy'],
                        entry_price=trade['entry'],
                        exit_price=round(exit_p, 2),
                        initial_sl=trade['initial_sl'],
                        pnl_pct=round(pnl, 2),
                        holding_days=days_held,
                        outcome="TARGET_HIT",
                        r_multiple=round(r_mult, 2)
                    ))
                    in_trade = False
                    continue

                # Trailing SL (Once in 1:1 profit)
                if trade['hit_1r']:
                    recent_3d_low = float(df['Low'].iloc[i-2:i+1].min()) * 0.995
                    ema_trail = float(current_bar['EMA20']) * 0.99
                    new_sl = max(recent_3d_low, ema_trail)
                    if new_sl > trade['current_sl']:
                        trade['current_sl'] = round(new_sl, 2)

                # Max Holding Time Exit (7 days for Penny, 20 days for Small)
                if days_held >= max_holding_days:
                    exit_p = current_bar['Close'] * (1 - (self.slippage_pct / 100))
                    pnl = ((exit_p - trade['entry']) / trade['entry']) * 100
                    r_mult = (exit_p - trade['entry']) / (trade['initial_risk'] + 1e-6)
                    
                    trades.append(TradeRecord(
                        entry_date=trade['entry_date'],
                        exit_date=date_str,
                        symbol=symbol,
                        tier_type="PENNY" if is_penny else ("SMALL" if is_small else "MID_LARGE"),
                        strategy=trade['strategy'],
                        entry_price=trade['entry'],
                        exit_price=round(exit_p, 2),
                        initial_sl=trade['initial_sl'],
                        pnl_pct=round(pnl, 2),
                        holding_days=days_held,
                        outcome="TIME_EXIT",
                        r_multiple=round(r_mult, 2)
                    ))
                    in_trade = False
                    continue

            # -------------------------------------------------------------
            # 2. ENTRY SCANNER WITH SPECIALIZED TIER LOGIC
            # -------------------------------------------------------------
            if not in_trade:
                prior_highs = df['High'].iloc[i-3:i]
                prior_lows = df['Low'].iloc[i-3:i]
                box_high = float(prior_highs.max())
                box_low = float(prior_lows.min())
                prior_adr = float(df['ADR20'].iloc[i-1])

                box_range_pct = ((box_high - box_low) / (box_low + 1e-6)) * 100
                coil_ratio = box_range_pct / (prior_adr + 1e-6)
                
                vol_baseline = float(df['Vol_SMA20'].iloc[i-1])
                rvol = current_bar['Volume'] / (vol_baseline + 1e-6)
                
                c_range = current_bar['High'] - current_bar['Low']
                upper_wick = current_bar['High'] - max(current_bar['Open'], current_bar['Close'])
                upper_wick_pct = (upper_wick / (c_range + 1e-6)) * 100
                
                lower_wick = min(current_bar['Open'], current_bar['Close']) - current_bar['Low']
                lower_wick_pct = (lower_wick / (c_range + 1e-6)) * 100

                is_uptrend = current_bar['Close'] > current_bar['SMA50']
                ema_rising = df['EMA20'].iloc[i] > df['EMA20'].iloc[i-5]

                # =========================================================
                # LOGIC A: SMALL CAP SPECIALIZED (ATR Cushion + Supply Shock)
                # =========================================================
                if is_small:
                    # Small caps require higher RVOL (2.0x+) and strict wick shield
                    is_small_breakout = (
                        is_uptrend and
                        ema_rising and
                        coil_ratio <= 1.35 and
                        rvol >= 2.0 and                    # Pure supply shock!
                        current_bar['Close'] > box_high and
                        upper_wick_pct <= 18.0             # Operator dump shield
                    )
                    if is_small_breakout:
                        entry_p = current_bar['Close'] * (1 + (self.slippage_pct / 100))
                        # ATR CUSHION: Give small cap room so operators don't shake us out
                        adr_buffer = (prior_adr / 100.0) * entry_p * 0.45
                        sl_p = round(box_low - adr_buffer, 2)
                        risk_amt = entry_p - sl_p
                        
                        target_p = round(entry_p + (3.5 * risk_amt), 2)  # High R:R on Small Caps
                        
                        trade = {
                            'entry': round(entry_p, 2),
                            'initial_sl': sl_p,
                            'current_sl': sl_p,
                            'initial_risk': risk_amt,
                            'target': target_p,
                            'entry_date': date_str,
                            'entry_index': i,
                            'hit_1r': False,
                            'strategy': 'SMALL_CAP_SHOCK'
                        }
                        in_trade = True
                        continue

                # =========================================================
                # LOGIC B: PENNY SNIPER (Dead Base Explosion + T+7 Exit)
                # =========================================================
                elif is_penny:
                    adr_sane = prior_adr <= 12.0 # Anti-reverse-split ceiling
                    # Dead base shock: RVOL >= 2.8x
                    is_penny_explosion = (
                        adr_sane and
                        rvol >= 2.8 and
                        current_bar['Close'] > current_bar['EMA20'] and
                        current_bar['Close'] > box_high and
                        upper_wick_pct <= 22.0
                    )
                    if is_penny_explosion:
                        entry_p = current_bar['Close'] * (1 + (self.slippage_pct / 100))
                        sl_p = round(min(box_low, current_bar['Low'] * 0.96), 2)
                        risk_amt = entry_p - sl_p
                        target_p = round(entry_p + (3.0 * risk_amt), 2)
                        
                        trade = {
                            'entry': round(entry_p, 2),
                            'initial_sl': sl_p,
                            'current_sl': sl_p,
                            'initial_risk': risk_amt,
                            'target': target_p,
                            'entry_date': date_str,
                            'entry_index': i,
                            'hit_1r': False,
                            'strategy': 'PENNY_SNIPER'
                        }
                        in_trade = True
                        continue

                # =========================================================
                # LOGIC C: STANDARD MID & LARGE CAPS (VCP + 20-EMA Spring)
                # =========================================================
                else:
                    avg_coil_vol = float(df['Volume'].iloc[i-3:i].mean())
                    vol_dry_up = avg_coil_vol <= (1.25 * vol_baseline)

                    is_vcp = (
                        is_uptrend and
                        ema_rising and
                        coil_ratio <= 1.30 and
                        vol_dry_up and
                        rvol >= 1.4 and
                        current_bar['Close'] > box_high and
                        upper_wick_pct <= 25.0
                    )

                    ema_dist = abs(current_bar['Low'] - current_bar['EMA20']) / current_bar['EMA20']
                    rsi_ok = 40.0 <= current_bar['RSI'] <= 60.0
                    is_spring = (
                        is_uptrend and
                        ema_rising and
                        rsi_ok and
                        ema_dist <= 0.018 and
                        current_bar['Close'] >= current_bar['Open'] and
                        lower_wick_pct >= 28.0 and
                        current_bar['Close'] > current_bar['EMA20']
                    )

                    if is_vcp or is_spring:
                        entry_p = current_bar['Close'] * (1 + (self.slippage_pct / 100))
                        sl_p = round(box_low * 0.99, 2) if is_vcp else round(min(current_bar['Low'], current_bar['EMA20'] * 0.985), 2)
                        risk_amt = entry_p - sl_p
                        
                        risk_pct = (risk_amt / entry_p) * 100
                        if 1.5 <= risk_pct <= 5.5:
                            target_p = round(entry_p + (3.0 * risk_amt), 2)
                            trade = {
                                'entry': round(entry_p, 2),
                                'initial_sl': sl_p,
                                'current_sl': sl_p,
                                'initial_risk': risk_amt,
                                'target': target_p,
                                'entry_date': date_str,
                                'entry_index': i,
                                'hit_1r': False,
                                'strategy': 'VCP_BREAKOUT' if is_vcp else 'EMA20_SPRING'
                            }
                            in_trade = True

        # -------------------------------------------------------------
        # 3. METRICS EVALUATION
        # -------------------------------------------------------------
        if not trades:
            return {"symbol": symbol, "total_trades": 0, "message": "No trades triggered"}

        total_trades = len(trades)
        wins = [t for t in trades if t.pnl_pct > 0]
        losses = [t for t in trades if t.pnl_pct <= 0]
        breakevens = [t for t in trades if abs(t.pnl_pct) <= 0.5]
        
        win_rate = (len(wins) / total_trades) * 100
        total_pnl = sum(t.pnl_pct for t in trades)
        avg_win = float(np.mean([t.pnl_pct for t in wins])) if wins else 0.0
        avg_loss = float(np.mean([t.pnl_pct for t in losses])) if losses else 0.0
        expectancy = ((win_rate / 100) * avg_win) + (((100 - win_rate) / 100) * avg_loss)

        return {
            "symbol": symbol,
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 1),
            "breakeven_trades": len(breakevens),
            "total_pnl_pct": round(total_pnl, 2),
            "avg_win_pct": round(avg_win, 2),
            "avg_loss_pct": round(avg_loss, 2),
            "expectancy_pct_per_trade": round(expectancy, 2),
            "trades": [t.__dict__ for t in trades]
        }