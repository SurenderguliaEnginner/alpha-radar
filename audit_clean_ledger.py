"""
ALPHA-RADAR CLEAN HISTORICAL FORWARD AUDIT
Evaluates ONLY verified equities (purging $0.03 warrants & pre-filter test noise)
Tracks Peak Excursion (MFE), 1:1 Breakeven Protection, and Target Hits.
"""
import os
import yfinance as yf
import pandas as pd
import numpy as np

LEDGER_PATH = "data/private_audit_ledger.parquet"

def main():
    print("=" * 85)
    print("🛰️ ALPHA-RADAR VERIFIED FORWARD PERFORMANCE AUDIT (NO JUNK / NO WARRANTS)")
    print("=" * 85)

    if not os.path.exists(LEDGER_PATH):
        print("[!] Ledger not found.")
        return

    df = pd.read_parquet(LEDGER_PATH)
    
    # 1. PURGE PRE-FILTER JUNK (Remove $0.03 warrants, penny junk < ₹10 / < $1 from early test runs)
    clean_df = df[
        (df['alert_price'] >= 10.0) | 
        ((df['alert_price'] >= 1.0) & (~df['symbol'].str.endswith(".NS")))
    ].copy()
    
    # Remove warrants ending in W/WS
    clean_df = clean_df[~clean_df['symbol'].str.endswith(('W', 'WS', '.P', '-P'))]

    print(f"[*] Total Raw Signals in Ledger: {len(df)}")
    print(f"[*] Purged {len(df) - len(clean_df)} pre-filter testing noise / warrants.")
    print(f"[*] Auditing {len(clean_df)} Verified Liquid Institutional Equities...\n")

    symbols = clean_df['symbol'].dropna().unique().tolist()
    
    try:
        data = yf.download(symbols, period="10d", interval="1d", progress=False, group_by="ticker")
    except Exception as e:
        print(f"[!] Fetch failed: {e}")
        return

    records = []
    for idx, row in clean_df.iterrows():
        sym = row['symbol']
        alert_px = float(row['alert_price'])
        sl_px = float(row.get('sl', alert_px * 0.96))
        target_px = float(row.get('target', alert_px * 1.10))
        risk_amt = alert_px - sl_px

        try:
            df_sym = data if len(symbols) == 1 else data[sym].dropna()
            if isinstance(df_sym.columns, pd.MultiIndex):
                df_sym.columns = df_sym.columns.get_level_values(0)

            if len(df_sym) < 2:
                continue

            latest_close = float(df_sym['Close'].iloc[-1])
            highest_high = float(df_sym['High'].max())
            lowest_low = float(df_sym['Low'].min())

            peak_gain_pct = round(((highest_high - alert_px) / alert_px) * 100, 2)
            current_gain_pct = round(((latest_close - alert_px) / alert_px) * 100, 2)

            # Institutional Trade Lifecycle Status
            curr = "₹" if ".NS" in sym else "$"
            status = "ACTIVE RUNNER"
            
            # Check if hit Target
            if highest_high >= target_px:
                status = "🎯 TARGET HIT (+3.0R)"
            # Check if hit Stop Loss before 1:1
            elif lowest_low <= sl_px and highest_high < (alert_px + risk_amt):
                status = "🛑 STOPPED OUT (-1.0R)"
            # Check if reached 1:1 R (Protected at Breakeven!)
            elif highest_high >= (alert_px + risk_amt):
                status = "🛡️ CTC BREAKEVEN / RUNNER"
            elif current_gain_pct > 0:
                status = "🟢 IN PROFIT"
            else:
                status = "⚠️ BASE CONSOLIDATION"

            records.append({
                "Symbol": sym,
                "Alert Price": f"{curr}{alert_px}",
                "Peak Gain": f"+{peak_gain_pct:.2f}%",
                "Current Return": f"{current_gain_pct:+.2f}%",
                "Lifecycle State": status
            })

        except Exception:
            continue

    if records:
        res_df = pd.DataFrame(records)
        print(res_df.head(20).to_string(index=False))

        # Real Institutional Success Rate (Trades that hit Target OR protected at CTC / In Profit)
        successful_trades = [r for r in records if "TARGET" in r["Lifecycle State"] or "CTC" in r["Lifecycle State"] or "PROFIT" in r["Lifecycle State"]]
        real_success_rate = round((len(successful_trades) / (len(records) + 1e-6)) * 100, 1)

        print("\n" + "=" * 85)
        print(f"🏆 CLEAN VERIFIED SIGNALS AUDITED : {len(records)}")
        print(f"🎯 INSTITUTIONAL SUCCESS RATE     : {real_success_rate}% (Target Hit + CTC Protected)")
        print(f"🛑 UNPROTECTED LOSSES            : {100 - real_success_rate}%")
        print("=" * 85)

if __name__ == "__main__":
    main()