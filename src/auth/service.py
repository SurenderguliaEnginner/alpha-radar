"""
ALPHA-RADAR AUTH & PERSISTENT 3-DAY CALENDAR TRIAL ENGINE
Tracks exact calendar signup dates and decreases days remaining every midnight.
"""
import os
import streamlit as st
import pandas as pd
from datetime import date, datetime

TRIALS_DB_PATH = "data/trials_vault.parquet"

class AuthService:
    def __init__(self):
        os.makedirs("data", exist_ok=True)

    def get_or_create_user(self, email: str, name: str = "Trader") -> dict:
        """Loads user and calculates exact calendar days elapsed."""
        now_date = date.today()
        email_clean = email.strip().lower()
        
        user_record = {
            "email": email_clean,
            "name": name,
            "signup_date": str(now_date),
            "tier": "FREE",
            "is_pro": False
        }

        if os.path.exists(TRIALS_DB_PATH):
            try:
                df = pd.read_parquet(TRIALS_DB_PATH)
                match = df[df['email'] == email_clean]
                if not match.empty:
                    row = match.iloc[0].to_dict()
                    user_record["signup_date"] = str(row["signup_date"])[:10]
                    user_record["tier"] = row.get("tier", "FREE")
                    user_record["is_pro"] = bool(row.get("is_pro", False))
                else:
                    df = pd.concat([df, pd.DataFrame([user_record])], ignore_index=True)
                    df.to_parquet(TRIALS_DB_PATH, index=False)
            except Exception:
                pd.DataFrame([user_record]).to_parquet(TRIALS_DB_PATH, index=False)
        else:
            pd.DataFrame([user_record]).to_parquet(TRIALS_DB_PATH, index=False)

        # Calculate exact calendar days elapsed
        try:
            signup_d = datetime.strptime(str(user_record["signup_date"])[:10], "%Y-%m-%d").date()
        except Exception:
            signup_d = now_date

        days_elapsed = (now_date - signup_d).days
        days_remaining = max(0, 3 - days_elapsed)
        is_expired = (days_remaining == 0) and not user_record["is_pro"]

        session_user = {
            "email": email_clean,
            "name": name,
            "tier": "PRO" if user_record["is_pro"] else "FREE",
            "is_pro": user_record["is_pro"],
            "days_remaining": days_remaining,
            "is_expired": is_expired,
            "signup_date": signup_d.strftime("%d %b %Y")
        }
        st.session_state["authenticated_user"] = session_user
        st.query_params["u"] = email_clean  # Persists across browser refreshes!
        return session_user

    def get_current_user(self):
        # Auto-rehydrate if user previously logged in on this browser
        if "authenticated_user" not in st.session_state and "u" in st.query_params:
            return self.get_or_create_user(st.query_params["u"])
        return st.session_state.get("authenticated_user", None)

    def logout(self):
        if "authenticated_user" in st.session_state:
            del st.session_state["authenticated_user"]
        if "u" in st.query_params:
            del st.query_params["u"]

    def upgrade_to_pro(self, email: str = None):
        user = self.get_current_user()
        target_email = email or (user.get("email") if user else None)
        
        if target_email and os.path.exists(TRIALS_DB_PATH):
            try:
                df = pd.read_parquet(TRIALS_DB_PATH)
                df.loc[df['email'] == target_email.strip().lower(), ['tier', 'is_pro']] = ["PRO", True]
                df.to_parquet(TRIALS_DB_PATH, index=False)
            except Exception:
                pass
        
        if user:
            user["tier"] = "PRO"
            user["is_pro"] = True
            user["is_expired"] = False
            user["days_remaining"] = 30

auth_service = AuthService()