"""Regression tests for the cached user-feature matrix (the online read path).

Feature-backed endpoints used to rebuild the whole matrix -- re-reading every
transaction and recomputing every user -- on *each* request, which cost ~6s per
call and put a page load within reach of the frontend's 12s abort. These tests
pin the two properties the cache has to keep:

* it returns exactly what an uncached build would (no stale or altered rows);
* it does not serve a frame built from a replaced dataset.
"""
from __future__ import annotations

import pandas as pd

from backend.data import features as user_features


def test_the_cached_frame_equals_a_freshly_built_one(small_db) -> None:
    """A cache hit must be indistinguishable from recomputing from scratch."""
    fresh = user_features.user_features(
        user_features.load_config(), user_features.load_transactions(small_db)
    )
    user_features.clear_user_features_cache()
    cached = user_features.user_features_cached(small_db)
    pd.testing.assert_frame_equal(cached, fresh)


def test_a_second_call_is_served_from_the_cache(small_db) -> None:
    """The second call must not rebuild: same object, no re-read."""
    user_features.clear_user_features_cache()
    first = user_features.user_features_cached(small_db)
    second = user_features.user_features_cached(small_db)
    assert first is second, "cached call rebuilt the feature matrix"


def test_replacing_the_dataset_invalidates_the_cache(small_db) -> None:
    """mtime/size are in the key, so a rewritten dataset is never served stale."""
    user_features.clear_user_features_cache()
    before = user_features.user_features_cached(small_db)
    assert len(before) > 0

    # Rewrite the file so its mtime/size fingerprint moves.
    small_db.write_bytes(small_db.read_bytes() + b"\x00")
    after = user_features.user_features_cached(small_db)
    assert after is not before, "cache served a frame from the replaced dataset"
    pd.testing.assert_frame_equal(after, before)


def test_clear_cache_forces_a_rebuild(small_db) -> None:
    """The documented escape hatch for replacing a dataset in-process."""
    user_features.clear_user_features_cache()
    first = user_features.user_features_cached(small_db)
    user_features.clear_user_features_cache()
    assert user_features.user_features_cached(small_db) is not first
