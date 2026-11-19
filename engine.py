from __future__ import annotations

import copy
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def to_cents(amount: float | int | str | Decimal) -> int:
    d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def from_cents(cents: int) -> float:
    return float(Decimal(cents) / Decimal(100))


def default_snapshot(team_id: str = "Team Healthcare", challenge_level: str = "Advanced") -> Dict[str, Any]:
    return {
        "team_id": team_id,
        "course": "Precalculus",
        "pathway_id": "NUR-2",
        "business_name": "Nurse-led health education simulation",
        "snapshot_id": "snap-001",
        "state_version": 1,
        "simulation_date": "2027-01-31",
        "base_period": "monthly",
        "working_days": 20,
        "currency": "USD",
        "selected_level": challenge_level,
        "level_by_skill": {
            "Precalculus": challenge_level
        },
        "random_seed": 2027,
        "assumptions": [
            "Fictional nonclinical health education workshops only; no medical diagnosis or treatment.",
            "Simplified accrual model with immediate payment; taxes and depreciation disabled at baseline.",
            "Seasonal trigonometric demand extension (when enabled in Advanced mode) is an illustrative assumption, not a clinical or market guarantee."
        ],
        "sources": [
            "Career Venture Lab Student Handbook (Revised Nov 2026) - Pathway NUR-2 & Precalculus Adapter"
        ],
        "offerings": [
            {
                "offering_id": "OFF-01",
                "name": "General wellness education workshop",
                "unit": "workshop seat",
                "price_cents": 2500,
                "base_demand": 80,
                "hours_per_unit": 0.5
            }
        ],
        "funding": {
            "owner_contribution_cents": 600000,
            "grant_cents": 0,
            "loan_principal_cents": 0,
            "equipment_assets_cents": 150000,
            "pre_opening_expense_cents": 50000,
            "opening_inventory_cents": 0,
            "opening_cash_cents": 400000,
            "current_cash_cents": 400000,
            "current_debt_cents": 0,
            "retained_earnings_cents": -50000
        },
        "operations": {
            "staff_hours": 30.0,
            "hours_per_unit": 0.5,
            "venue_seats": 60,
            "no_show_rate": 0.0,
            "satisfaction_mean": 4.0
        },
        "cost_lines": {
            "variable": [
                {"name": "educator_delivery", "unit_cost_cents": 200},
                {"name": "materials", "unit_cost_cents": 200},
                {"name": "cleaning_consumables", "unit_cost_cents": 100}
            ],
            "fixed": [
                {"name": "venue", "monthly_cost_cents": 25000},
                {"name": "scheduling_software", "monthly_cost_cents": 10000},
                {"name": "accessibility_support", "monthly_cost_cents": 20000},
                {"name": "admin_insurance_assumption", "monthly_cost_cents": 15000}
            ]
        },
        "ledger": [],
        "executed_run_ids": [],
        "campaigns": [],
        "decisions": []
    }


def compute_normal_capacity(staff_hours: float, hours_per_unit: float, venue_seats: int) -> int:
    if staff_hours < 0 or hours_per_unit <= 0 or venue_seats < 0:
        raise ValueError("Invalid capacity parameters.")
    staff_cap = math.floor(staff_hours / hours_per_unit)
    return int(min(staff_cap, int(venue_seats)))


def get_unit_variable_cents(snap: Dict[str, Any]) -> int:
    return sum(int(item["unit_cost_cents"]) for item in snap["cost_lines"]["variable"])


def get_monthly_fixed_cents(snap: Dict[str, Any]) -> int:
    return sum(int(item["monthly_cost_cents"]) for item in snap["cost_lines"]["fixed"])


def precalc_average_cost(s: float, fixed_dollars: float = 700.0, var_dollars: float = 5.0) -> Optional[float]:
    if s <= 0:
        return None
    return (fixed_dollars / s) + var_dollars


def precalc_demand_from_price(p: float, d0: float = 80.0, p0: float = 25.0) -> float:
    if p0 <= 0:
        return 0.0
    return max(0.0, 2.0 * d0 - (d0 / p0) * p)


def precalc_seasonal_demand(t: int, d0: float = 80.0) -> float:
    return d0 * (1.0 + 0.20 * math.sin(2.0 * math.pi * (t - 1) / 12.0))


def simulate_month(
    snap: Dict[str, Any],
    *,
    run_id: str,
    sim_date: str,
    requested: int,
    price_cents: int,
    no_show_rate: float,
    marketing_cents: int = 0,
    refund_cents: int = 0,
    new_owner_cash_cents: int = 0,
    loan_cash_cents: int = 0,
    principal_repayment_cents: int = 0,
    interest_cents: int = 0,
    additional_capex_cents: int = 0,
    capacity_override: Optional[int] = None,
    mode_label: str = "normal"
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if requested < 0 or price_cents < 0 or marketing_cents < 0 or refund_cents < 0:
        raise ValueError("Quantities and monetary amounts must be nonnegative.")
    if not (0.0 <= no_show_rate <= 1.0):
        raise ValueError("no_show_rate must be in [0, 1].")

    new_snap = copy.deepcopy(snap)

    # Duplicate-run protection
    if run_id in new_snap.get("executed_run_ids", []):
        raise ValueError(f"Duplicate run_id '{run_id}' rejected. Reopening or rerunning will not duplicate transactions.")

    ops = new_snap["operations"]
    if capacity_override is not None:
        if capacity_override < 0:
            raise ValueError("capacity_override must be >= 0.")
        effective_capacity = int(capacity_override)
    else:
        effective_capacity = compute_normal_capacity(
            ops["staff_hours"], ops["hours_per_unit"], ops["venue_seats"]
        )

    # NUR deterministic algorithm:
    # booked = min(requested, floor(staff_hours/hours_per_unit), venue_seats)
    # attended = floor(booked * (1 - no_show_rate)); sold = attended
    booked = min(int(requested), effective_capacity)
    attended = math.floor(booked * (1.0 - no_show_rate))
    sold = int(attended)
    unserved_demand = max(0, int(requested) - booked)

    unit_var_cents = get_unit_variable_cents(new_snap)
    fixed_cents = get_monthly_fixed_cents(new_snap)

    gross_revenue_cents = price_cents * sold
    net_revenue_cents = gross_revenue_cents - refund_cents
    variable_expense_cents = unit_var_cents * sold
    total_operating_expense_cents = variable_expense_cents + fixed_cents + marketing_cents

    operating_profit_cents = net_revenue_cents - total_operating_expense_cents
    net_profit_cents = operating_profit_cents - interest_cents

    opening_cash_cents = int(new_snap["funding"]["current_cash_cents"])
    closing_cash_cents = (
        opening_cash_cents
        + net_revenue_cents
        - variable_expense_cents
        - fixed_cents
        - marketing_cents
        - interest_cents
        - principal_repayment_cents
        - additional_capex_cents
        + new_owner_cash_cents
        + loan_cash_cents
    )

    if closing_cash_cents < 0:
        raise ValueError("Insufficient cash for this transaction set (closing cash would be negative).")

    # Update balances and version
    new_version = int(new_snap["state_version"]) + 1
    new_snap["state_version"] = new_version
    new_snap["snapshot_id"] = f"snap-{new_version:03d}"
    new_snap["simulation_date"] = sim_date

    f = new_snap["funding"]
    f["current_cash_cents"] = closing_cash_cents
    f["owner_contribution_cents"] += new_owner_cash_cents
    f["current_debt_cents"] += loan_cash_cents - principal_repayment_cents
    f["equipment_assets_cents"] += additional_capex_cents
    f["retained_earnings_cents"] += net_profit_cents

    record = {
        "run_id": run_id,
        "date": sim_date,
        "mode": mode_label,
        "state_version": new_version,
        "requested": int(requested),
        "effective_capacity": effective_capacity,
        "booked": booked,
        "attended": attended,
        "sold": sold,
        "unserved_demand": unserved_demand,
        "unit_price_cents": price_cents,
        "gross_revenue_cents": gross_revenue_cents,
        "refund_cents": refund_cents,
        "net_revenue_cents": net_revenue_cents,
        "variable_expense_cents": variable_expense_cents,
        "fixed_expense_cents": fixed_cents,
        "marketing_cents": marketing_cents,
        "total_expense_cents": total_operating_expense_cents + interest_cents,
        "operating_profit_cents": operating_profit_cents,
        "interest_cents": interest_cents,
        "net_profit_cents": net_profit_cents,
        "opening_cash_cents": opening_cash_cents,
        "closing_cash_cents": closing_cash_cents
    }

    new_snap["ledger"].append(record)
    new_snap["executed_run_ids"].append(run_id)
    return new_snap, record


def validate_imported_snapshot(raw_json: str, expected_team_id: str, current_version: int) -> Dict[str, Any]:
    data = json.loads(raw_json)
    required_keys = [
        "team_id", "course", "pathway_id", "snapshot_id",
        "state_version", "simulation_date", "funding", "operations", "cost_lines", "ledger"
    ]
    for k in required_keys:
        if k not in data:
            raise ValueError(f"Missing required snapshot field: '{k}'.")
    if data["team_id"] != expected_team_id:
        raise ValueError(f"Team mismatch: expected '{expected_team_id}', got '{data['team_id']}'.")
    if data["pathway_id"] != "NUR-2":
        raise ValueError(f"Pathway mismatch: expected 'NUR-2', got '{data['pathway_id']}'.")
    if int(data["state_version"]) < int(current_version):
        raise ValueError(
            f"Stale snapshot rejected: imported state_version v{data['state_version']} is older than current v{current_version}."
        )
    return data
