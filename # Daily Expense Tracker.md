# Daily Expense Tracker

## Run on Windows
1. Extract this ZIP to a folder.
2. Open Command Prompt in that folder and run:

```cmd
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Features
- Add daily expenses with amount, date, category, payment method, and note
- Today's and monthly totals
- Monthly budget progress
- Category pie chart and daily spending chart
- Filterable history and CSV export
- Edit/delete entries

Expenses and budget are stored in `expenses.db` next to `app.py`. Back up this file; this local version does not sync across devices.
