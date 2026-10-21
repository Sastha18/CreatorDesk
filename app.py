
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st

from proposal_studio import render_proposal_studio
from finance_tracker import render_finance


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "creatordesk.db"

st.set_page_config(
    page_title="CreatorDesk",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def connect_db():
    return sqlite3.connect(str(DB_PATH), timeout=10)


def initialize_db():
    with connect_db() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

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
                fee REAL DEFAULT 0,
                due_date TEXT NOT NULL,
                status TEXT DEFAULT 'Not started',
                payment_status TEXT DEFAULT 'Unpaid',
                created_at TEXT NOT NULL,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )
        """)

        # Store the business profile without modifying
        # the existing clients or projects tables.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL DEFAULT ''
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO app_settings
                (setting_key, setting_value)
            VALUES ('business_name', '')
        """)


def get_business_name():
    with connect_db() as conn:
        row = conn.execute("""
            SELECT setting_value
            FROM app_settings
            WHERE setting_key = 'business_name'
        """).fetchone()

    return row[0] if row else ""


def save_business_name(name):
    with connect_db() as conn:
        conn.execute("""
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES ('business_name', ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
        """, (name.strip(),))


def get_clients():
    with connect_db() as conn:
        return conn.execute("""
            SELECT id, name, contact, service, created_at
            FROM clients
            ORDER BY id DESC
        """).fetchall()


def get_projects():
    with connect_db() as conn:
        return conn.execute("""
            SELECT
                p.id,
                c.name,
                p.title,
                p.fee,
                p.due_date,
                p.status,
                p.payment_status,
                p.created_at
            FROM projects p
            JOIN clients c ON c.id = p.client_id
            ORDER BY p.id DESC
        """).fetchall()


def add_client(name, contact, service):
    if not name.strip():
        raise ValueError("Client name is required.")

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO clients
                (name, contact, service, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            name.strip(),
            contact.strip(),
            service.strip(),
            datetime.now().isoformat(timespec="seconds"),
        ))


def add_project(client_id, title, fee, due_date):
    if not title.strip():
        raise ValueError("Project title is required.")

    if fee < 0:
        raise ValueError("Project fee cannot be negative.")

    with connect_db() as conn:
        conn.execute("""
            INSERT INTO projects
                (
                    client_id, title, fee, due_date,
                    status, payment_status, created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            client_id,
            title.strip(),
            fee,
            due_date.isoformat(),
            "Not started",
            "Unpaid",
            datetime.now().isoformat(timespec="seconds"),
        ))


# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown("""
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.18);
    }

    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

def render_dashboard():
    clients = get_clients()
    projects = get_projects()
    business_name = get_business_name()

    if business_name:
        st.title(f"Welcome to {business_name} 👋")
    else:
        st.title("Welcome to CreatorDesk 👋")

    st.caption(
        "Your workspace for managing clients, projects, "
        "proposals, and business finances."
    )

    # Clearly labelled business-name field.
    with st.expander("⚙️ Business Profile", expanded=not business_name):
        st.subheader("Personalise your workspace")

        with st.form("business_profile_form"):
            entered_name = st.text_input(
                "Your name or business name",
                value=business_name,
                placeholder="e.g. CreatorDesk Studio",
                help="This name appears in your dashboard greeting.",
                max_chars=100,
            )

            save_profile = st.form_submit_button(
                "Save Business Profile",
                type="primary",
            )

            if save_profile:
                if not entered_name.strip():
                    st.error("Please enter a name before saving.")
                else:
                    save_business_name(entered_name)
                    st.success("Business profile saved!")
                    st.rerun()

    total_projects = len(projects)
    active_projects = sum(
        1 for project in projects
        if project[5] not in ("Completed", "Cancelled")
    )
    completed_projects = sum(
        1 for project in projects
        if project[5] == "Completed"
    )
    total_project_value = sum(
        float(project[3] or 0) for project in projects
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Clients", len(clients))
    c2.metric("Total Projects", total_projects)
    c3.metric("Active Projects", active_projects)
    c4.metric("Completed Projects", completed_projects)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("📊 Business Overview")
        st.metric("Total Project Value", f"₹{total_project_value:,.2f}")
        st.caption(
            "This is the sum of recorded project fees, "
            "not actual revenue received."
        )

    with right:
        st.subheader("🚀 Recent Projects")

        if projects:
            st.dataframe(
                [
                    {
                        "Client": p[1],
                        "Project": p[2],
                        "Due Date": p[4],
                        "Status": p[5],
                    }
                    for p in projects[:5]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No projects yet. Start by adding a client "
                "and creating your first project."
            )


# --------------------------------------------------
# CLIENTS
# --------------------------------------------------

def render_clients():
    st.title("👥 Clients")
    st.caption("View your existing client records.")

    clients = get_clients()

    if not clients:
        st.info("No clients added yet. Use Add Client to get started.")
        return

    search = st.text_input(
        "Search clients",
        placeholder="Search by name, contact, or service...",
    )

    filtered = [
        c for c in clients
        if search.strip().casefold() in " ".join(
            str(value or "") for value in c[1:4]
        ).casefold()
    ]

    st.caption(f"{len(filtered)} client(s) found")

    st.dataframe(
        [
            {
                "ID": c[0],
                "Client Name": c[1],
                "Contact": c[2],
                "Service": c[3],
                "Created": c[4],
            }
            for c in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# ADD CLIENT
# --------------------------------------------------

def render_add_client():
    st.title("➕ Add Client")
    st.caption("Create a new client record.")

    with st.form("add_client_form", clear_on_submit=True):
        name = st.text_input(
            "Client name *",
            placeholder="Enter client or company name",
        )
        contact = st.text_input(
            "Contact information",
            placeholder="Email or phone (optional)",
        )
        service = st.text_input(
            "Service required",
            placeholder="e.g. Website design",
        )

        submitted = st.form_submit_button(
            "Save Client",
            type="primary",
        )

        if submitted:
            if not name.strip():
                st.error("Please enter the client name.")
            else:
                add_client(name, contact, service)
                st.success(f"Client '{name.strip()}' added successfully!")
                st.rerun()


# --------------------------------------------------
# PROJECTS
# --------------------------------------------------

def render_projects():
    st.title("📁 Projects")
    st.caption("Track projects and their current status.")

    projects = get_projects()

    if not projects:
        st.info("No projects yet. Add a client, then create a project.")
        return

    search = st.text_input(
        "Search projects",
        placeholder="Search by client, project, or status...",
    )

    filtered = [
        p for p in projects
        if search.strip().casefold() in " ".join(
            str(value or "") for value in (p[1], p[2], p[5], p[6])
        ).casefold()
    ]

    st.dataframe(
        [
            {
                "ID": p[0],
                "Client": p[1],
                "Project": p[2],
                "Fee (₹)": p[3],
                "Due Date": p[4],
                "Status": p[5],
                "Payment Status": p[6],
            }
            for p in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# ADD PROJECT
# --------------------------------------------------

def render_add_project():
    st.title("➕ Add Project")
    st.caption("Create a project and link it to a client.")

    clients = get_clients()

    if not clients:
        st.warning("Add a client before creating a project.")
        st.info("Open the Add Client page first.")
        return

    client_options = {
        f"{client[1]} (#{client[0]})": client[0]
        for client in clients
    }

    with st.form("add_project_form", clear_on_submit=True):
        selected_client = st.selectbox(
            "Select client",
            list(client_options.keys()),
        )

        title = st.text_input(
            "Project title *",
            placeholder="e.g. Portfolio website",
        )

        fee = st.number_input(
            "Agreed project fee (₹)",
            min_value=0.0,
            value=0.0,
            step=500.0,
        )

        due_date = st.date_input(
            "Project due date",
            value=date.today(),
            min_value=date.today(),
        )

        submitted = st.form_submit_button(
            "Create Project",
            type="primary",
        )

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


# --------------------------------------------------
# MAIN NAVIGATION
# --------------------------------------------------

def main():
    initialize_db()

    st.sidebar.title("🚀 CreatorDesk")
    st.sidebar.caption("Your business workspace")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Clients",
            "Projects",
            "Add Client",
            "Add Project",
            "Proposal Studio",
            "Finance Centre",
        ],
    )

    st.sidebar.divider()
    st.sidebar.caption("CreatorDesk · Business workspace")

    if page == "Dashboard":
        render_dashboard()

    elif page == "Clients":
        render_clients()

    elif page == "Projects":
        render_projects()

    elif page == "Add Client":
        render_add_client()

    elif page == "Add Project":
        render_add_project()

    elif page == "Proposal Studio":
        render_proposal_studio(DB_PATH)

    elif page == "Finance Centre":
        render_finance(DB_PATH)


if __name__ == "__main__":
    main()
