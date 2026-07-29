import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── App Constants ──────────────────────────────────────────────────────────
AFFILIATE_ID       = "creatormoneym-20"
MIN_DISCOUNT_PCT   = 20.0    # minimum % discount to flag as a deal
STRONG_DEAL_PCT    = 40.0    # % discount to flag as a strong deal
MAX_DEALS_SHOWN    = 20      # max deals to show in the UI


def _get(key: str, default: str = "") -> str:
    """Read a secret from st.secrets, falling back to environment variables."""
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.environ.get(key, default)


OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
BOT_TOKEN          = _get("BOT_TOKEN")
CHAT_ID            = _get("CHAT_ID")
SUPABASE_URL       = _get("SUPABASE_URL")
SUPABASE_KEY       = _get("SUPABASE_KEY")
