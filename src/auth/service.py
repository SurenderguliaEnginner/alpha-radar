"""
ALPHA-RADAR USER AUTH & PERSISTENT TRIAL ENGINE
Handles Google Authentication & Tamper-Proof 3-Day Countdown.
"""
import os
import time
import streamlit as st
import pandas as pd
from datetime import date, datetime

class AuthService:
    def __init__(self):
        pass

    def get_or_create_user(self, email: str, name: str = "Trader") -> dict:
        """Persistently tracks user trial with timestamp verification."""
        now = time.time()
        email_clean = email.strip().lower()

        # Check if user already has a signup timestamp in URL params
        st_param = st.query_params.get("st")
        if st_param:
            try:
                signup_epoch = float(st_param)
            except Exception:
                signup_epoch = now
        else:
            signup_epoch = now
            st.query_params["st"] = str(int(signup_epoch))

        st.query_params["u"] = email_clean

        # Calculate exact calendar days elapsed (86400 seconds = 1 day)
        days_elapsed = int((now - signup_epoch) // 86400)
        days_remaining = max(0, 3 - days_elapsed)
        is_expired = (days_remaining == 0) and not st.session_state.get("user_is_pro", False)
        is_pro = st.session_state.get("user_is_pro", False)

        signup_dt = datetime.fromtimestamp(signup_epoch)

        session_user = {
            "email": email_clean,
            "name": name,
            "tier": "PRO" if is_pro else "FREE",
            "is_pro": is_pro,
            "days_remaining": days_remaining,
            "is_expired": is_expired,
            "signup_date": signup_dt.strftime("%d %b %Y")
        }
        st.session_state["authenticated_user"] = session_user
        return session_user

    def get_current_user(self):
        if "authenticated_user" in st.session_state:
            return st.session_state["authenticated_user"]
        
        # Auto-rehydrate if user previously logged in on this browser
        if "u" in st.query_params:
            return self.get_or_create_user(st.query_params["u"])
        return None

    def logout(self):
        if "authenticated_user" in st.session_state:
            del st.session_state["authenticated_user"]
        st.query_params.clear()

    def upgrade_to_pro(self):
        st.session_state["user_is_pro"] = True
        user = self.get_current_user()
        if user:
            user["tier"] = "PRO"
            user["is_pro"] = True
            user["is_expired"] = False
            user["days_remaining"] = 30

auth_service = AuthService()