"""
ALPHA-RADAR QUANTITATIVE TERMINAL CONFIGURATION
Master parameters, Liquidity Floors, and Risk Limits.
"""
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class RiskParameters:
    # Baseline Volatility & Compression
    ADR_WINDOW: int = 20
    MAX_ADR_CEILING_PCT: float = 15.0      # Eliminates reverse-split penny death traps
    MAX_COIL_RATIO: float = 0.85           # 3-Day Box / 20-Day ADR <= 0.85x
    
    # Microstructure & Traps
    MIN_RVOL_BREAKOUT: float = 1.8         # Minimum volume expansion
    MAX_UPPER_WICK_PCT: float = 18.0       # Rejection shield against operator dumping
    
    # Liquidity Floors (Hard gates)
    MIN_DOLLAR_TURNOVER_US: float = 500_000.0       # $500k / day minimum
    MIN_RUPEE_TURNOVER_IN: float = 15_000_000.0     # ₹1.5 Crore / day minimum

    # Security & Admin Console
    MASTER_ADMIN_PIN: str = "777"
    
    # Paths
    CATALOG_PATH: str = "data/global_master_catalog.parquet"
    LEDGER_PATH: str = "data/private_audit_ledger.parquet"
    SCANS_PATH: str = "data/scans/latest_scans.parquet"

CONFIG = RiskParameters()