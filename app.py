import sqlite3
from pathlib import Path
from datetime import date
from finance_tracker import render_finance
import streamlit as st
from proposal_studio import render_proposal_studio

# --------------------------------------------------
# CreatorDesk: a simple freelance business manager
# --------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "creatordesk.db"

st.set_page_config(
    page_title="CreatorDesk",
    page_icon="💼",
    layout="wide",
)

# CreatorDesk professional theme
st.markdown("""
<style>
    :root {
        --cd-primary: #6366f1;
        --cd-primary-hover: #4f46e5;
        --cd-bg: #f5f7fb;
        --cd-text: #111827;
        --cd-muted: #6b7280;
        --cd-border: #e5e7eb;
    }

    .stApp {
        background: var(--cd-bg);
        color: var(--cd-text);
    }

    [data-testid="stHeader"] {
        background: rgba(245, 247, 251, 0.92);
    }

    [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #273244;
    }

    [data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #cbd5e1;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 9px;
        padding: 7px 10px;
        transition: background 0.15s ease;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: #273244;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #9ca3af;
    }

    h1, h2, h3 {
        color: var(--cd-text);
        letter-spacing: -0.025em;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--cd-border);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 5px rgba(15, 23, 42, 0.03);
    }

    [data-testid="stMetricLabel"] {
        color: var(--cd-muted);
    }

    [data-testid="stMetricValue"] {
        color: var(--cd-text);
        font-weight: 700;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--cd-border);
        border-radius: 14px;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        background: var(--cd-primary);
        color: #ffffff;
        border: 1px solid var(--cd-primary);
        border-radius: 9px;
        font-weight: 600;
        min-height: 40px;
        transition: background 0.15s ease;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: var(--cd-primary-hover);
        color: #ffffff;
        border-color: var(--cd-primary-hover);
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox [data-baseweb="select"] {
        border-radius: 9px;
    }

    [data-testid="stAlert"] {
        border-radius: 10px;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    @media (max-width: 768px) {
        [data-testid="stMetric"] {
            padding: 12px;
        }
    }
</style>
""", unsafe_allow_html=True)


# -------------------- DATABASE --------------------

def connect_db():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT DEFAULT '',
                service TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                fee REAL NOT NULL DEFAULT 0,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Not started',
                payment_status TEXT NOT NULL DEFAULT 'Unpaid',
                created_at TEXT NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients(id)
            )
        """)


def add_client(name, contact, service):
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO clients
                (name, contact, service, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                name.strip(),
                contact.strip(),
                service.strip(),
                date.today().isoformat(),
            ),
        )


def get_clients():
    with connect_db() as conn:
        return conn.execute(
            """
            SELECT id, name, contact, service
            FROM clients
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()


def add_project(client_id, title, fee, due_date):
    with connect_db() as conn:
        conn.execute(
            """
            INSERT INTO projects
                (client_id, title, fee, due_date, status,
                 payment_status, created_at)
            VALUES (?, ?, ?, ?, 'Not started', 'Unpaid', ?)
            """,
            (
                client_id,
                title.strip(),
                fee,
                due_date.isoformat(),
                date.today().isoformat(),
            ),
        )


def get_projects():
    with connect_db() as conn:
        return conn.execute(
            """
            SELECT
                p.id,
                c.name,
                p.title,
                p.fee,
                p.due_date,
                p.status,
                p.payment_status
            FROM projects AS p
            JOIN clients AS c ON c.id = p.client_id
            ORDER BY p.due_date, p.id DESC
            """
        ).fetchall()


def update_project(project_id, status, payment_status):
    with connect_db() as conn:
        conn.execute(
            """
            UPDATE projects
            SET status = ?, payment_status = ?
            WHERE id = ?
            """,
            (status, payment_status, project_id),
        )


# -------------------- STARTUP --------------------

initialize_database()

st.title("💼 CreatorDesk")
st.caption("Your freelance work, organised in one place.")

page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Clients",
        "Projects",
        "Add Client",
        "Add Project",
        "Proposal Studio",
        "Finance centre",
    ],
)

clients = get_clients()
projects = get_projects()


# -------------------- DASHBOARD --------------------

if page == "Dashboard":
    st.subheader("Your business at a glance")

    total_clients = len(clients)
    active_projects = sum(
        1 for p in projects
        if p[5] != "Completed"
    )
    unpaid_amount = sum(
        p[3] for p in projects
        if p[6] != "Paid"
    )
    completed_projects = sum(
        1 for p in projects
        if p[5] == "Completed"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total clients", total_clients)
    col2.metric("Active projects", active_projects)
    col3.metric("Completed projects", completed_projects)
    col4.metric("Outstanding fees", f"₹{unpaid_amount:,.2f}")

    st.divider()
    st.subheader("Upcoming deadlines")

    upcoming = [
        p for p in projects
        if p[5] != "Completed"
    ]
    upcoming.sort(key=lambda p: p[4])

    if upcoming:
        for p in upcoming[:5]:
            with st.container(border=True):
                st.write(f"**{p[2]}** — {p[1]}")
                st.caption(
                    f"Due: {p[4]} | Status: {p[5]} "
                    f"| Payment: {p[6]} | Fee: ₹{p[3]:,.2f}"
                )
    else:
        st.info("No projects yet. Add your first client and project!")

    st.caption(
        "Outstanding fees are based on unpaid project fees, "
        "not verified bank transactions."
    )


# -------------------- CLIENTS --------------------

elif page == "Clients":
    st.subheader("Your clients")

    if clients:
        for client_id, name, contact, service in clients:
            with st.container(border=True):
                st.write(f"**{name}**")
                st.write(f"Contact: {contact or 'Not provided'}")
                st.write(f"Service: {service or 'Not specified'}")
    else:
        st.info("No clients yet. Open Add Client to get started.")


# -------------------- PROJECTS --------------------

elif page == "Projects":
    st.subheader("Manage your projects")

    if not projects:
        st.info("No projects yet. Add a client, then create a project.")

    for p in projects:
        project_id, client_name, title, fee, due_date, status, payment = p

        with st.container(border=True):
            st.write(f"### {title}")
            st.write(f"**Client:** {client_name}")
            st.write(f"**Fee:** ₹{fee:,.2f}")
            st.write(f"**Deadline:** {due_date}")

            with st.form(key=f"project_form_{project_id}"):
                new_status = st.selectbox(
                    "Project status",
                    ["Not started", "In progress", "Completed"],
                    index=[
                        "Not started",
                        "In progress",
                        "Completed",
                    ].index(status),
                    key=f"status_{project_id}",
                )

                new_payment = st.selectbox(
                    "Payment status",
                    ["Unpaid", "Partially paid", "Paid"],
                    index=[
                        "Unpaid",
                        "Partially paid",
                        "Paid",
                    ].index(payment),
                    key=f"payment_{project_id}",
                )

                submitted = st.form_submit_button("Save changes")

                if submitted:
                    update_project(
                        project_id,
                        new_status,
                        new_payment,
                    )
                    st.success("Project updated.")
                    st.rerun()


# -------------------- ADD CLIENT --------------------

elif page == "Add Client":
    st.subheader("Add a new client")

    with st.form("add_client_form", clear_on_submit=True):
        name = st.text_input("Client or business name *")
        contact = st.text_input("Contact details (optional)")
        service = st.text_input(
            "What service do they need? (optional)"
        )

        submitted = st.form_submit_button("Save client")

        if submitted:
            if not name.strip():
                st.error("Please enter a client name.")
            else:
                add_client(name, contact, service)
                st.success(f"Client '{name.strip()}' saved!")
                st.rerun()


# -------------------- ADD PROJECT --------------------

elif page == "Add Project":
    st.subheader("Create a project")

    if not clients:
        st.warning("Add a client before creating a project.")
        st.info("Open Add Client in the sidebar first.")
    else:
        client_options = {
            f"{c[1]} (Client #{c[0]})": c[0]
            for c in clients
        }

        with st.form("add_project_form", clear_on_submit=True):
            selected_client = st.selectbox(
                "Choose client",
                list(client_options.keys()),
            )

            title = st.text_input("Project title *")

            fee = st.number_input(
                "Agreed project fee (₹)",
                min_value=0.0,
                value=500.0,
                step=100.0,
            )

            due_date = st.date_input(
                "Project deadline",
                value=date.today(),
            )

            submitted = st.form_submit_button("Create project")

            if submitted:
                if not title.strip():
                    st.error("Please enter a project title.")
                else:
                    add_project(
                        client_options[selected_client],
                        title,
                        fee,
                        due_date,
                    )
                    st.success(f"Project '{title.strip()}' created!")
                    st.rerun()
elif page == "Proposal Studio":
     render_proposal_studio(DB_PATH)

elif page == "Finance Centre":
    render_finance(DB_PATH)
# -------------------- FOOTER --------------------

st.sidebar.divider()
st.sidebar.caption("CreatorDesk MVP • Local database")
st.sidebar.caption("Built with Python + Streamlit")
