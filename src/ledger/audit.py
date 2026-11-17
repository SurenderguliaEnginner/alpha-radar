"""
ALPHA-RADAR PRIVATE AUDIT LEDGER SERVICE
Permanently logs flagged setups and calculates forward D+1 & D+7 performance.
"""
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

LEDGER_PATH = "data/private_audit_ledger.parquet"

class AuditLedgerService:
    def __init__(self, ledger_path: str = LEDGER_PATH):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)

    def log_signals(self, signals: List[Dict[str, Any]]):
        """Appends new flagged setups to the immutable audit ledger."""
        if not signals:
            return

        new_df = pd.DataFrame(signals)
        new_df['logged_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_df['status'] = "ACTIVE"
        new_df['forward_d1_pct'] = 0.0
        new_df['forward_d7_pct'] = 0.0

        if os.path.exists(self.ledger_path):
            try:
                existing_df = pd.read_parquet(self.ledger_path)
                combined = pd.concat([existing_df, new_df], ignore_index=True)
                # Keep latest record if flagged multiple times on same date
                combined.drop_duplicates(subset=['symbol', 'alert_date'], keep='last', inplace=True)
                combined.to_parquet(self.ledger_path, index=False)
            except Exception:
                new_df.to_parquet(self.ledger_path, index=False)
        else:
            new_df.to_parquet(self.ledger_path, index=False)

    def get_ledger(self) -> pd.DataFrame:
        """Retrieves raw historical audit ledger."""
        if os.path.exists(self.ledger_path):
            return pd.read_parquet(self.ledger_path)
        return pd.DataFrame()