"""
ALPHA-RADAR INSTITUTIONAL SECURITY & ANTI-SCRAPING SHIELD
Handles Data Sanitization, Circuit Traps, and Server-Side Entitlements.
"""
from typing import List, Dict, Any

def sanitize_alerts_for_user(alerts: List[Dict[str, Any]], is_pro_user: bool = False) -> List[Dict[str, Any]]:
    """
    CRITICAL SECURITY SHIELD:
    Never transmits locked premium alerts to non-paying users.
    Prevents Inspect-Element (F12) DOM-scraping attacks.
    """
    if is_pro_user:
        return alerts

    # Free Users only receive Top 3 alerts from the server
    sanitized = []
    for a in alerts[:3]:
        sanitized.append(a)
        
    return sanitized

def is_circuit_locked(df) -> bool:
    """
    Detects if an equity is locked in an Upper Circuit.
    Prevents flagging trades where retail buyers cannot execute.
    """
    if len(df) < 2:
        return False
    last = df.iloc[-1]
    # If High == Low and day range is 0 with massive gap, or close == high at 5%, 10%, 20% limits
    day_gain = (last['Close'] - last['Open']) / (last['Open'] + 1e-6)
    is_flat_candle = (last['High'] == last['Low']) or (last['Close'] == last['High'] and day_gain >= 0.048)
    return bool(is_flat_candle and last['Volume'] < df['Volume'].rolling(20).mean().iloc[-2] * 0.2)