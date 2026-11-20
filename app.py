import io
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from engine import (
    compute_normal_capacity,
    default_snapshot,
    from_cents,
    get_monthly_fixed_cents,
    get_unit_variable_cents,
    precalc_average_cost,
    precalc_demand_from_price,
    precalc_seasonal_demand,
    simulate_month,
    to_cents,
    validate_imported_snapshot,
)

st.set_page_config(
    page_title="Team Healthcare | NUR-2 Precalculus Simulation",
    layout="wide",
)

# Initialize session state
if "snapshot" not in st.session_state:
    st.session_state.snapshot = default_snapshot(team_id="Team Healthcare", challenge_level="Advanced")
if "baseline_snapshot" not in st.session_state:
    st.session_state.baseline_snapshot = default_snapshot(team_id="Team Healthcare", challenge_level="Advanced")

snap = st.session_state.snapshot

# Sidebar: Persistent State, Save/Load JSON, Reset
with st.sidebar:
    st.header("Team Healthcare | NUR-2")
    st.caption("Precalculus • Nurse-Led Health Education Simulation")
    st.info(
        f"**Snapshot:** `{snap['snapshot_id']}` (v{snap['state_version']})  \n"
        f"**Date:** `{snap['simulation_date']}`  \n"
        f"**Level:** `{snap['selected_level']}`"
    )

    st.subheader("Durable Save / Restore (JSON)")
    snap_json = json.dumps(snap, indent=2)
    st.download_button(
        label="Download Snapshot JSON",
        data=snap_json,
        file_name=f"team_healthcare_nur2_v{snap['state_version']}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("Restore / Import Snapshot JSON", type=["json"])
    if uploaded is not None:
        if st.button("Validate & Load Uploaded JSON", use_container_width=True):
            try:
                raw = uploaded.read().decode("utf-8")
                validated = validate_imported_snapshot(
                    raw,
                    expected_team_id=snap["team_id"],
                    current_version=snap["state_version"],
                )
                st.session_state.snapshot = validated
                st.success(f"Loaded {validated['snapshot_id']} (v{validated['state_version']}).")
                st.rerun()
            except Exception as exc:
                st.error(f"Import rejected: {exc}")

    st.divider()
    if st.button("Reset to NUR-2 Opening State (v1)", use_container_width=True):
        st.session_state.snapshot = default_snapshot(
            team_id=snap["team_id"], challenge_level=snap["selected_level"]
        )
        st.success("Reset to opening post-startup state (v1).")
        st.rerun()

st.title("Career Venture Lab — Nurse-Led Health Education Simulation (NUR-2)")
st.caption(
    "Simulation only: fictional nonclinical health education workshops, customers, and funding. "
    "No medical diagnosis, treatment, or real patient data."
)

# Top KPI Strip
f = snap["funding"]
ops = snap["operations"]
derived_cap = compute_normal_capacity(ops["staff_hours"], ops["hours_per_unit"], ops["venue_seats"])
unit_var = from_cents(get_unit_variable_cents(snap))
monthly_fixed = from_cents(get_monthly_fixed_cents(snap))
base_price = from_cents(snap["offerings"][0]["price_cents"])

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Current Cash", f"${from_cents(f['current_cash_cents']):,.2f}")
k2.metric("Derived Capacity", f"{derived_cap} seats/mo")
k3.metric("Base Seat Price", f"${base_price:,.2f}")
k4.metric("Variable / Fixed Cost", f"${unit_var:.2f}/seat \vert{}${monthly_fixed:.0f}/mo")
k5.metric("Recorded Rounds", f"{len(snap['ledger'])}")

if f["current_cash_cents"] < 80000:
    st.warning("Cash Alert: Current cash is below the $800.00 NUR reserve warning threshold.")

tabs = st.tabs([
    "1. Overview & System Map",
    "2. Inputs & Funding",
    "3. Precalculus Math & Levels",
    "4. Run Simulation & Fixtures",
    "5. Ledger & Stage 1 Status",
])

# TAB 1: OVERVIEW
with tabs[0]:
    st.subheader("Business System Overview")
    st.markdown(
        """
        **Offering:** General Wellness Education Workshop (fictional nonclinical health education)  
        **Operating Cycle:** Save State -> Export Snapshot -> Run AI Specialist Proposals -> Student Math Verification -> Approve & Advance Simulation
        """
    )

    st.markdown("#### System Dependency & Feedback Loop")
    st.code(
        """
[Marketing Campaign (Manual Cost)] ---> [Requested Workshop Demand (D)]
                                                 |
                                                 v
[Educator Hours & Venue Seats] ---> [Capacity = min(floor(hours/0.5), seats)]
                                                 |
                                                 v
                             [Booked = min(Requested, Capacity)]
                                                 |
                                                 v
                         [Attended / Sold = floor(Booked * (1 - no_show))]
                                                 |
                       +-------------------------+-------------------------+
                       v                                                   v
       [Revenue & Variable Costs]                         [Satisfaction & Repeat Demand]
                       |
                       v
        [Dated Ledger & Cash Balance]
        """,
        language="text",
    )

    st.markdown("#### Startup Opening Balance Reconciliation")
    bal_df = pd.DataFrame([
        {"Account": "Post-Startup Spendable Cash", "Amount ($)": from_cents(f["opening_cash_cents"]), "Type": "Asset"},
        {"Account": "Demonstration & Accessibility Equipment", "Amount ($)": from_cents(f["equipment_assets_cents"]), "Type": "Asset"},
        {"Account": "Opening Inventory", "Amount ($)": from_cents(f["opening_inventory_cents"]), "Type": "Asset"},
        {"Account": "Owner Contribution", "Amount ($)": from_cents(f["owner_contribution_cents"]), "Type": "Equity"},
        {"Account": "Retained Earnings (Pre-Opening Expense)", "Amount ($)": from_cents(f["retained_earnings_cents"]), "Type": "Equity"},
    ])
    st.dataframe(bal_df, use_container_width=True, hide_index=True)

# TAB 2: INPUTS & FUNDING
with tabs[1]:
    st.subheader("Editable Business & Capacity Parameters")
    st.caption("Edit assumptions below. Changes apply to your current snapshot configuration.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Offering & Operations**")
        new_price = st.number_input("Workshop Seat Price ($)", min_value=1.0, value=float(base_price), step=1.0)
        new_d0 = st.number_input("Baseline Monthly Demand D0 (seats)", min_value=0, value=int(snap["offerings"][0]["base_demand"]), step=5)
        new_staff_hours = st.number_input("Educator Staff Hours / Month", min_value=0.0, value=float(ops["staff_hours"]), step=1.0)
        new_hours_unit = st.number_input("Educator Hours per Seat", min_value=0.1, value=float(ops["hours_per_unit"]), step=0.1)
        new_venue_seats = st.number_input("Venue Seat Limit / Month", min_value=0, value=int(ops["venue_seats"]), step=5)
        new_no_show = st.slider("No-Show Rate", min_value=0.0, max_value=1.0, value=float(ops["no_show_rate"]), step=0.05)

    with c2:
        st.markdown("**Unit Variable & Monthly Fixed Costs**")
        v_edu = st.number_input("Educator Delivery ($/seat)", min_value=0.0, value=from_cents(snap["cost_lines"]["variable"][0]["unit_cost_cents"]), step=0.5)
        v_mat = st.number_input("Materials ($/seat)", min_value=0.0, value=from_cents(snap["cost_lines"]["variable"][1]["unit_cost_cents"]), step=0.5)
        v_cln = st.number_input("Cleaning Consumables ($/seat)", min_value=0.0, value=from_cents(snap["cost_lines"]["variable"][2]["unit_cost_cents"]), step=0.5)

        f_ven = st.number_input("Venue ($/month)", min_value=0.0, value=from_cents(snap["cost_lines"]["fixed"][0]["monthly_cost_cents"]), step=25.0)
        f_sch = st.number_input("Scheduling Software ($/month)", min_value=0.0, value=from_cents(snap["cost_lines"]["fixed"][1]["monthly_cost_cents"]), step=25.0)
        f_acc = st.number_input("Accessibility Support ($/month)", min_value=0.0, value=from_cents(snap["cost_lines"]["fixed"][2]["monthly_cost_cents"]), step=25.0)
        f_adm = st.number_input("Admin & Insurance ($/month)", min_value=0.0, value=from_cents(snap["cost_lines"]["fixed"][3]["monthly_cost_cents"]), step=25.0)

    if st.button("Save Parameter Updates to Snapshot", type="primary"):
        snap["offerings"][0]["price_cents"] = to_cents(new_price)
        snap["offerings"][0]["base_demand"] = int(new_d0)
        snap["offerings"][0]["hours_per_unit"] = float(new_hours_unit)
        snap["operations"]["staff_hours"] = float(new_staff_hours)
        snap["operations"]["hours_per_unit"] = float(new_hours_unit)
        snap["operations"]["venue_seats"] = int(new_venue_seats)
        snap["operations"]["no_show_rate"] = float(new_no_show)

        snap["cost_lines"]["variable"] = [
            {"name": "educator_delivery", "unit_cost_cents": to_cents(v_edu)},
            {"name": "materials", "unit_cost_cents": to_cents(v_mat)},
            {"name": "cleaning_consumables", "unit_cost_cents": to_cents(v_cln)},
        ]
        snap["cost_lines"]["fixed"] = [
            {"name": "venue", "monthly_cost_cents": to_cents(f_ven)},
            {"name": "scheduling_software", "monthly_cost_cents": to_cents(f_sch)},
            {"name": "accessibility_support", "monthly_cost_cents": to_cents(f_acc)},
            {"name": "admin_insurance_assumption", "monthly_cost_cents": to_cents(f_adm)},
        ]
        st.success("Updated snapshot parameters.")
        st.rerun()

# TAB 3: PRECALCULUS MATH & LEVELS
with tabs[2]:
    st.subheader("Math Skills & Challenge Level Panel — Precalculus")

    selected_level = st.selectbox(
        "Challenge Level (Teacher-Approved)",
        options=["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(snap["selected_level"]),
    )
    if selected_level != snap["selected_level"]:
        snap["selected_level"] = selected_level
        snap["level_by_skill"]["Precalculus"] = selected_level
        st.rerun()

    d0_val = float(snap["offerings"][0]["base_demand"])
    p0_val = from_cents(snap["offerings"][0]["price_cents"])
    v_val = from_cents(get_unit_variable_cents(snap))
    f_val = from_cents(get_monthly_fixed_cents(snap))
    cap_val = compute_normal_capacity(ops["staff_hours"], ops["hours_per_unit"], ops["venue_seats"])

    if selected_level == "Foundation":
        st.markdown("### Foundation: Rational Average Cost Function $A(s)$")
        st.latex(r"A(s) = \frac{F}{s} + v = \frac{" + f"{f_val:.0f}" + r"}{s} + " + f"{v_val:.2f}")
        st.markdown(
            rf"- **Practical Domain:** $0 < s \le {cap_val}$ attended seats/month (
