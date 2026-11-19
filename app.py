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
k4.metric("Variable / Fixed Cost", f"${unit_var:.2f}/seat | ${monthly_fixed:.0f}/mo")
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
        st.latex(r"A(s) = rac{F}{s} + v = rac{" + f"{f_val:.0f}" + r"}{s} + " + f"{v_val:.2f}")
        st.markdown(
            f"- **Practical Domain:** $0 < s \le {cap_val}$ attended seats/month (undefined at $s = 0$).  
"
            f"- **Vertical Asymptote:** $s = 0$ (as seats approach 0, fixed cost per seat grows without bound).  
"
            f"- **Horizontal Behavior:** Approaches $y = \${v_val:.2f}/\text{{seat}}$ as $s$ grows (bounded by capacity $s = {cap_val}$, where $A({cap_val}) = \${precalc_average_cost(cap_val, f_val, v_val):.2f}/\text{{seat}}$)."
        )

        s_grid = np.linspace(1, max(1, cap_val), 100)
        a_grid = [precalc_average_cost(x, f_val, v_val) for x in s_grid]

        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.plot(s_grid, a_grid, label="Average Cost A(s) ($/seat)", linewidth=2)
        ax.axhline(v_val, linestyle="--", color="gray", label=f"Horizontal Asymptote y = ${v_val:.2f}")
        ax.axvline(cap_val, linestyle=":", color="black", label=f"Capacity Limit s = {cap_val}")
        ax.set_title(f"NUR-2 Average Cost Curve (Snapshot {snap['snapshot_id']}, v{snap['state_version']})")
        ax.set_xlabel("Completed Workshop Seats s (seats/month)")
        ax.set_ylabel("Average Cost ($/seat)")
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

        table_s = [s for s in [1, 5, 10, 20, 30, 40, 50, 60] if s <= max(60, cap_val)]
        df_avg = pd.DataFrame({
            "Seats (s)": table_s,
            "Total Cost C(s) ($)": [round(f_val + v_val * s, 2) for s in table_s],
            "Average Cost A(s) ($/seat)": [round(precalc_average_cost(s, f_val, v_val), 2) for s in table_s],
        })
        st.dataframe(df_avg, use_container_width=True, hide_index=True)

    elif selected_level == "Applied":
        st.markdown("### Applied: Function Composition & Capacity Capping")
        st.latex(r"q(p) = \max\left(0, 2D_0 - rac{D_0}{p_0}p
ight), \quad s(p) = \min(	ext{capacity}, q(p)), \quad P(p) = p \cdot s(p) - (F + v \cdot s(p))")
        breakpoint_p = p0_val * (2.0 - cap_val / d0_val) if d0_val > 0 else 0.0
        st.markdown(
            f"- **Price Domain:** $0 \le p \le \${2 * p0_val:.2f}$  
"
            f"- **Capacity Breakpoint Price:** $p = \${breakpoint_p:.2f}$ (below this price, demand exceeds capacity {cap_val} and realized sales stay capped at {cap_val}).  
"
            f"- **Note:** Curves show continuous projections; actual simulation transactions round to whole seats."
        )

        test_p = st.slider("Explore Price p ($/seat)", min_value=0.0, max_value=float(2 * p0_val), value=float(p0_val), step=0.5)
        cont_q = precalc_demand_from_price(test_p, d0_val, p0_val)
        cont_s = min(float(cap_val), cont_q)
        int_s = min(int(cap_val), math.floor(cont_q))
        cont_profit = test_p * cont_s - (f_val + v_val * cont_s)
        int_profit = test_p * int_s - (f_val + v_val * int_s)

        m1, m2, m3 = st.columns(3)
        m1.metric("Demand q(p)", f"{cont_q:.2f} seats")
        m2.metric("Realized Sales s(p)", f"{cont_s:.2f} cont. | {int_s} whole")
        m3.metric("Projected Profit", f"${cont_profit:,.2f} cont. | ${int_profit:,.2f} whole")

        p_grid = np.linspace(0, 2 * p0_val, 150)
        rev_grid = [p * min(float(cap_val), precalc_demand_from_price(p, d0_val, p0_val)) for p in p_grid]
        cost_grid = [f_val + v_val * min(float(cap_val), precalc_demand_from_price(p, d0_val, p0_val)) for p in p_grid]
        prof_grid = [r - c for r, c in zip(rev_grid, cost_grid)]

        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.plot(p_grid, rev_grid, label="Composed Revenue R(p) ($)", linewidth=2)
        ax.plot(p_grid, cost_grid, label="Composed Cost C(s(p)) ($)", linestyle="--")
        ax.plot(p_grid, prof_grid, label="Composed Profit P(p) ($)", linewidth=2)
        ax.axhline(0, color="black", linewidth=1)
        ax.axvline(breakpoint_p, color="gray", linestyle=":", label=f"Capacity Breakpoint p=${breakpoint_p:.2f}")
        ax.set_title(f"NUR-2 Composed Functions vs. Price (Snapshot {snap['snapshot_id']}, v{snap['state_version']})")
        ax.set_xlabel("Workshop Price p ($/seat)")
        ax.set_ylabel("Dollars ($/month)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    else:
        st.markdown("### Advanced: Seasonal Trigonometric Demand Extension & Capacity Clipping")
        st.latex(r"D(t) = D_0 \left(1 + 0.20 \sin\left(rac{2\pi(t - 1)}{12}
ight)
ight), \quad s(t) = \min(	ext{capacity}, \lfloor D(t) 
floor)")
        st.markdown(
            f"- **Assumed Seasonality:** Period = 12 months; peak demand at $t = 4$ ($1.20 \cdot D_0 = {1.2 * d0_val:.1f}$ seats); trough at $t = 10$ ($0.80 \cdot D_0 = {0.8 * d0_val:.1f}$ seats).  
"
            f"- **Extrapolation & Domain Limit:** Sine amplitude (20%) is a fictional teaching assumption; realized sales are clipped at current monthly capacity ({cap_val} seats)."
        )

        months = list(range(1, 13))
        raw_d = [precalc_seasonal_demand(t, d0_val) for t in months]
        clipped_s = [min(cap_val, math.floor(d)) for d in raw_d]
        lost_d = [max(0, math.floor(d) - s) for d, s in zip(raw_d, clipped_s)]
        proj_profit = [p0_val * s - (f_val + v_val * s) for s in clipped_s]

        fig, ax = plt.subplots(figsize=(7.5, 3.8))
        ax.plot(months, raw_d, marker="o", label="Unconstrained Seasonal Demand D(t) (seats)", linewidth=2)
        ax.bar(months, clipped_s, alpha=0.35, label="Realized Sales Clipped at Capacity (seats)")
        ax.axhline(cap_val, color="black", linestyle="--", label=f"Monthly Capacity ({cap_val} seats)")
        ax.set_title(f"NUR-2 Seasonal Demand vs. Realized Capacity (Snapshot {snap['snapshot_id']}, v{snap['state_version']})")
        ax.set_xlabel("Month Index t (1 = Jan ... 12 = Dec)")
        ax.set_ylabel("Workshop Seats")
        ax.set_xticks(months)
        ax.set_ylim(bottom=0)
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

        season_df = pd.DataFrame({
            "Month (t)": months,
            "Seasonal Demand D(t)": [round(d, 2) for d in raw_d],
            "Realized Sales (seats)": clipped_s,
            "Unserved Demand (seats)": lost_d,
            "Projected Profit ($)": [round(pr, 2) for pr in proj_profit],
        })
        st.dataframe(season_df, use_container_width=True, hide_index=True)

    st.info("**Interpretation Prompt:** What changed when capacity capped seasonal demand? Where is the vertical asymptote of average cost, and why is $s=0$ excluded from the practical domain?")

# TAB 4: RUN SIMULATION & FIXTURES
with tabs[3]:
    st.subheader("Execute Simulation Step or Official NUR-2 Fixture")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Manual Monthly Simulation Step (Normal Mode)")
        run_id_in = st.text_input("Unique Run ID", value=f"run-{snap['state_version']:03d}")
        sim_date_in = st.text_input("Simulation Date (YYYY-MM-DD)", value="2027-01-31")
        req_in = st.number_input("Requested Workshop Seats", min_value=0, value=int(snap["offerings"][0]["base_demand"]), step=1)
        mkt_in = st.number_input("Own-Business Marketing Expense ($)", min_value=0.0, value=0.0, step=25.0)
        loan_in = st.number_input("Simulated Loan Proceeds ($)", min_value=0.0, value=0.0, step=100.0)
        capex_in = st.number_input("Equipment Purchase / CapEx ($)", min_value=0.0, value=0.0, step=100.0)

        if st.button("Approve & Advance Simulation Once", type="primary"):
            try:
                updated, rec = simulate_month(
                    snap,
                    run_id=run_id_in.strip(),
                    sim_date=sim_date_in.strip(),
                    requested=int(req_in),
                    price_cents=snap["offerings"][0]["price_cents"],
                    no_show_rate=float(ops["no_show_rate"]),
                    marketing_cents=to_cents(mkt_in),
                    loan_cash_cents=to_cents(loan_in),
                    additional_capex_cents=to_cents(capex_in),
                    mode_label="normal",
                )
                st.session_state.snapshot = updated
                st.success(
                    f"Committed {rec['run_id']}: Sold {rec['sold']} seats, "
                    f"Profit ${from_cents(rec['net_profit_cents']):,.2f}, "
                    f"Closing Cash ${from_cents(rec['closing_cash_cents']):,.2f}."
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Simulation blocked: {exc}")

    with col_b:
        st.markdown("### NUR-2 Official Acceptance Fixture Replay")
        st.warning("Fixture mode resets to opening cash ($4,000) and replays `sample_data/monthly_fixture.csv` using explicit `capacity_override`.")
        fixture_path = Path("sample_data/monthly_fixture.csv")
        if fixture_path.exists():
            fix_df = pd.read_csv(fixture_path)
            st.dataframe(fix_df, use_container_width=True, hide_index=True)

            if st.button("Reset & Replay Official 3-Month Fixture"):
                try:
                    temp_snap = default_snapshot(team_id=snap["team_id"], challenge_level=snap["selected_level"])
                    for idx, row in fix_df.iterrows():
                        temp_snap, _ = simulate_month(
                            temp_snap,
                            run_id=f"fixture-{row['month']}",
                            sim_date=f"{row['month']}-28",
                            requested=int(row["requested"]),
                            price_cents=2500,
                            no_show_rate=0.0,
                            marketing_cents=to_cents(float(row["ad_cost"])),
                            capacity_override=int(row["capacity_override"]),
                            mode_label="fixture_override",
                        )
                    st.session_state.snapshot = temp_snap
                    st.success("Replayed 3-month NUR-2 fixture successfully! Check the Ledger tab.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Fixture error: {exc}")
        else:
            st.error("Missing `sample_data/monthly_fixture.csv`.")

# TAB 5: LEDGER & STAGE 1 STATUS
with tabs[4]:
    st.subheader("Dated Event Ledger & CSV Export")
    if snap["ledger"]:
        led_df = pd.DataFrame(snap["ledger"])
        display_df = pd.DataFrame({
            "Run ID": led_df["run_id"],
            "Date": led_df["date"],
            "Mode": led_df["mode"],
            "Version": led_df["state_version"],
            "Requested": led_df["requested"],
            "Capacity": led_df["effective_capacity"],
            "Sold": led_df["sold"],
            "Unserved": led_df["unserved_demand"],
            "Revenue ($)": led_df["net_revenue_cents"].apply(from_cents),
            "Total Expense ($)": led_df["total_expense_cents"].apply(from_cents),
            "Net Profit ($)": led_df["net_profit_cents"].apply(from_cents),
            "Closing Cash ($)": led_df["closing_cash_cents"].apply(from_cents),
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Export Ledger as CSV",
            data=csv_bytes,
            file_name=f"team_healthcare_ledger_v{snap['state_version']}.csv",
            mime="text/csv",
        )
    else:
        st.info("No simulation rounds recorded yet. Run a month or replay the fixture in Tab 4.")

    st.divider()
    st.markdown("### Implementation Status (Honest Stage Checklist)")
    st.markdown(
        """
        - **Stage 1 (Implemented):** NUR-2 inputs & startup balances, deterministic capacity/no-show engine, Precalculus Foundation/Applied/Advanced math panel, dated ledger, duplicate-run protection, and JSON/CSV save & restore.
        - **Stage 2 (Not Yet Implemented):** Full multi-report print/PDF center, AI recommendation JSON importer tab, and Marketing Studio draft/A-B builder.
        - **Stage 3 (Not Yet Implemented):** Cross-course artifact panel and snapshot-frozen Practice Assessment generator.
        - **Stage 4 (Optional / Not Implemented):** Demonstration storefront with fictional test checkout.
        """
    )
