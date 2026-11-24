"""
ALPHA-RADAR AUTOMATIC CATALOG INGESTION & IPO SYNC ENGINE
Automatically fetches newly listed NSE India and US equities and appends to the master catalog.
"""
import sys
import os
import requests
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

CATALOG_PATH = "data/global_master_catalog.parquet"

# Official exchange directories
NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

class CatalogAutoIngestion:
    def __init__(self, catalog_path: str = CATALOG_PATH):
        self.catalog_path = catalog_path
        os.makedirs("data", exist_ok=True)

    def load_existing_catalog(self) -> pd.DataFrame:
        if os.path.exists(self.catalog_path):
            try:
                return pd.read_parquet(self.catalog_path)
            except Exception:
                pass
        return pd.DataFrame(columns=["symbol", "name", "market_cap_cr", "market", "tier"])

    def fetch_new_nse_listings(self) -> list:
        """Fetches active Indian equities directly from NSE official master list."""
        headers = {"User-Agent": "Mozilla/5.0"}
        print("[*] Checking NSE official listings for new IPOs / stocks...", end=" ", flush=True)
        try:
            res = requests.get(NSE_EQUITY_URL, headers=headers, timeout=15)
            if res.status_code == 200:
                from io import StringIO
                df_nse = pd.read_csv(StringIO(res.text))
                new_nse = []
                for _, row in df_nse.iterrows():
                    sym = f"{str(row.get('SYMBOL', '')).strip()}.NS"
                    name = str(row.get('NAME OF COMPANY', sym))
                    new_nse.append({
                        "symbol": sym,
                        "name": name,
                        "market_cap_cr": 5000.0,
                        "market": "INDIA",
                        "tier": "TIER_2_MID"
                    })
                print(f"✅ Found {len(new_nse)} active NSE equities.")
                return new_nse
        except Exception as e:
            print(f"⚠️ NSE fetch skipped: {e}")
        return []

    def fetch_new_sec_listings(self) -> list:
        """Fetches active US primary equities from SEC EDGAR master directory."""
        headers = {"User-Agent": "AlphaRadarBot/1.0 (quant@alpha-radar.io)"}
        print("[*] Checking US SEC directory for new listings...", end=" ", flush=True)
        try:
            res = requests.get(SEC_TICKERS_URL, headers=headers, timeout=15)
            if res.status_code == 200:
                sec_json = res.json()
                new_us = []
                for _, item in sec_json.items():
                    sym = str(item.get("ticker", "")).strip().upper()
                    name = str(item.get("title", sym))
                    if not any(sym.endswith(sfx) for sfx in ["W", "WS", "U", "P", "-P"]):
                        new_us.append({
                            "symbol": sym,
                            "name": name,
                            "market_cap_cr": 5000.0,
                            "market": "US",
                            "tier": "TIER_2_MID"
                        })
                print(f"✅ Found {len(new_us)} active US equities.")
                return new_us
        except Exception as e:
            print(f"⚠️ US fetch skipped: {e}")
        return []

    def sync_and_update(self):
        existing_df = self.load_existing_catalog()
        print(f"[*] Current Catalog Count: {len(existing_df)} Equities.")

        new_nse = self.fetch_new_nse_listings()
        new_us = self.fetch_new_sec_listings()

        all_incoming = new_nse + new_us
        if not all_incoming:
            print("[!] No new incoming data received.")
            return

        incoming_df = pd.DataFrame(all_incoming)

        # Merge with existing, dropping duplicates by symbol
        if not existing_df.empty:
            merged = pd.concat([existing_df, incoming_df], ignore_index=True)
            merged.drop_duplicates(subset=["symbol"], keep="first", inplace=True)
        else:
            merged = incoming_df.drop_duplicates(subset=["symbol"], keep="first")

        merged.to_parquet(self.catalog_path, index=False)
        print("=" * 75)
        print(f"🏆 CATALOG SYNC COMPLETE // TOTAL EQUITIES IN VAULT: {len(merged)}")
        print(f"[✓] Successfully saved to {self.catalog_path} (Strictly local to this laptop).")
        print("=" * 75)

if __name__ == "__main__":
    syncer = CatalogAutoIngestion()
    syncer.sync_and_update()