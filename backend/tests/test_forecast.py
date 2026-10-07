"""Forecast and savings-plan tests (Phase 3).

Covers the whole P0 chain on the small generated dataset: baselines, the
calendar spread, the score blocks, the forecast service (including its
no-artifacts fallback) and the savings plan built from that forecast.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import json
from pydantic import ValidationError

from backend.app.schemas import ForecastRequest
from backend.app.services import forecast_service, plan_service
from backend.data import split as split_module
from backend.ml import baselines, dataset, evaluate, explain as ml_explain, forecast

DEMO_USER = "rahim"


# ---------------------------------------------------------------------------
# baselines
# ---------------------------------------------------------------------------
def test_baselines_cover_every_horizon_for_every_user(small_db) -> None:
    frame = dataset.make_frame(small_db)
    users = frame.features["user_id"].drop_duplicates().head(3)
    predictions = baselines.predict(frame.daily, users, horizon_days=5)
    assert set(predictions["horizon"].unique()) == {1, 2, 3, 4, 5}
    assert set(predictions["user_id"].unique()) == set(users)
    for method in baselines.BASELINE_NAMES:
        for flow in ("inflow", "outflow"):
            assert f"{method}_{flow}" in predictions.columns
    assert not predictions[["seasonal_naive_inflow", "trailing_average_outflow"]].isna().any().any()


def test_seasonal_baseline_uses_the_users_own_week(small_db) -> None:
    """The 7-day lag must come from the same user, never from a neighbour."""
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    other = frame.features["user_id"].iloc[1]
    one_user = baselines.predict(frame.daily, [user], horizon_days=1)
    two_users = baselines.predict(frame.daily, [user, other], horizon_days=1)
    mine = one_user.loc[one_user["user_id"].eq(user)].reset_index(drop=True)
    shared = two_users.loc[two_users["user_id"].eq(user)].reset_index(drop=True)
    assert mine["seasonal_naive_inflow"].tolist() == shared["seasonal_naive_inflow"].tolist()
    assert mine["trailing_average_outflow"].tolist() == shared["trailing_average_outflow"].tolist()


# ---------------------------------------------------------------------------
# training targets and the calendar spread
# ---------------------------------------------------------------------------
def test_horizon_target_is_the_mean_of_the_next_two_weeks(small_db) -> None:
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    one = frame.daily.loc[frame.daily["user_id"].eq(user)].sort_values("date").reset_index(drop=True)
    targets = forecast.horizon_targets(one, horizon_days=3).frame
    expected = one["inflow_bdt"].iloc[1:4].mean()
    assert targets["target_inflow"].iloc[0] == pytest.approx(expected)
    # the last rows have no complete future window, so they cannot be targets
    assert len(targets) == len(one) - 3


def test_horizon_targets_are_never_nan(small_db) -> None:
    """Guards the silent failure that produced an all-NaN net target.

    Inflow and outflow lookaheads carry disjoint column names, so subtracting
    the two frames by name aligns on the union and yields all-NaN. The training
    run then "succeeds" with a one-tree model and a NaN bias. Every target must
    be finite, and ``horizon_targets`` raises rather than returning one that is
    not.
    """
    frame = dataset.make_frame(small_db)
    targets = forecast.horizon_targets(frame.features, horizon_days=7).frame
    for column in ("target_inflow", "target_outflow", "target_fee", "target_net"):
        values = targets[column].to_numpy(dtype=float)
        assert np.isfinite(values).all(), f"{column} contains non-finite values"
    # One net definition (GAP-04): the window net includes fees, exactly like
    # the anchor roll_28_net and the served actuals — not inflow−outflow.
    first = targets.iloc[0]
    assert first["target_net"] == pytest.approx(
        first["target_inflow"] - first["target_outflow"] - first["target_fee"]
    )


def test_spread_keeps_the_horizon_total(small_db) -> None:
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    daily = frame.daily.loc[frame.daily["user_id"].eq(user)]
    start = pd.to_datetime(frame.features.loc[frame.features["user_id"].eq(user), "date"].max())
    means = pd.DataFrame({"mean_inflow": [1000.0], "mean_outflow": [800.0]})
    spread = evaluate.spread_predictions(
        pd.DataFrame({"user_id": [user], "date": [start]}), means, daily, horizon_days=14
    )
    assert len(spread) == 14
    assert spread["predicted_inflow"].sum() == pytest.approx(1000.0 * 14, rel=1e-6)
    assert spread["predicted_outflow"].sum() == pytest.approx(800.0 * 14, rel=1e-6)
    assert (spread["predicted_inflow"] >= 0).all()


def test_additive_net_spread_never_explodes_a_single_day(small_db) -> None:
    """GAP-04: dividing by a signed weekday sum once put 33.7× the window
    total on one day. Additive deviations keep every day bounded."""
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    daily = frame.daily.loc[frame.daily["user_id"].eq(user)]
    start = pd.to_datetime(frame.features.loc[frame.features["user_id"].eq(user), "date"].max())
    dates = pd.DataFrame({"user_id": [user], "date": [start]})
    means = pd.DataFrame({
        "mean_inflow": [1000.0], "mean_outflow": [800.0], "mean_net": [500.0],
    })
    spread = evaluate.spread_predictions(dates, means, daily, horizon_days=14)
    total = spread["predicted_net"].sum()
    assert total == pytest.approx(500.0 * 14, rel=1e-6)
    assert (spread["predicted_net"].abs() <= 5 * abs(total)).all()


def test_spread_weights_never_read_the_scored_future(small_db) -> None:
    """GAP-04 no-lookahead: a future spike must not move weights used for an
    earlier origin — the shape cannot see tomorrow."""
    from backend.ml.evaluate import _spread_one_origin

    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    daily = frame.daily.loc[frame.daily["user_id"].eq(user)].sort_values("date")
    origin = pd.to_datetime(daily["date"].iloc[60])
    sub = pd.DataFrame({"user_id": [user], "date": [origin]})
    means = pd.DataFrame({
        "mean_inflow": [1000.0], "mean_outflow": [800.0], "mean_net": [500.0],
    })
    clean = _spread_one_origin(sub, means, daily, origin, 14)
    spiked = daily.copy()
    future_mondays = (pd.to_datetime(spiked["date"]) > origin) & (
        pd.to_datetime(spiked["date"]).dt.weekday == 0
    )
    spiked.loc[future_mondays, "inflow_bdt"] *= 50.0
    assert future_mondays.any()
    with_spike = _spread_one_origin(sub, means, spiked, origin, 14)
    pd.testing.assert_frame_equal(clean, with_spike)


def test_scored_cells_cover_complete_windows_only(small_db, tmp_path) -> None:
    """GAP-04: truncated windows must not be scored as 14-day totals, so
    n_cells == n_windows × horizon by construction."""
    import shutil

    from backend.ml import evaluate as forecast_evaluate
    from backend.ml import forecast as forecast_model

    # Anchor-only artifacts (committed meta, no boosters): predict_mean falls
    # back to each user's own trailing mean, which is all this needs.
    anchor_dir = tmp_path / "anchor_artifacts"
    anchor_dir.mkdir()
    shutil.copy(forecast_model.ARTIFACT_DIR / "forecast_meta.json", anchor_dir / "forecast_meta.json")
    frame = dataset.make_frame(small_db)
    splits = split_module.load_splits(small_db)
    joined, _ = forecast_evaluate.scored_cells(
        frame.features, frame.daily, splits, anchor_dir, horizon_days=14,
    )
    windows = joined[["user_id", "date"]].drop_duplicates().shape[0]
    assert windows > 0
    assert len(joined) == windows * 14


def test_spread_uses_the_net_model_and_keeps_its_total(small_db) -> None:
    """The served days must sum to the net model's 14-day total, not the
    difference of the two spread flows. When those disagree, net is the one the
    solver reads and therefore the one that must survive."""
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    daily = frame.daily.loc[frame.daily["user_id"].eq(user)]
    start = pd.to_datetime(
        frame.features.loc[frame.features["user_id"].eq(user), "date"].max()
    )
    dates = pd.DataFrame({"user_id": [user], "date": [start]})
    means = pd.DataFrame({
        "mean_inflow": [1000.0], "mean_outflow": [800.0], "mean_net": [500.0],
    })
    spread = evaluate.spread_predictions(dates, means, daily, horizon_days=14)
    assert (spread["net_source"] == "model").all()
    assert spread["predicted_net"].sum() == pytest.approx(500.0 * 14, rel=1e-6)
    # the flow difference is 200/day, so the two genuinely disagree here
    implied = (spread["predicted_inflow"] - spread["predicted_outflow"]).sum()
    assert spread["predicted_net"].sum() != pytest.approx(implied, rel=1e-6)


def test_spread_falls_back_and_says_so_when_the_net_model_is_unusable(small_db) -> None:
    """A non-finite net must degrade to the flow difference, visibly."""
    frame = dataset.make_frame(small_db)
    user = frame.features["user_id"].iloc[0]
    daily = frame.daily.loc[frame.daily["user_id"].eq(user)]
    start = pd.to_datetime(
        frame.features.loc[frame.features["user_id"].eq(user), "date"].max()
    )
    dates = pd.DataFrame({"user_id": [user], "date": [start]})
    means = pd.DataFrame({
        "mean_inflow": [1000.0], "mean_outflow": [800.0], "mean_net": [float("nan")],
    })
    spread = evaluate.spread_predictions(dates, means, daily, horizon_days=14)
    assert (spread["net_source"] == "difference").all()
    assert spread["predicted_net"].notna().all()


def test_score_blocks_report_the_model_next_to_both_baselines() -> None:
    joined = pd.DataFrame({
        "user_id": ["u1", "u1", "u2", "u2"],
        # one forecast window per user: every horizon shares the feature date,
        # which is what the cumulative score sums over
        "date": pd.to_datetime(["2025-03-01"] * 4),
        "horizon": [1, 2, 1, 2],
        "actual_inflow": [100.0, 200.0, 300.0, 400.0],
        "actual_outflow": [50.0, 60.0, 70.0, 80.0],
        "actual_net": [50.0, 140.0, 230.0, 320.0],
        "predicted_inflow": [110.0, 190.0, 290.0, 410.0],
        "predicted_outflow": [55.0, 65.0, 65.0, 75.0],
        "predicted_net": [52.0, 138.0, 232.0, 322.0],
        "seasonal_naive_inflow": [0.0, 0.0, 0.0, 0.0],
        "seasonal_naive_outflow": [0.0, 0.0, 0.0, 0.0],
        "seasonal_naive_net": [0.0, 0.0, 0.0, 0.0],
        "trailing_average_inflow": [500.0, 500.0, 500.0, 500.0],
        "trailing_average_outflow": [500.0, 500.0, 500.0, 500.0],
        "trailing_average_net": [0.0, 0.0, 0.0, 0.0],
    })
    day_level = evaluate.day_level_scores(joined)
    assert day_level["inflow"]["model"]["mae"] == pytest.approx(10.0)
    assert day_level["inflow"]["improvement_over_best_pct"] > 0
    assert day_level["inflow"]["model"]["rmse"] >= day_level["inflow"]["model"]["mae"]

    cumulative = evaluate.cumulative_scores(joined)
    # per (user, date) the model sums to 300 vs actual 300 -> only rounding left
    assert cumulative["inflow"]["model"]["mae"] == pytest.approx(0.0, abs=1e-9)

    # net is scored on its own column, so its accuracy is never inferred
    # from the two flow metrics
    assert "net" in day_level and "net" in cumulative
    assert day_level["net"]["model"]["mae"] == pytest.approx(2.0)


def test_test_split_users_are_never_the_demo_user(small_db) -> None:
    """The leakage guard the evaluation depends on."""
    splits = split_module.load_splits(small_db)
    assert DEMO_USER not in set(splits.loc[splits["split"].eq("test"), "user_id"])
    assert set(split_module.users_in_split(splits, "test")).isdisjoint(
        split_module.users_in_split(splits, "train")
    )


# ---------------------------------------------------------------------------
# the service chain the demo runs on
# ---------------------------------------------------------------------------
@pytest.fixture()
def empty_artifacts(tmp_path) -> str:
    """An artifact directory with no trained model, to exercise the fallback."""
    directory = tmp_path / "artifacts"
    directory.mkdir()
    return str(directory)


def test_forecast_returns_fourteen_days_and_a_verdict(small_db, empty_artifacts: str) -> None:
    payload = forecast_service.build_forecast(
        DEMO_USER, horizon_days=14, db_path=small_db, artifact_dir=empty_artifacts
    )
    assert len(payload["days"]) == 14
    first, last = payload["days"][0], payload["days"][-1]
    assert pd.Timestamp(last["date"]) - pd.Timestamp(first["date"]) == pd.Timedelta(days=13)
    for day in payload["days"]:
        assert day["predicted_inflow_bdt"] >= 0
        assert day["predicted_outflow_bdt"] >= 0
        # net is always finite, and the day rows sum to the window total
        assert np.isfinite(day["predicted_net_bdt"])
        assert isinstance(day["is_pressure_day"], bool)
    # no artifacts -> the trailing-average rule serves the request, and says so
    assert payload["provenance"]["source"] == "rule"
    # with no net model the net is the flow difference, and provenance says so
    assert payload["net_source"] == "difference"
    assert payload["provenance"]["assumption"]
    assert payload["metrics"] is None
    assert set(payload["pressure_days"]) <= {day["date"] for day in payload["days"]}


def test_forecast_monthly_net_matches_the_daily_rows(small_db, empty_artifacts: str) -> None:
    payload = forecast_service.build_forecast(
        DEMO_USER, horizon_days=14, db_path=small_db, artifact_dir=empty_artifacts
    )
    window_net = sum(day["predicted_net_bdt"] for day in payload["days"])
    assert payload["monthly_net"] == pytest.approx(window_net * 30 / 14, rel=1e-6)

def test_forecast_can_switch_pressure_days_off(small_db, empty_artifacts: str) -> None:
    payload = forecast_service.build_forecast(
        DEMO_USER, include_pressure_days=False, db_path=small_db, artifact_dir=empty_artifacts
    )
    assert payload["pressure_days"] == []
    assert all(day["is_pressure_day"] is False for day in payload["days"])


def test_forecast_rejects_unknown_users(small_db, empty_artifacts: str) -> None:
    with pytest.raises(KeyError):
        forecast_service.build_forecast("nobody", db_path=small_db, artifact_dir=empty_artifacts)


def test_plan_is_solved_from_the_forecast_surplus(small_db, empty_artifacts: str) -> None:
    outlook = forecast_service.build_forecast(
        DEMO_USER, db_path=small_db, artifact_dir=empty_artifacts
    )
    plan = plan_service.build_plan(
        DEMO_USER, goal_bdt=30000, months=6, db_path=small_db, artifact_dir=empty_artifacts
    )
    assert plan["forecasted_surplus_bdt"] == pytest.approx(max(outlook["monthly_net"], 0.0), abs=0.01)
    assert plan["required_monthly_bdt"] == pytest.approx(5000.0)
    assert plan["safety_buffer_bdt"] == pytest.approx(
        outlook["monthly_outflow"] * forecast_service.SAFETY_BUFFER_DAYS / 30.0, abs=0.01
    )
    assert len(plan["arithmetic"]) == 4
    assert plan["feasible"] is (plan["required_monthly_bdt"] <= plan["feasible_monthly_bdt"])
    assert plan["do_nothing"]["horizon_months"] == 6
    assert plan["pressure_days"] == outlook["pressure_days"]
    assert plan["provenance"]["assumption"]


def test_plan_verdict_follows_the_arithmetic(small_db, empty_artifacts: str) -> None:
    """Either the numbers fit or they do not — nothing may fudge the verdict."""
    plan = plan_service.build_plan(
        DEMO_USER, goal_bdt=5_000_000, months=6, db_path=small_db, artifact_dir=empty_artifacts
    )
    assert plan["feasible"] is False
    assert plan["provenance"]["prediction"].startswith("Not feasible")


# ---------------------------------------------------------------------------
# SHAP drivers: the "why" under the forecast card
# ---------------------------------------------------------------------------
def test_forecast_request_defaults_to_drivers_in_bangla() -> None:
    """The card asks for drivers by default; the language is whitelisted."""
    request = ForecastRequest()
    assert request.include_drivers is True
    assert request.language == "bn"
    assert ForecastRequest(language="en").language == "en"
    with pytest.raises(ValidationError):
        # Deliberately invalid on purpose: the whitelist must reject it.
        ForecastRequest(language="fr")  # type: ignore[arg-type]


def test_build_forecast_wires_drivers_only_when_asked(
    small_db, empty_artifacts: str, monkeypatch
) -> None:
    """The service attaches ml.explain's drivers on request — and does not pay
    for an explainer when the caller only needs the numbers."""
    fake = ml_explain.Driver(
        feature="roll_7_outflow", direction="increases", impact_bdt=123.45, detail="d"
    )
    calls: dict[str, object] = {}

    def fake_top_drivers(row, flow="outflow", language="en", artifact_dir=None, limit=3):
        calls["flow"] = flow
        calls["language"] = language
        return [fake]

    monkeypatch.setattr("backend.ml.explain.top_drivers", fake_top_drivers)
    payload = forecast_service.build_forecast(
        DEMO_USER,
        db_path=small_db,
        artifact_dir=empty_artifacts,
        include_drivers=True,
        language="en",
    )
    assert payload["drivers"] == [fake.as_dict()]
    assert calls == {"flow": "outflow", "language": "en"}
    calls.clear()
    quiet = forecast_service.build_forecast(
        DEMO_USER, db_path=small_db, artifact_dir=empty_artifacts
    )
    assert quiet["drivers"] == []
    assert calls == {}


def test_forecast_route_maps_drivers_into_the_response(monkeypatch, tmp_path) -> None:
    """The route used to drop the drivers the service built — pin the wiring."""
    from fastapi.testclient import TestClient

    from backend.app.config import Settings, get_settings
    from backend.app.main import create_app
    from backend.app.schemas import Provenance

    token = "forecast-driver-token"
    settings = Settings(
        demo_auth_token=token, request_log_path=str(tmp_path / "requests.jsonl")
    )
    captured: dict[str, object] = {}

    def fake_build(user_id, **kwargs):
        captured.update(kwargs)
        return {
            "days": [],
            "pressure_days": [],
            "generated_from": None,
            "net_source": "model",
            "metrics": None,
            "drivers": [
                {
                    "feature": "roll_7_outflow",
                    "direction": "increases",
                    "impact_bdt": 123.45,
                    "detail": "spending over 7 days pushes up next spending",
                }
            ],
            "provenance": Provenance(
                prediction="p", assumption="a", explanation="e", source="model"
            ).model_dump(),
        }

    monkeypatch.setattr("backend.app.services.forecast_service.build_forecast", fake_build)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    response = TestClient(app).post(
        "/forecast", json={"language": "en"}, headers={"X-Demo-Token": token}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["drivers"] == [
        {
            "feature": "roll_7_outflow",
            "direction": "increases",
            "impact_bdt": 123.45,
            "detail": "spending over 7 days pushes up next spending",
        }
    ]
    assert captured["language"] == "en"

    assert captured["include_drivers"] is True


def test_read_booster_text_normalizes_crlf_to_lf() -> None:
    """C1: the loader must not choke on CRLF boosters.

    ``lgb.Booster(model_file=...)`` aborts the whole process when a booster
    file has CRLF endings. ``_read_booster_text`` collapses CRLF -> LF before
    handing the text to LightGBM, so a CRLF artifact degrades instead of
    aborting.
    """
    import tempfile

    with tempfile.NamedTemporaryFile("wb", delete=False) as handle:
        handle.write(b"lightgbm version = 4.7.0\r\ndata pointer = 0\r\n")
        tmp_path = handle.name
    try:
        text = forecast._read_booster_text(Path(tmp_path))
    finally:
        os.remove(tmp_path)
    assert chr(13) not in text
    assert text.startswith("lightgbm version = 4.7.0\n")


def test_forecast_model_loading_degrades_on_non_booster(tmp_path) -> None:
    """C1: a directory with only a meta file must still serve a forecast.
    The loader degrades to anchored fallback instead of raising.
    """
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "forecast_meta.json").write_text(
        json.dumps({"features": []}), encoding="utf-8"
    )
    boosters = forecast.load(artifacts)
    assert "_meta" in boosters
    assert "inflow" not in boosters
    assert "outflow" not in boosters
    # Minimal feature matrix: predict_mean requires the full forecast feature
    # columns even though only the anchored levels are used.
    feat_cols = [
        "day_of_month", "weekday", "is_weekend", "is_month_end", "days_to_month_end",
        "lag_1_net", "lag_2_net", "lag_3_net", "lag_7_net", "lag_14_net",
        "lag_1_outflow", "lag_2_outflow", "lag_3_outflow", "lag_7_outflow", "lag_1_inflow",
        "roll_3_inflow", "roll_3_outflow", "roll_3_net", "roll_7_inflow", "roll_7_outflow",
        "roll_7_net", "roll_14_outflow", "roll_14_net", "roll_28_inflow", "roll_28_outflow",
        "roll_28_net", "max_7_outflow", "shortfall_last_7", "mtd_inflow", "mtd_outflow",
        "mtd_cash_out_bdt", "mtd_cash_out_count", "roll_7_cash_out_bdt", "roll_28_cash_out_bdt",
        "days_since_cash_out", "balance_end_bdt",
    ]
    row = pd.DataFrame([{c: 0.0 for c in feat_cols}])
    row["roll_28_inflow"] = [100.0]
    row["roll_28_outflow"] = [60.0]
    row["roll_28_net"] = [40.0]
    flows = forecast.predict_mean(row, artifact_dir=artifacts)
    assert np.isfinite(flows["mean_inflow"]).all()
    assert np.isfinite(flows["mean_net"]).all()
