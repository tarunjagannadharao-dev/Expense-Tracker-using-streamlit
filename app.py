from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client

CATEGORIES = ["Food & Drinks", "Groceries", "Transport", "Shopping", "Bills & Utilities", "Health", "Entertainment", "Education", "Travel", "Home", "Family", "Other"]
PAYMENTS = ["UPI", "Cash", "Credit Card", "Debit Card", "Bank Transfer", "Other"]

st.set_page_config(page_title="Daily Expense Tracker", page_icon="💸", layout="wide")


def secret(name):
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        return None


def login():
    password = secret("APP_PASSWORD")
    if not password:
        st.error("APP_PASSWORD is missing. Add it under Streamlit Cloud → App settings → Secrets.")
        st.stop()
    if st.session_state.get("authenticated"):
        with st.sidebar:
            if st.button("Log out", use_container_width=True):
                st.session_state.authenticated = False
                st.rerun()
        return
    st.title("💸 Daily Expense Tracker")
    st.subheader("Sign in")
    entered = st.text_input("App password", type="password")
    if st.button("Continue", type="primary"):
        if entered == str(password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()


@st.cache_resource
def supabase_client():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_SECRET_KEY")
    if not url or not key:
        st.error("SUPABASE_URL or SUPABASE_SECRET_KEY is missing from Streamlit Secrets.")
        st.stop()
    return create_client(str(url), str(key))


def load_expenses(client):
    response = (client.table("expenses")
        .select("id, expense_date, amount, category, payment_method, description")
        .order("expense_date", desc=True).order("id", desc=True).execute())
    cols = ["id", "expense_date", "amount", "category", "payment_method", "description"]
    df = pd.DataFrame(response.data or [], columns=cols)
    if not df.empty:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
        df["expense_date"] = pd.to_datetime(df["expense_date"]).dt.date
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["description"] = df["description"].fillna("")
    return df


def get_budget(client):
    result = (client.table("settings").select("setting_value")
        .eq("setting_key", "monthly_budget").limit(1).execute())
    if not result.data:
        set_budget(client, 20000.0)
        return 20000.0
    return float(result.data[0]["setting_value"])


def set_budget(client, value):
    client.table("settings").upsert({
        "setting_key": "monthly_budget", "setting_value": str(float(value))
    }, on_conflict="setting_key").execute()


def rupees(value):
    return f"₹{float(value):,.2f}"


login()
try:
    db = supabase_client()
    df = load_expenses(db)
    budget = get_budget(db)
except Exception as exc:
    st.error("Unable to connect to Supabase or retrieve data.")
    st.caption(f"Technical detail: {exc}")
    st.info("Verify Streamlit Secrets and that the expenses/settings tables exist.")
    st.stop()

st.title("💸 Daily Expense Tracker")