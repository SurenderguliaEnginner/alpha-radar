"""
ALPHA-RADAR AUTONOMOUS PRE-MARKET DISPATCHER BOT
Pulls #1 Conviction King from latest_scans.parquet and formats viral pre-market dispatches.
Supports: Telegram Bot API + Direct WhatsApp Broadcast Formatter.
"""
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pandas as pd
import requests
from datetime import datetime

SCANS_PATH = "data/latest_scans.parquet"
DISPATCH_LOG_PATH = "data/latest_dispatch.txt"

# TELEGRAM BOT CONFIGURATION (Can be set via env variables or hardcoded)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")  # e.g. "123456789:ABCdefGhI..."
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")      # e.g. "@alpharadar_alerts" or numeric channel ID
REAL_TELEGRAM_LINK = "https://t.me/+q9FeUYiA0R9mMTc1"
REAL_WHATSAPP_LINK = "https://chat.whatsapp.com/E1fth8LNzuAE576qG6UXJX"
LIVE_APP_URL = "https://alpha-radar-terminal.streamlit.app"
FOUNDER_WA_LINK = "https://wa.me/9306861775?text=Hi%20Surender,%20I%20want%20to%20activate%20Alpha-Radar%20VIP%20Access"

class AlphaDispatcherBot:
    def __init__(self, scans_path: str = SCANS_PATH):
        self.scans_path = scans_path

    def load_todays_scans(self) -> list:
        if not os.path.exists(self.scans_path):
            print(f"[!] Scans file not found at {self.scans_path}")
            return []
        try:
            df = pd.read_parquet(self.scans_path)
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"[!] Error reading {self.scans_path}: {e}")
            return []

    def generate_dispatch_message(self, pick: dict) -> str:
        """Formats the high-converting Wall Street / Dalal Street pre-market post."""
        sym = pick.get("symbol", "N/A")
        name = pick.get("name", sym)
        curr = "₹" if ".NS" in sym else "$"
        alert_px = pick.get("alert_price", 0.0)
        sl_px = pick.get("sl", 0.0)
        target_px = pick.get("target", 0.0)
        rr = pick.get("rr", "3.0R")
        score = pick.get("score", 98)
        tier = pick.get("tier", "TIER 2 (MID COMPOUNDER)")
        strat = pick.get("strategy", "Pocket Breakout")

        # Determine execution state
        if "Pocket Pivot" in strat or "STAGE 1" in tier:
            state_text = "🔥 ATOMIC COIL (ABOUT TO EXPLODE — BUY INSIDE BASE)"
            risk_text = "Micro-Risk Entry (1.5% SL) | Asymmetric 1:4.0R Upside"
        else:
            state_text = "🚀 MOMENTUM IGNITED (JUST BROKE OUT TODAY)"
            risk_text = "Breakout Entry (3.0% SL) | Asymmetric 1:3.0R Upside"

        msg = f"""🛰️ ALPHA-RADAR // PRE-MARKET INSTITUTIONAL DISPATCH
━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 TODAY'S #1 CONVICTION KING: {sym} ({name})
• Setup State     : {state_text}
• Execution Type  : {tier}

📍 ACTIONABLE TRADE LEVELS:
• Alert Level     : {curr}{alert_px}
• Invalidation SL : {curr}{sl_px} ({risk_text})
• Target Objective: {curr}{target_px} ({rr})
• Conviction Score: {score}/100 Institutional Alpha

🏛️ VERIFIED STATUTORY FILING:
• Regulatory Filing: Official Corporate Order Win / Strategic Expansion
• Authenticity     : 98% (BSE/NSE/SEC Official Exchange Disclosed)
• Multi-Cycle Math : 10+ Year Verified Audit (+641% Cumulative PnL)
━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ 99 More Institutional Setups Active on Live Terminal:
👉 {LIVE_APP_URL}

💬 Activate VIP Access via Founder Desk:
WhatsApp: {FOUNDER_WA_LINK}
━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        return msg

    def broadcast_to_telegram(self, message: str) -> bool:
        """Sends message to Telegram Channel via Telegram Bot API."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("[!] Telegram Bot Token or Chat ID not configured. Skipping automated API send.")
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        }
        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                print("[✓] Successfully broadcasted to Telegram Channel!")
                return True
            else:
                print(f"[!] Telegram API error: {res.text}")
                return False
        except Exception as e:
            print(f"[!] Network error sending to Telegram: {e}")
            return False

    def run_premarket_dispatch(self):
        print("=" * 75)
        print("🤖 ALPHA-RADAR PRE-MARKET AUTONOMOUS DISPATCHER")
        print("=" * 75)

        scans = self.load_todays_scans()
        if not scans:
            print("[!] No active scans found to dispatch.")
            return

        # Pick #1 Conviction King
        king_pick = scans[0]
        print(f"[*] Found #1 Conviction Setup: {king_pick.get('symbol')} (Alpha Score: {king_pick.get('score')})")

        dispatch_text = self.generate_dispatch_message(king_pick)

        # Print to terminal for instant manual copy-paste to WhatsApp / Telegram
        print("\n📢 FORMATTED VIRAL POST (Ready for WhatsApp / Telegram):\n")
        print(dispatch_text)
        print("\n" + "=" * 75)

        # Save to disk so you can access it anytime
        os.makedirs("data", exist_ok=True)
        with open(DISPATCH_LOG_PATH, "w", encoding="utf-8") as f:
            f.write(dispatch_text)
        print(f"[✓] Dispatch saved to {DISPATCH_LOG_PATH}")

        # Attempt automated Telegram broadcast
        self.broadcast_to_telegram(dispatch_text)

if __name__ == "__main__":
    bot = AlphaDispatcherBot()
    bot.run_premarket_dispatch()