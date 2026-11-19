import pytest
from engine import (
    compute_normal_capacity,
    default_snapshot,
    from_cents,
    precalc_average_cost,
    precalc_seasonal_demand,
    simulate_month,
    to_cents,
    validate_imported_snapshot,
)


def test_nur2_baseline_capacity_and_zero_sales():
    snap = default_snapshot()
    assert compute_normal_capacity(30.0, 0.5, 60) == 60

    snap, rec = simulate_month(
        snap, run_id="zero-test", sim_date="2027-01-31", requested=0, price_cents=2500, no_show_rate=0.0
    )
    assert rec["sold"] == 0
    assert rec["net_revenue_cents"] == 0
    assert rec["variable_expense_cents"] == 0
    assert rec["net_profit_cents"] == -70000  # -$700 fixed cost
    assert rec["closing_cash_cents"] == 330000  # $3,300


def test_nur2_three_month_fixture():
    snap = default_snapshot()
    rows = [
        ("2027-01", 80, 60, 0, 60, 150000, 100000, 50000, 450000),
        ("2027-02", 88, 60, 100, 60, 150000, 110000, 40000, 490000),
        ("2027-03", 72, 45, 0, 45, 112500, 92500, 20000, 510000),
    ]
    for month, req, cap, ad, exp_sold, exp_rev, exp_exp, exp_prof, exp_cash in rows:
        snap, rec = simulate_month(
            snap,
            run_id=f"fix-{month}",
            sim_date=f"{month}-28",
            requested=req,
            price_cents=2500,
            no_show_rate=0.0,
            marketing_cents=to_cents(ad),
            capacity_override=cap,
        )
        assert rec["sold"] == exp_sold
        assert rec["net_revenue_cents"] == exp_rev
        assert rec["total_expense_cents"] == exp_exp
        assert rec["net_profit_cents"] == exp_prof
        assert rec["closing_cash_cents"] == exp_cash


def test_nur2_no_show_business_specific():
    snap = default_snapshot()
    snap, rec = simulate_month(
        snap, run_id="noshow-test", sim_date="2027-01-31", requested=80, price_cents=2500, no_show_rate=0.20
    )
    assert rec["booked"] == 60
    assert rec["attended"] == 48
    assert rec["sold"] == 48
    assert rec["net_revenue_cents"] == 120000
    assert rec["variable_expense_cents"] == 24000
    assert rec["net_profit_cents"] == 26000


def test_duplicate_run_and_stale_import_rejection():
    snap = default_snapshot()
    snap, _ = simulate_month(
        snap, run_id="run-1", sim_date="2027-01-31", requested=80, price_cents=2500, no_show_rate=0.0
    )
    with pytest.raises(ValueError, match="Duplicate run_id"):
        simulate_month(
            snap, run_id="run-1", sim_date="2027-01-31", requested=80, price_cents=2500, no_show_rate=0.0
        )

    stale_json = '{"team_id": "Team Healthcare", "course": "Precalculus", "pathway_id": "NUR-2", "snapshot_id": "snap-001", "state_version": 1, "simulation_date": "2027-01-31", "funding": {}, "operations": {}, "cost_lines": {}, "ledger": []}'
    with pytest.raises(ValueError, match="Stale snapshot rejected"):
        validate_imported_snapshot(stale_json, expected_team_id="Team Healthcare", current_version=2)


def test_precalculus_adapter_checks():
    assert precalc_average_cost(0) is None
    assert pytest.approx(precalc_average_cost(60, 700.0, 5.0), rel=1e-6) == (700.0 / 60.0 + 5.0)
    assert pytest.approx(precalc_seasonal_demand(4, 80.0), rel=1e-6) == 96.0
    assert pytest.approx(precalc_seasonal_demand(10, 80.0), rel=1e-6) == 64.0
