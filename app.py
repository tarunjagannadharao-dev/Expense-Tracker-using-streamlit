import sqlite3
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).resolve().parent / "expenses.db"
CATEGORIES = ["Food & Drinks", "Groceries", "Transport", "Shopping", "Bills & Utilities", "Health", "Entertainment", "Education", "Travel", "Home", "Family", "Other"]
PAYMENTS = ["UPI", "Cash", "Credit Card", "Debit Card", "Bank Transfer", "Other"]
st.set_page_config(page_title="Daily Expense Tracker", page_icon="💸", layout="wide")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0), category TEXT NOT NULL,
            payment_method TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL)""")
        c.execute("CREATE TABLE IF NOT EXISTS settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")
        c.execute("INSERT OR IGNORE INTO settings VALUES ('monthly_budget', '20000')")

def budget_get():
    with conn() as c:
        r = c.execute("SELECT setting_value FROM settings WHERE setting_key='monthly_budget'").fetchone()
    return float(r[0]) if r else 20000.0

def budget_set(v):
    with conn() as c:
        c.execute("INSERT INTO settings VALUES('monthly_budget', ?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value", (str(float(v)),))

def load():
    with conn() as c:
        d = pd.read_sql_query("SELECT id, expense_date, amount, category, payment_method, description FROM expenses ORDER BY expense_date DESC, id DESC", c)
    if not d.empty:
        d["expense_date"] = pd.to_datetime(d["expense_date"]).dt.date
        d["amount"] = pd.to_numeric(d["amount"], errors="coerce").fillna(0.0)
    return d

def rupees(v):
    return f"₹{float(v):,.2f}"

init()
st.title("💸 Daily Expense Tracker")
st.caption("Record daily spending, review trends, and monitor your monthly budget. Data is stored locally on this computer.")

with st.sidebar:
    st.header("Add expense")
    with st.form("add", clear_on_submit=True):
        d = st.date_input("Date", value=date.today(), max_value=date.today())
        a = st.number_input("Amount (₹)", min_value=0.01, value=100.0, step=10.0)
        cat = st.selectbox("Category", CATEGORIES)
        pay = st.selectbox("Payment method", PAYMENTS)
        desc = st.text_input("Description / note", placeholder="e.g. lunch, cab, groceries")
        add = st.form_submit_button("Save expense", type="primary", use_container_width=True)
    if add:
        with conn() as c:
            c.execute("INSERT INTO expenses(expense_date,amount,category,payment_method,description,created_at) VALUES(?,?,?,?,?,?)",
                      (d.isoformat(), float(a), cat, pay, desc.strip(), datetime.now().isoformat(timespec="seconds")))
        st.success("Expense saved.")
        st.rerun()
    st.divider()
    st.subheader("Monthly budget")
    with st.form("budget"):
        b = st.number_input("Budget (₹)", min_value=0.0, value=budget_get(), step=500.0)
        save_b = st.form_submit_button("Update budget", use_container_width=True)
    if save_b:
        budget_set(b)
        st.success("Budget updated.")
        st.rerun()

df = load()
today = date.today()
month = df[df.expense_date.apply(lambda x: x.year == today.year and x.month == today.month)] if not df.empty else df.copy()
today_df = df[df.expense_date == today] if not df.empty else df.copy()
today_total = float(today_df.amount.sum()) if not today_df.empty else 0.0
month_total = float(month.amount.sum()) if not month.empty else 0.0
b = budget_get()
remaining = b - month_total

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spent today", rupees(today_total))
c2.metric("Spent this month", rupees(month_total))
c3.metric("Budget remaining", rupees(remaining), delta=f"{month_total / b:.1%} used" if b > 0 else "No budget set", delta_color="inverse")
c4.metric("Entries this month", f"{len(month):,}")
if b > 0:
    st.progress(min(month_total / b, 1.0), text=f"Monthly budget used: {month_total / b:.1%}")
    if month_total > b:
        st.warning(f"Monthly budget exceeded by {rupees(month_total-b)}.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🧾 Expense history", "✏️ Edit / delete"])
with tab1:
    left, right = st.columns(2)
    with left:
        st.subheader("Spending by category — this month")
        if month.empty:
            st.info("No expenses recorded this month yet.")
        else:
            g = month.groupby("category", as_index=False).amount.sum().sort_values("amount", ascending=False)
            st.plotly_chart(px.pie(g, names="category", values="amount", hole=0.45), use_container_width=True)
    with right:
        st.subheader("Daily spending — this month")
        if month.empty:
            st.info("Add an expense to see the daily trend.")
        else:
            g = month.groupby("expense_date", as_index=False).amount.sum().sort_values("expense_date")
            g["day"] = g.expense_date.astype(str)
            st.plotly_chart(px.bar(g, x="day", y="amount", labels={"day":"Date","amount":"Amount (₹)"}), use_container_width=True)
    st.subheader("Recent expenses")
    if df.empty:
        st.info("Add your first expense using the sidebar.")
    else:
        r = df.head(10).copy()
        r["expense_date"] = r.expense_date.astype(str)
        r["amount"] = r.amount.map(rupees)
        st.dataframe(r.rename(columns={"id":"ID","expense_date":"Date","amount":"Amount","category":"Category","payment_method":"Payment method","description":"Description"}), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Search and filter")
    if df.empty:
        st.info("No expenses saved yet.")
    else:
        min_d, max_d = min(df.expense_date), max(df.expense_date)
        f1, f2, f3 = st.columns(3)
        start = f1.date_input("From", value=max(min_d, today.replace(day=1)), key="from_date")
        end = f2.date_input("To", value=max_d, key="to_date")
        cats = f3.multiselect("Categories", CATEGORIES, key="filter_categories")
        filt = df[(df.expense_date >= start) & (df.expense_date <= end)] if start <= end else df.iloc[0:0]
        if cats:
            filt = filt[filt.category.isin(cats)]
        st.write(f"**{len(filt)} entries · Total: {rupees(filt.amount.sum())}**")
        out = filt.copy()
        out["expense_date"] = out.expense_date.astype(str)
        st.dataframe(out.rename(columns={"id":"ID","expense_date":"Date","amount":"Amount (₹)","category":"Category","payment_method":"Payment method","description":"Description"}), use_container_width=True, hide_index=True)
        st.download_button("Download CSV", filt.to_csv(index=False).encode("utf-8"), "expenses.csv", "text/csv")

with tab3:
    st.subheader("Edit or delete an expense")
    if df.empty:
        st.info("No expenses to edit.")
    else:
        labels = {f"#{int(r.id)} · {r.expense_date} · {r.category} · {rupees(r.amount)} · {str(r.description)[:30]}": int(r.id) for r in df.itertuples()}
        label = st.selectbox("Select entry", list(labels.keys()))
        eid = labels[label]
        r = df[df.id == eid].iloc[0]
        with st.form("edit"):
            ed = st.date_input("Date", value=r.expense_date, key="ed")
            ea = st.number_input("Amount (₹)", min_value=0.01, value=float(r.amount), step=10.0, key="ea")
            ec = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(r.category) if r.category in CATEGORIES else 0, key="ec")
            ep = st.selectbox("Payment method", PAYMENTS, index=PAYMENTS.index(r.payment_method) if r.payment_method in PAYMENTS else 0, key="ep")
            et = st.text_input("Description", value=str(r.description), key="et")
            update = st.form_submit_button("Save changes", type="primary")
        if update:
            with conn() as c:
                c.execute("UPDATE expenses SET expense_date=?, amount=?, category=?, payment_method=?, description=? WHERE id=?", (ed.isoformat(), float(ea), ec, ep, et.strip(), eid))
            st.success("Expense updated.")
            st.rerun()
        confirm = st.checkbox("Confirm permanent deletion")
        if st.button("Delete selected expense", disabled=not confirm):
            with conn() as c:
                c.execute("DELETE FROM expenses WHERE id=?", (eid,))
            st.success("Expense deleted.")
            st.rerun()

st.caption("Local storage: expenses.db beside app.py. Back up this file periodically. This app does not sync across devices.")
