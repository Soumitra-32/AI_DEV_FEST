"""Shared pytest fixtures for the data pipeline tests.

The fixtures build a *small* dataset (60 users, 3 months) once per test session
so the suite stays fast, while still exercising the exact same code path as the
full 500-user / 6-month run.
"""
from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from backend.data import generator
from backend.scripts import generate_data

SMALL_USERS = 60
SMALL_MONTHS = 3


@pytest.fixture(scope="session")
def base_config() -> dict:
    """The real pipeline configuration from ``backend/data/config.yaml``."""
    return generator.load_config()


@pytest.fixture(scope="session")
def small_config(base_config: dict) -> dict:
    """The same configuration, scaled down so tests run quickly."""
    cfg = copy.deepcopy(base_config)
    cfg["dataset"]["n_users"] = SMALL_USERS
    cfg["dataset"]["months"] = SMALL_MONTHS
    return cfg


@pytest.fixture(scope="session")
def small_dataset(small_config: dict) -> SimpleNamespace:
    """Users, transactions, labels and splits for the small dataset."""
    users, transactions, anomaly_labels, splits, user_labels = generate_data.build_dataset(small_config)
    return SimpleNamespace(
        users=users,
        transactions=transactions,
        anomaly_labels=anomaly_labels,
        splits=splits,
        user_labels=user_labels,
    )


@pytest.fixture(scope="session")
def small_db(tmp_path_factory, small_config: dict, small_dataset: SimpleNamespace):
    """The small dataset written to a real SQLite file (for end-to-end checks)."""
    db_path = tmp_path_factory.mktemp("shonchoy") / "shonchoy_small.db"
    generate_data.write_dataset(
        db_path,
        small_config,
        small_dataset.users,
        small_dataset.transactions,
        small_dataset.anomaly_labels,
        small_dataset.splits,
        small_dataset.user_labels,
    )
    return db_path
