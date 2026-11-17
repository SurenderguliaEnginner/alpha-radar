"""
ALPHA-RADAR DEEP HISTORICAL AUDIT (5 TO 8-YEAR STRESS TEST)
Testing across multiple market regimes with Trailing SL & CTC.
"""
import yfinance as yf
import pandas as pd
from src.backtest.engine import SwingBacktester

# Elite Momentum Basket across India & US
SWING_UNIVERSE = [
    "TRENT.NS",
    "DIXON.NS",
    "HAL.NS",
    "BSE.NS",
    "KAYNES.NS",
    "NVDA",
    "PLTR",
    "IONQ"
]

def main():
    print("=" * 80)
    print("🛰️ ALPHA-RADAR DEEP MULTI-YEAR AUDIT (DYNAMIC CTC & TRAILING SL)")
    print("=" * 80)
    
    backtester = SwingBacktester(slippage_pct=0.15, max_holding_days=25)
    all_results = []
    all_trades = []

    for sym in SWING_UNIVERSE:
        print(f"[*] Testing {sym} (8-Year Deep Data)...", end=" ", flush=True)
        try:
            # Download up to 8 years of history
            df = yf.download(sym, period="8y", interval="1d", progress=False)
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
                
            if len(df) < 60:
                print("❌ Insufficient data")
                continue

            res = backtester.run_backtest(df, symbol=sym)
            if res.get("total_trades", 0) > 0:
                all_results.append({
                    "Symbol": sym,
                    "Trades": res["total_trades"],
                    "Win Rate %": f"{res['win_rate_pct']}%",
                    "CTC Scratches": res.get("breakeven_trades", 0),
                    "Total PnL %": f"{res['total_pnl_pct']}%",
                    "Avg Win %": f"+{res['avg_win_pct']}%",
                    "Avg Loss %": f"{res['avg_loss_pct']}%",
                    "Expectancy": f"+{res['expectancy_pct_per_trade']}%"
                })
                all_trades.extend(res.get("trades", []))
                print(f"✅ {res['total_trades']} trades | Win: {res['win_rate_pct']}% | PnL: +{res['total_pnl_pct']}%")
            else:
                print("⚠️ 0 triggers")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 80)
    print("📊 8-YEAR INSTITUTIONAL COMPREHENSIVE PERFORMANCE SUMMARY")
    print("=" * 80)
    if all_results:
        summary_df = pd.DataFrame(all_results)
        print(summary_df.to_string(index=False))
        
        total_trades = sum(t["Trades"] for t in all_results)
        total_wins = sum(1 for t in all_trades if t["pnl_pct"] > 0)
        overall_win_rate = round((total_wins / (total_trades + 1e-6)) * 100, 1)
        total_portfolio_pnl = round(sum(t["pnl_pct"] for t in all_trades), 2)
        total_breakevens = sum(1 for t in all_trades if abs(t["pnl_pct"]) <= 0.5)
        
        print("\n" + "-" * 80)
        print(f"🔥 TOTAL PORTFOLIO TRADES  : {total_trades}")
        print(f"🛡️ PROTECTED CTC SCRATCHES : {total_breakevens} (Saved from turning into losses)")
        print(f"🏆 OVERALL WIN RATE        : {overall_win_rate}%")
        print(f"💰 CUMULATIVE BASKET PnL   : +{total_portfolio_pnl}%")
        print("-" * 80)

if __name__ == "__main__":
    main()