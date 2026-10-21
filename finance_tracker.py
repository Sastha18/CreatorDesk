
import sqlite3
from datetime import date
from pathlib import Path

import streamlit as st


def connect_db(db_path):
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_finance_db(db_path):
    """Create finance tables without modifying existing tables."""
    with connect_db(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                payment_date TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'Other',
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
                    ON DELETE RESTRICT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                project_id INTEGER,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id)
                    ON DELETE RESTRICT
            )
        """)


def get_finance_data(db_path):
    with connect_db(db_path) as conn:
        payments = conn.execute("""
            SELECT pay.id, c.name, p.title, pay.amount,
                   pay.payment_date, pay.method, pay.note,
                   p.id
            FROM payments pay
            JOIN projects p ON p.id = pay.project_id
            JOIN clients c ON c.id = p.client_id
            ORDER BY pay.payment_date DESC, pay.id DESC
        """).fetchall()

        expenses = conn.execute("""
            SELECT e.id, e.title, e.amount, e.expense_date,
                   e.category, p.title, e.note, e.project_id
            FROM expenses e
            LEFT JOIN projects p ON p.id = e.project_id
            ORDER BY e.expense_date DESC, e.id DESC
        """).fetchall()

        projects = conn.execute("""
            SELECT p.id, c.name, p.title, p.fee, p.status,
                   COALESCE(SUM(pay.amount), 0)
            FROM projects p
            JOIN clients c ON c.id = p.client_id
            LEFT JOIN payments pay ON pay.project_id = p.id
            GROUP BY p.id, c.name, p.title, p.fee, p.status
            ORDER BY p.id DESC
        """).fetchall()

    return payments, expenses, projects


def add_payment(db_path, project_id, amount, payment_date,
                method, note):
    with connect_db(db_path) as conn:
        row = conn.execute("""
            SELECT fee
            FROM projects
            WHERE id = ?
        """, (project_id,)).fetchone()

        if row is None:
            raise ValueError("The selected project no longer exists.")

        total_paid = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE project_id = ?
        """, (project_id,)).fetchone()[0]

        if amount > row[0] - total_paid + 0.000001:
            raise ValueError(
                "This payment exceeds the project's remaining balance."
            )

        conn.execute("""
            INSERT INTO payments
                (project_id, amount, payment_date, method, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            amount,
            payment_date.isoformat(),
            method,
            note.strip(),
            date.today().isoformat(),
        ))


def add_expense(db_path, title, amount, expense_date,
                category, project_id, note):
    with connect_db(db_path) as conn:
        conn.execute("""
            INSERT INTO expenses
                (title, amount, expense_date, category,
                 project_id, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title.strip(),
            amount,
            expense_date.isoformat(),
            category,
            project_id,
            note.strip(),
            date.today().isoformat(),
        ))


def render_finance(db_path):
    initialize_finance_db(db_path)

    st.header("💰 Finance Centre")
    st.caption(
        "Track recorded payments and expenses. "
        "These are manual records, not verified bank transactions."
    )

    payments, expenses, projects = get_finance_data(db_path)

    total_received = sum(row[3] for row in payments)
    total_expenses = sum(row[2] for row in expenses)
    outstanding = sum(
        max(0.0, row[3] - row[5])
        for row in projects
        if row[4] != "Cancelled"
    )
    estimated_profit = total_received - total_expenses

    c1, c2 = st.columns(2)
    c1.metric("Payments recorded", f"₹{total_received:,.2f}")
    c2.metric("Outstanding balance", f"₹{outstanding:,.2f}")

    c3, c4 = st.columns(2)
    c3.metric("Recorded expenses", f"₹{total_expenses:,.2f}")
    c4.metric("Cash-flow estimate", f"₹{estimated_profit:,.2f}")

    st.divider()

    tab_pay, tab_exp, tab_report = st.tabs([
        "Record Payment", "Add Expense", "Financial Report"
    ])

    project_options = {
        f"{row[2]} — {row[1]} (#{row[0]})": row[0]
        for row in projects
    }

    with tab_pay:
        st.subheader("Record a client payment")

        if not project_options:
            st.info("Create a client and project before recording payments.")
        else:
            with st.form("finance_payment_form", clear_on_submit=True):
                selected = st.selectbox(
                    "Project", list(project_options.keys())
                )
                project_id = project_options[selected]
                selected_project = next(
                    row for row in projects if row[0] == project_id
                )
                remaining = max(
                    0.0, selected_project[3] - selected_project[5]
                )

                st.write(f"Agreed fee: ₹{selected_project[3]:,.2f}")
                st.write(f"Previously recorded: ₹{selected_project[5]:,.2f}")
                st.write(f"Remaining balance: ₹{remaining:,.2f}")

                amount = st.number_input(
                    "Payment amount (₹)",
                    min_value=0.01,
                    value=min(500.0, remaining) if remaining > 0 else 0.01,
                    step=100.0,
                )
                payment_date = st.date_input(
                    "Payment date", value=date.today(),
                    max_value=date.today()
                )
                method = st.selectbox(
                    "Payment method",
                    ["Bank transfer", "UPI", "Cash", "Card", "Other"]
                )
                note = st.text_input("Reference or note (optional)")
                submitted = st.form_submit_button("Save payment")

                if submitted:
                    try:
                        add_payment(
                            db_path, project_id, amount,
                            payment_date, method, note
                        )
                        st.success("Payment recorded!")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    with tab_exp:
        st.subheader("Record a business expense")

        expense_projects = {"General business expense": None}
        expense_projects.update(project_options)

        with st.form("finance_expense_form", clear_on_submit=True):
            title = st.text_input("Expense description *")
            amount = st.number_input(
                "Expense amount (₹)", min_value=0.01,
                value=100.0, step=50.0
            )
            expense_date = st.date_input(
                "Expense date", value=date.today(),
                max_value=date.today()
            )
            category = st.selectbox(
                "Category",
                [
                    "Software", "Equipment", "Travel", "Marketing",
                    "Internet", "Supplies", "Other"
                ]
            )
            selected_expense_project = st.selectbox(
                "Link to project (optional)",
                list(expense_projects.keys())
            )
            note = st.text_input("Note (optional)")
            submitted = st.form_submit_button("Save expense")

            if submitted:
                if not title.strip():
                    st.error("Enter an expense description.")
                else:
                    add_expense(
                        db_path, title, amount, expense_date, category,
                        expense_projects[selected_expense_project], note
                    )
                    st.success("Expense recorded!")
                    st.rerun()

    with tab_report:
        st.subheader("Recorded payments")
        if payments:
            st.dataframe(
                [
                    {
                        "Client": row[1],
                        "Project": row[2],
                        "Amount (₹)": row[3],
                        "Date": row[4],
                        "Method": row[5],
                        "Note": row[6],
                    }
                    for row in payments
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No payment records yet.")

        st.subheader("Recorded expenses")
        if expenses:
            st.dataframe(
                [
                    {
                        "Expense": row[1],
                        "Amount (₹)": row[2],
                        "Date": row[3],
                        "Category": row[4],
                        "Project": row[5] or "General",
                        "Note": row[6],
                    }
                    for row in expenses
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No expenses recorded yet.")

        st.subheader("Project balances")
        if projects:
            st.dataframe(
                [
                    {
                        "Client": row[1],
                        "Project": row[2],
                        "Agreed fee (₹)": row[3],
                        "Recorded payments (₹)": row[5],
                        "Remaining (₹)": max(0.0, row[3] - row[5]),
                    }
                    for row in projects
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.caption(
            "Cash-flow estimate = recorded payments minus recorded expenses. "
            "It is not accounting profit or a tax calculation."
        )
