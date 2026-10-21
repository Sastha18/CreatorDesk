
import sqlite3
from pathlib import Path
from datetime import date, datetime

import streamlit as st


def initialise_proposal_table(db_path):
    """Add the proposal table without changing existing tables."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                project_title TEXT NOT NULL,
                proposal_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Draft'
            )
        """)


def generate_offline_proposal(
    freelancer_name,
    client_name,
    project_title,
    service,
    scope,
    deliverables,
    deadline,
    budget,
    terms,
):
    """Create an editable proposal using a free local template."""

    today = date.today().strftime("%d %B %Y")

    return f"""PROJECT PROPOSAL

Prepared by: {freelancer_name}
Prepared for: {client_name}
Date: {today}

PROJECT TITLE
{project_title}

INTRODUCTION
Hello {client_name},

Thank you for considering me for this project. I am pleased to
share this proposal outlining the proposed work, deliverables,
timeline, and budget.

PROJECT OVERVIEW
{scope}

SERVICES
{service}

DELIVERABLES
{deliverables}

PROJECT TIMELINE
Proposed deadline: {deadline}

The timeline will be confirmed after the project requirements
and starting date are agreed upon.

PROJECT BUDGET
Proposed project fee: Rs. {budget:,.2f}

PAYMENT AND TERMS
{terms}

NEXT STEPS
Please review the proposal and let me know if any adjustments
are needed. Work will begin once the scope, timeline, and
payment terms have been mutually agreed upon.

Thank you for your time and consideration.

Best regards,
{freelancer_name}
"""


def save_proposal(
    db_path,
    client_name,
    project_title,
    proposal_text,
    proposal_id=None,
):
    """Save a new draft or update an existing saved draft."""

    with sqlite3.connect(str(db_path)) as conn:
        if proposal_id is None:
            cursor = conn.execute(
                """
                INSERT INTO proposals
                    (client_name, project_title, proposal_text,
                     created_at, status)
                VALUES (?, ?, ?, ?, 'Draft')
                """,
                (
                    client_name,
                    project_title,
                    proposal_text,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return cursor.lastrowid

        conn.execute(
            """
            UPDATE proposals
            SET client_name = ?, project_title = ?, proposal_text = ?
            WHERE id = ?
            """,
            (
                client_name,
                project_title,
                proposal_text,
                proposal_id,
            ),
        )
        return proposal_id


def get_saved_proposals(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        return conn.execute(
            """
            SELECT id, client_name, project_title, created_at,
                   status, proposal_text
            FROM proposals
            ORDER BY id DESC
            """
        ).fetchall()


def render_proposal_studio(db_path):
    """Display Proposal Studio inside the existing Streamlit app."""

    db_path = Path(db_path)
    initialise_proposal_table(db_path)

    st.title("✍️ Proposal Studio")
    st.caption(
        "Create, edit, save, and export project proposals. "
        "The offline generator requires no API key."
    )

    tab_create, tab_saved = st.tabs(
        ["Create a proposal", "Saved proposals"]
    )

    with tab_create:
        st.subheader("Project details")

        with st.form("proposal_generator_form"):
            freelancer_name = st.text_input(
                "Your name or business name",
                placeholder="e.g. CreatorDesk Studio",
            )

            client_name = st.text_input(
                "Client name",
                placeholder="e.g. Example Creator",
            )

            project_title = st.text_input(
                "Project title",
                placeholder="e.g. 10 short-form videos",
            )

            service = st.text_input(
                "Service offered",
                placeholder="e.g. Video editing and captions",
            )

            scope = st.text_area(
                "Project scope",
                placeholder=(
                    "Describe the client's problem and "
                    "what work you will perform."
                ),
                height=110,
            )

            deliverables = st.text_area(
                "Deliverables",
                placeholder=(
                    "e.g. 10 edited videos, captions, "
                    "and two rounds of revisions"
                ),
                height=90,
            )

            deadline = st.date_input(
                "Proposed deadline",
                value=date.today(),
            )

            budget = st.number_input(
                "Proposed fee (INR)",
                min_value=0.0,
                value=500.0,
                step=100.0,
            )

            terms = st.text_area(
                "Payment and project terms",
                value=(
                    "Payment schedule and any advance payment "
                    "will be agreed before work begins. "
                    "Additional work outside the agreed scope "
                    "may require a separate quote."
                ),
                height=100,
            )

            generate = st.form_submit_button(
                "Generate offline proposal",
                type="primary",
            )

        if generate:
            required = [
                freelancer_name.strip(),
                client_name.strip(),
                project_title.strip(),
                service.strip(),
                scope.strip(),
                deliverables.strip(),
            ]

            if not all(required):
                st.error(
                    "Please complete your name, client, project, "
                    "service, scope, and deliverables."
                )
            else:
                st.session_state["proposal_text"] = (
                    generate_offline_proposal(
                        freelancer_name.strip(),
                        client_name.strip(),
                        project_title.strip(),
                        service.strip(),
                        scope.strip(),
                        deliverables.strip(),
                        deadline.strftime("%d %B %Y"),
                        budget,
                        terms.strip() or "Terms to be agreed.",
                    )
                )

                st.session_state["proposal_client"] = (
                    client_name.strip()
                )
                st.session_state["proposal_title"] = (
                    project_title.strip()
                )
                st.session_state["proposal_id"] = None

        st.divider()
        st.subheader("Edit and export")

        proposal_text = st.text_area(
            "Proposal text — edit anything before saving",
            key="proposal_text",
            height=380,
            placeholder=(
                "Your generated proposal will appear here."
            ),
        )

        col_save, col_download = st.columns(2)

        with col_save:
            if st.button(
                "Save draft",
                disabled=not proposal_text.strip(),
                use_container_width=True,
            ):
                client = st.session_state.get(
                    "proposal_client", ""
                )
                title = st.session_state.get(
                    "proposal_title", ""
                )

                if not client or not title:
                    st.error(
                        "Generate a proposal first, or load "
                        "a saved proposal from the Saved proposals tab."
                    )
                else:
                    saved_id = save_proposal(
                        db_path,
                        client,
                        title,
                        proposal_text,
                        st.session_state.get("proposal_id"),
                    )
                    st.session_state["proposal_id"] = saved_id
                    st.success("Proposal draft saved.")

        with col_download:
            st.download_button(
                "Download .txt",
                data=proposal_text,
                file_name="creatordesk_proposal.txt",
                mime="text/plain",
                disabled=not proposal_text.strip(),
                use_container_width=True,
            )

    with tab_saved:
        st.subheader("Your saved proposals")
        saved = get_saved_proposals(db_path)

        if not saved:
            st.info("No saved proposals yet.")
        else:
            options = {
                f"#{p[0]} — {p[2]} / {p[1]} ({p[4]})": p
                for p in saved
            }

            selected_label = st.selectbox(
                "Choose a proposal",
                list(options.keys()),
            )
            selected = options[selected_label]

            st.write(f"**Client:** {selected[1]}")
            st.write(f"**Project:** {selected[2]}")
            st.caption(f"Created: {selected[3]}")

            if st.button("Load into editor"):
                st.session_state["proposal_text"] = selected[5]
                st.session_state["proposal_client"] = selected[1]
                st.session_state["proposal_title"] = selected[2]
                st.session_state["proposal_id"] = selected[0]
                st.success(
                    "Loaded. Return to Create a proposal to edit it."
                )
                st.rerun()
