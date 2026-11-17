"""
ALPHA-RADAR GLOBAL 8,986 CATALOG VECTORIZED SCANNER
With Non-Equity Purge (Anti-SPAC Shield) and Dollar Liquidity Floor.
"""
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from src.strategy.engine import StrategyEngine
from src.catalyst.resolver import CatalystResolver
from src.ledger.audit import AuditLedgerService

SCANS_OUTPUT_PATH = "data/latest_scans.parquet"
CATALOG_PATH = "data/global_master_catalog.parquet"

def is_junk_ticker(symbol: str) -> bool:
    """Strips US SPAC Units, Warrants, and Preferred shares."""
    sym = symbol.upper()
    # US Warrants, Units, Preferred
    if any(sym.endswith(suffix) for suffix in ["W", "WS", "U", "RT", "P", ".P", "-P", "-U"]):
        return True
    # Indian non-equity junk (bonds, debentures)
    if any(sym.endswith(ind) for ind in [".NCP", ".P", "-GB", ".BO"]):
        return True
    return False

class GlobalMarketScanner:
    def __init__(self, catalog_path: str = CATALOG_PATH, chunk_size: int = 100):
        self.strategy_engine = StrategyEngine()
        self.resolver = CatalystResolver(catalog_path=catalog_path)
        self.ledger_service = AuditLedgerService()
        self.chunk_size = chunk_size
        self.catalog = self._load_universe(catalog_path)

    def _load_universe(self, catalog_path: str) -> pd.DataFrame:
        if os.path.exists(catalog_path):
            try:
                df = pd.read_parquet(catalog_path)
                print(f"[✓] Loaded Master Global Catalog: {len(df)} Equities.")
                return df
            except Exception as e:
                print(f"[!] Error: {e}")
        return pd.DataFrame()

    def run_full_scan(self, max_stocks: int = None) -> List[Dict[str, Any]]:
        all_symbols = self.catalog['symbol'].dropna().unique().tolist()
        
        # 1. NON-EQUITY & SPAC PURGE
        clean_symbols = [s for s in all_symbols if not is_junk_ticker(s)]
        if max_stocks:
            clean_symbols = clean_symbols[:max_stocks]

        total_stocks = len(clean_symbols)
        today_str = datetime.now().strftime("%Y-%m-%d")
        chunks = [clean_symbols[i:i + self.chunk_size] for i in range(0, total_stocks, self.chunk_size)]
        
        print("=" * 80)
        print(f"🛰️ ALPHA-RADAR INSTITUTIONAL SCAN // FILTERING {total_stocks} VERIFIED EQUITIES")
        print(f"[*] Processing {len(chunks)} Parallel Batches ({self.chunk_size} tickers/batch)...")
        print("=" * 80)

        flagged_alerts = []
        metadata_map = self.catalog.set_index('symbol').to_dict(orient='index') if 'symbol' in self.catalog.columns else {}

        for idx, chunk in enumerate(chunks, 1):
            print(f"[*] Batch {idx}/{len(chunks)} ({len(chunk)} tickers)...", end=" ", flush=True)
            try:
                batch_data = yf.download(
                    chunk, 
                    period="60d", 
                    interval="1d", 
                    group_by="ticker", 
                    progress=False, 
                    threads=True
                )
            except Exception:
                print("❌ Skipped")
                continue

            batch_flagged = 0
            for sym in chunk:
                try:
                    df_sym = batch_data if len(chunk) == 1 else batch_data[sym].dropna()
                    if isinstance(df_sym.columns, pd.MultiIndex):
                        df_sym.columns = df_sym.columns.get_level_values(0)

                    if len(df_sym) < 45:
                        continue

                    # 2. HARD LIQUIDITY FLOOR SHIELD
                    is_india = sym.endswith(".NS")
                    turnover_20d = float((df_sym['Close'] * df_sym['Volume']).rolling(20).mean().iloc[-2])
                    min_turnover = 15_000_000.0 if is_india else 500_000.0  # ₹1.5 Cr in IN / $500k in US
                    
                    if turnover_20d < min_turnover:
                        continue  # KILLS ILLIQUID TRAPS AND FAKE SPACS INSTANTLY!

                    # Metadata & Catalyst
                    meta = metadata_map.get(sym, {})
                    c_name = meta.get("name", sym)
                    m_cap = float(meta.get("market_cap_cr", 5000.0))
                    cat_info = self.resolver.fetch_live_catalyst(sym)

                    # Strategy Evaluation
                    signal = self.strategy_engine.evaluate_ticker(
                        df_sym,
                        symbol=sym,
                        market_cap_cr=m_cap,
                        is_india=is_india,
                        catalyst_headline=cat_info['headline']
                    )

                    if signal and signal.action == "BUY":
                        vol_sma20 = float(df_sym['Volume'].rolling(20).mean().iloc[-2])
                        rvol = round(float(df_sym['Volume'].iloc[-1]) / (vol_sma20 + 1e-6), 1)

                        prior_high = float(df_sym['High'].iloc[-4:-1].max())
                        prior_low = float(df_sym['Low'].iloc[-4:-1].min())
                        daily_ranges = ((df_sym['High'] - df_sym['Low']) / df_sym['Low']) * 100
                        adr_20 = float(daily_ranges.rolling(20).mean().iloc[-2])
                        coil = round(((prior_high - prior_low) / (prior_low + 1e-6) * 100) / (adr_20 + 1e-6), 2)

                        c_range = float(df_sym['High'].iloc[-1] - df_sym['Low'].iloc[-1])
                        u_wick = float(df_sym['High'].iloc[-1] - max(df_sym['Open'].iloc[-1], df_sym['Close'].iloc[-1]))
                        u_wick_pct = round((u_wick / (c_range + 1e-6)) * 100, 1)

                        alert_dict = {
                            "symbol": signal.symbol,
                            "name": c_name,
                            "tier": signal.tier,
                            "strategy": signal.strategy_name,
                            "alert_price": round(signal.entry_price, 2),
                            "sl": round(signal.stop_loss, 2),
                            "target": round(signal.target_price, 2),
                            "rr": f"{signal.risk_reward_ratio}R",
                            "rvol": f"{rvol}x",
                            "coil": f"{coil}x",
                            "wick": f"{u_wick_pct}%",
                            "score": signal.alpha_score,
                            "catalyst": f"{signal.catalyst_tag}: {cat_info['headline']}",
                            "reason": signal.reason,
                            "alert_date": today_str
                        }
                        flagged_alerts.append(alert_dict)
                        batch_flagged += 1

                except Exception:
                    continue

            print(f"✅ ({batch_flagged} real alerts)")

        flagged_alerts.sort(key=lambda x: x["score"], reverse=True)

        print("\n" + "=" * 80)
        print(f"🏆 CLEAN GLOBAL SCAN COMPLETE: FLAGGED {len(flagged_alerts)} VERIFIED ALERTS")
        print("=" * 80)

        # Print all flagged alerts cleanly
        for i, a in enumerate(flagged_alerts, 1):
            curr = "₹" if ".NS" in a["symbol"] else "$"
            print(f" #{i} [{a['symbol']}] {a['name']} ({a['tier']})")
            print(f"    Alert: {curr}{a['alert_price']} | SL: {curr}{a['sl']} | Target: {curr}{a['target']} ({a['rr']}) | Score: {a['score']}/100")
            print(f"    Reason: {a['reason']}\n")

        if flagged_alerts:
            os.makedirs("data", exist_ok=True)
            pd.DataFrame(flagged_alerts).to_parquet(SCANS_OUTPUT_PATH, index=False)
            self.ledger_service.log_signals(flagged_alerts)

        return flagged_alerts

if __name__ == "__main__":
    scanner = GlobalMarketScanner()
    scanner.run_full_scan()

# Alias for web interface compatibility
MarketScanner = GlobalMarketScanner