"""
ALPHA-RADAR 4-TIER INSTITUTIONAL BENCHMARK AUDIT
Stress-testing across Large, Mid, Small, and Penny Equities with Dynamic CTC & Trailing SL.
"""
import yfinance as yf
import pandas as pd
from src.backtest.engine import SwingBacktester

TIER_UNIVERSE = {
    "TIER_1_LARGE": [
        "RELIANCE.NS", "TCS.NS", "ICICIBANK.NS", "AAPL", "MSFT"
    ],
    "TIER_2_MID": [
        "DIXON.NS", "BSE.NS", "KAYNES.NS", "POLYCAB.NS", "NVDA", "PLTR"
    ],
    "TIER_3_SMALL": [
        "SHAILY.NS", "NEWGEN.NS", "ZENTEC.NS", "CELH"
    ],
    "TIER_4_PENNY": [
        "SUZLON.NS", "RGTI", "SOUN", "IONQ"
    ]
}

def main():
    print("=" * 85)
    print("🛰️ ALPHA-RADAR 4-TIER GLOBAL QUANTITATIVE AUDIT (5 TO 8 YEARS)")
    print("=" * 85)
    
    backtester = SwingBacktester(slippage_pct=0.15, max_holding_days=25)
    tier_summaries = []
    grand_trades = []

    for tier_name, tickers in TIER_UNIVERSE.items():
        print(f"\n⚡ AUDITING {tier_name} ({len(tickers)} Stocks)...")
        tier_results = []
        
        for sym in tickers:
            print(f"  [*] Processing {sym}...", end=" ", flush=True)
            try:
                df = yf.download(sym, period="8y", interval="1d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                if len(df) < 60:
                    print("❌ Insufficient data")
                    continue
                
                res = backtester.run_backtest(df, symbol=sym)
                if res.get("total_trades", 0) > 0:
                    tier_results.append(res)
                    grand_trades.extend(res.get("trades", []))
                    print(f"✅ {res['total_trades']} trades | Win: {res['win_rate_pct']}% | PnL: +{res['total_pnl_pct']}%")
                else:
                    print("⚠️ 0 triggers")
            except Exception as e:
                print(f"❌ Error: {e}")

        # Tier Analytics
        if tier_results:
            t_trades = sum(r["total_trades"] for r in tier_results)
            t_wins = sum(int(round((r["win_rate_pct"] / 100) * r["total_trades"])) for r in tier_results)
            t_winrate = round((t_wins / (t_trades + 1e-6)) * 100, 1)
            t_pnl = round(sum(r["total_pnl_pct"] for r in tier_results), 2)
            t_scratches = sum(r.get("breakeven_trades", 0) for r in tier_results)
            
            tier_summaries.append({
                "Tier": tier_name,
                "Stocks": len(tier_results),
                "Trades": t_trades,
                "Win Rate %": f"{t_winrate}%",
                "CTC Scratches": t_scratches,
                "Tier PnL %": f"+{t_pnl}%" if t_pnl >= 0 else f"{t_pnl}%"
            })

    # FINAL REPORT CARD
    print("\n" + "=" * 85)
    print("🏆 4-TIER INSTITUTIONAL REPORT CARD")
    print("=" * 85)
    if tier_summaries:
        report_df = pd.DataFrame(tier_summaries)
        print(report_df.to_string(index=False))

        # Overall Grand Portfolio Math
        all_trades_count = len(grand_trades)
        all_wins = sum(1 for t in grand_trades if t["pnl_pct"] > 0)
        overall_wr = round((all_wins / (all_trades_count + 1e-6)) * 100, 1)
        grand_pnl = round(sum(t["pnl_pct"] for t in grand_trades), 2)
        total_scratches = sum(1 for t in grand_trades if abs(t["pnl_pct"]) <= 0.5)

        print("-" * 85)
        print(f"🌐 TOTAL GLOBAL TRADES     : {all_trades_count}")
        print(f"🛡️ TOTAL PROTECTED SCRATCHES: {total_scratches}")
        print(f"🎯 GRAND WIN RATE          : {overall_wr}%")
        print(f"💰 TOTAL PORTFOLIO PnL     : +{grand_pnl}%")
        print("=" * 85)

if __name__ == "__main__":
    main()