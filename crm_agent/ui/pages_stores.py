"""Stores page: import seed CSV, browse, manually add a store."""

from __future__ import annotations

import streamlit as st

import settings
from db import seed, stores_repo
from db.connection import get_conn


def render() -> None:
    st.header("Stores")
    st.caption(
        "Manage the local store database. The matcher uses this to identify which "
        "store a raw note belongs to."
    )

    conn = get_conn()
    try:
        count = stores_repo.store_count(conn)
        st.write(f"**{count}** stores in the database.")

        with st.expander("Import seed CSV"):
            st.code(str(settings.SEED_STORES_CSV), language="text")
            skip_existing = st.checkbox("Skip stores already imported (by name)", value=True)
            if st.button("Import", type="primary"):
                report = seed.import_stores_csv(
                    conn, settings.SEED_STORES_CSV, skip_existing=skip_existing
                )
                contacts_report = seed.import_contacts_csv(conn, settings.SEED_CONTACTS_CSV)
                st.success(
                    f"Imported {report.stores_inserted} stores, "
                    f"{report.aliases_inserted} aliases, "
                    f"{contacts_report.contacts_inserted} contacts. "
                    f"Skipped {report.stores_skipped} existing."
                )
                for w in report.warnings + contacts_report.warnings:
                    st.warning(w)

        with st.expander("Add a store manually"):
            with st.form("add_store_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    store_name = st.text_input("Store name *")
                    project_name = st.text_input("Project name")
                    owner_name = st.text_input("Owner")
                    phone = st.text_input("Phone")
                    email = st.text_input("Email")
                with col2:
                    primary_contact = st.text_input("Primary contact")
                    guidecx_project_id = st.text_input("GuideCX project ID")
                    city = st.text_input("City")
                    state = st.text_input("State (2-letter)")
                    status = st.text_input("Status", value="Onboarding")
                aliases_str = st.text_input(
                    "Aliases (pipe-delimited)", help="e.g. Joe's | Joes Market | JM"
                )
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Add store")
                if submitted:
                    if not store_name.strip():
                        st.error("Store name is required.")
                    else:
                        sid = stores_repo.insert_store(
                            conn,
                            store_name=store_name.strip(),
                            project_name=project_name.strip() or None,
                            owner_name=owner_name.strip() or None,
                            primary_contact=primary_contact.strip() or None,
                            phone_raw=phone.strip() or None,
                            email=email.strip() or None,
                            city=city.strip() or None,
                            state=state.strip() or None,
                            guidecx_project_id=guidecx_project_id.strip() or None,
                            status=status.strip() or None,
                            notes=notes.strip() or None,
                        )
                        stores_repo.add_alias(conn, sid, store_name)
                        for alias in [a.strip() for a in aliases_str.split("|") if a.strip()]:
                            stores_repo.add_alias(conn, sid, alias)
                        conn.commit()
                        st.success(f"Added '{store_name}' (id={sid}).")

        st.divider()
        st.subheader("All stores")
        stores = stores_repo.all_stores(conn)
        if not stores:
            st.info("No stores yet. Import the seed CSV or add one above.")
        else:
            rows = []
            for s in stores:
                rows.append(
                    {
                        "ID": s.id,
                        "Store": s.store_name,
                        "Owner": s.owner_name or "",
                        "Phone": s.phone_raw or "",
                        "City": s.city or "",
                        "Project": s.guidecx_project_id or "",
                        "Status": s.status or "",
                        "Aliases": " | ".join(s.aliases),
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)
    finally:
        conn.close()
