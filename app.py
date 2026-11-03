            st.rerun()
        except Exception as exc:
            st.error(f"Could not update budget: {exc}")

today = date.today()
month = df[df.expense_date.apply(lambda x: x.year == today.year and x.month == today.month)] if not df.empty else df.copy()
today_df = df[df.expense_date == today] if not df.empty else df.copy()
today_total = float(today_df.amount.sum()) if not today_df.empty else 0.0
month_total = float(month.amount.sum()) if not month.empty else 0.0
remaining = budget - month_total

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spent today", rupees(today_total))
c2.metric("Spent this month", rupees(month_total))
c3.metric("Budget remaining", rupees(remaining),
          delta=f"{month_total / budget:.1%} used" if budget > 0 else "No budget set",
          delta_color="inverse")
c4.metric("Entries this month", f"{len(month):,}")
if budget > 0:
    st.progress(min(month_total / budget, 1.0), text=f"Monthly budget used: {month_total / budget:.1%}")
    if month_total > budget:
        st.warning(f"Monthly budget exceeded by {rupees(month_total - budget)}.")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🧾 Expense history", "✏️ Edit / delete"])
with tab1:
    left, right = st.columns(2)
    with left:
        st.subheader("Spending by category — this month")
        if month.empty:
            st.info("No expenses recorded this month yet.")
        else:
            grouped = month.groupby("category", as_index=False).amount.sum().sort_values("amount", ascending=False)
            st.plotly_chart(px.pie(grouped, names="category", values="amount", hole=0.45), use_container_width=True)
    with right:
        st.subheader("Daily spending — this month")
        if month.empty:
            st.info("Add an expense to see the daily trend.")
        else:
            grouped = month.groupby("expense_date", as_index=False).amount.sum().sort_values("expense_date")
            grouped["day"] = grouped.expense_date.astype(str)
            st.plotly_chart(px.bar(grouped, x="day", y="amount",
                labels={"day": "Date", "amount": "Amount (₹)"}), use_container_width=True)
    st.subheader("Recent expenses")
    if df.empty:
        st.info("Add your first expense using the sidebar.")
    else:
        recent = df.head(10).copy()
        recent["expense_date"] = recent.expense_date.astype(str)
        recent["amount"] = recent.amount.map(rupees)
        st.dataframe(recent.rename(columns={
            "id": "ID", "expense_date": "Date", "amount": "Amount",
            "category": "Category", "payment_method": "Payment method",
            "description": "Description"
        }), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Search and filter")
    if df.empty:
        st.info("No expenses saved yet.")
    else:
        min_date, max_date = min(df.expense_date), max(df.expense_date)
        f1, f2, f3 = st.columns(3)
        start = f1.date_input("From", value=max(min_date, today.replace(day=1)), key="from_date")
        end = f2.date_input("To", value=max_date, key="to_date")
        cats = f3.multiselect("Categories", CATEGORIES, key="filter_categories")
        filtered = df[(df.expense_date >= start) & (df.expense_date <= end)] if start <= end else df.iloc[0:0]
        if cats:
            filtered = filtered[filtered.category.isin(cats)]
        st.write(f"**{len(filtered)} entries · Total: {rupees(filtered.amount.sum())}**")
        export = filtered.copy()
        export["expense_date"] = export.expense_date.astype(str)
        st.dataframe(export.rename(columns={
            "id": "ID", "expense_date": "Date", "amount": "Amount (₹)",
            "category": "Category", "payment_method": "Payment method",
            "description": "Description"
        }), use_container_width=True, hide_index=True)
        st.download_button("Download CSV", export.to_csv(index=False).encode("utf-8"),
                           "expenses.csv", "text/csv")

with tab3:
    st.subheader("Edit or delete an expense")
    if df.empty:
        st.info("No expenses to edit.")
    else:
        labels = {
            f"#{int(r.id)} · {r.expense_date} · {r.category} · {rupees(r.amount)} · {str(r.description)[:30]}": int(r.id)
            for r in df.itertuples()
        }
        label = st.selectbox("Select entry", list(labels.keys()))
        expense_id = labels[label]
        row = df[df.id == expense_id].iloc[0]
        with st.form("edit"):
            edit_date = st.date_input("Date", value=row.expense_date, key="edit_date")
            edit_amount = st.number_input("Amount (₹)", min_value=0.01, value=float(row.amount), step=10.0, key="edit_amount")
            edit_category = st.selectbox("Category", CATEGORIES,
                index=CATEGORIES.index(row.category) if row.category in CATEGORIES else 0, key="edit_category")
            edit_payment = st.selectbox("Payment method", PAYMENTS,
                index=PAYMENTS.index(row.payment_method) if row.payment_method in PAYMENTS else 0, key="edit_payment")
            edit_description = st.text_input("Description", value=str(row.description), key="edit_description")
            update = st.form_submit_button("Save changes", type="primary")
        if update:
            try:
                db.table("expenses").update({
                    "expense_date": edit_date.isoformat(), "amount": float(edit_amount),
                    "category": edit_category, "payment_method": edit_payment,
                    "description": edit_description.strip()
                }).eq("id", expense_id).execute()
                st.success("Expense updated.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not update expense: {exc}")

        confirm = st.checkbox("Confirm permanent deletion")
        if st.button("Delete selected expense", disabled=not confirm):
            try:
                db.table("expenses").delete().eq("id", expense_id).execute()
                st.success("Expense deleted.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete expense: {exc}")

st.caption("Cloud storage: Supabase. Expenses and monthly budget are shared across devices.")
