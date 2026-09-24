"""
Unit tests for the cross-encounter observation store (paper Section III-C,
"Re-encounter comparison").

The mechanism exists because an advisor asked whether cached data from earlier
scans could corroborate a new prediction. It can only do so under constraints,
and these tests are those constraints made executable - each one fails if the
mechanism drifts back toward the version that would be circular:

  1. the store holds observations, never predictions;
  2. a disagreement is evidence, an agreement is not (asymmetry);
  3. no prior encounter means no entry - an absent check is not a passed check;
  4. only fields that cannot legitimately change are compared;
  5. a re-encounter can lower confidence, never raise it.
"""

import os
import tempfile

import _runner_bootstrap  # noqa: F401  (sys.path setup)
import advanced_nmap_scanner as scanner
import observation_store as store

SALT = b"fixed-salt-for-tests"


def observation(**overrides):
    """A minimal stored observation; overrides replace individual fields."""
    base = {
        "device_key": "dev-test000",
        "observed_at": "2026-09-01 10:00:00",
        "modalias": "bluetooth:v004Cp7410d1A50",
        "cod_hex": "0x7A020C",
        "vendor": "Apple, Inc.",
        "lmp_integer": 12,
        "sdp_profiles": ["a2dp", "pbap"],
        "gatt_uuid_count": 3,
        "appearance_category": None,
        "name_resolved": True,
    }
    base.update(overrides)
    return base


# --- 1. the store holds observations, never predictions ---------------------

def test_observation_record_contains_no_prediction():
    """
    The whole argument for this mechanism is that it compares readings, not
    conclusions. A prediction field leaking into the record would make the
    comparison circular, which is exactly what it was designed to avoid.
    """
    obs = store.build_observation(
        "AA:BB:CC:DD:EE:FF", "0x7A020C", "Apple, Inc.",
        chipset_info={"source": "bluetooth", "vendor_id": "004C",
                      "product_id": "7410", "version": "1A50"},
        hw_info={"lmp_integer": 12}, c_data=None,
        sdp_flags={"a2dp": 1, "pbap": 1, "failed": 0},
        gatt_uuids=["180a"], gatt_appearance=None, name="iPhone")
    forbidden = ("device_type", "os", "major_minor_version", "confidence",
                 "confidence_score", "prediction", "inference")
    present = [k for k in obs if k in forbidden]
    assert not present, f"prediction fields stored: {present}"


def test_advertised_name_is_not_stored():
    """Names in this project are frequently personal - only the fact that one
    resolved is kept (research/DATA_RETENTION.md)."""
    obs = store.build_observation(
        "AA:BB:CC:DD:EE:FF", "N/A", "Apple, Inc.", None, {"lmp_integer": 0},
        None, {}, [], None, "Irem iPhone")
    assert "Irem iPhone" not in repr(obs)
    assert obs["name_resolved"] is True


def test_device_key_is_stable_and_not_the_mac():
    a = store.device_key("AA:BB:CC:DD:EE:FF", salt=SALT)
    b = store.device_key("aa:bb:cc:dd:ee:ff", salt=SALT)
    other = store.device_key("11:22:33:44:55:66", salt=SALT)
    assert a == b, "key must be stable for one device, case-insensitively"
    assert a != other
    assert a.startswith("dev-")
    # The key must not be a plain hash of the address: without a secret salt
    # the whole MAC space is brute-forceable, so the store would still be an
    # archive of recoverable identifiers.
    assert store.device_key("AA:BB:CC:DD:EE:FF", salt=b"different-salt") != a, (
        "key must depend on the salt, or it is a plain hash of the MAC and "
        "reversible by brute force over the address space"
    )


# --- 2. asymmetry: disagreement is evidence, agreement is not ---------------

def test_mismatched_invariant_field_is_a_conflict():
    """A device's Modalias cannot legitimately differ between two scans."""
    current = observation(modalias="bluetooth:v0075pA013d0001")
    entry = store.prior_encounter_entry(current, [observation()])
    assert entry["direction"] == "conflicts"
    assert entry["weight"] > 0


def test_agreement_is_recorded_as_unused_not_support():
    """
    The key constraint. A reader agreeing with itself is not independent
    corroboration, so a match must not count toward the agreement total or
    raise confidence - it is recorded at weight 0 as "unused", the same way an
    undatable chipset already is.
    """
    entry = store.prior_encounter_entry(observation(), [observation()])
    assert entry["direction"] == "unused", (
        "agreement with an earlier scan was recorded as support, which would "
        "let the scorer corroborate itself"
    )
    assert entry["weight"] == 0.0


def test_conflict_reports_both_values_for_audit():
    current = observation(vendor="Samsung Electronics")
    mismatches, _ = store.compare_with_prior(current, [observation()])
    assert len(mismatches) == 1
    assert mismatches[0]["current"] == "Samsung Electronics"
    assert mismatches[0]["previous"] == "Apple, Inc."


# --- 3. no prior encounter means no entry -----------------------------------

def test_first_encounter_produces_no_entry():
    """An absent check is not a passed check."""
    assert store.prior_encounter_entry(observation(), []) is None


def test_unresolved_fields_are_not_counted_as_agreement():
    """
    "Not observed" is not "observed to be the same". Two scans that both failed
    to read Modalias have not agreed about anything.
    """
    blank = observation(modalias=None, cod_hex="N/A", vendor="")
    mismatches, comparable = store.compare_with_prior(blank, [blank])
    assert mismatches == []
    assert comparable == 0
    entry = store.prior_encounter_entry(blank, [blank])
    assert entry["direction"] == "unused" and entry["weight"] == 0.0


# --- 4. only invariant fields are compared ----------------------------------

def test_legitimately_varying_signals_are_not_compared():
    """
    RSSI, LMP read success, which services answered and how many GATT UUIDs
    came back all vary between scans of one device. Comparing them for equality
    would manufacture conflicts out of ordinary scan-to-scan variation.
    """
    current = observation(lmp_integer=0, sdp_profiles=[], gatt_uuid_count=0,
                          name_resolved=False)
    mismatches, _ = store.compare_with_prior(current, [observation()])
    assert mismatches == [], f"compared a field that legitimately varies: {mismatches}"


def test_invariant_field_set_is_explicit():
    assert set(store.INVARIANT_FIELDS) == {"modalias", "cod_hex", "vendor"}
    overlap = set(store.INVARIANT_FIELDS) & set(store.VARIABLE_FIELDS)
    assert not overlap, f"field is both invariant and variable: {overlap}"


# --- 5. a re-encounter can lower confidence, never raise it -----------------

def base_args(prior_encounter):
    """predict_device on a device whose branch is decided by name alone."""
    return scanner.predict_device(
        hw_info={"lmp_integer": 12, "manufacturer": "Unknown"},
        services=[], sdp_flags={k: 0 for k in
                                ("a2dp", "map", "pbap", "hfp", "opp", "did",
                                 "hid", "pan", "failed")},
        sdp_handles=[], gatt_uuids=[], vendor="Apple, Inc.", name="iPhone",
        c_data={"lmp_integer": 12, "success": True, "estimated_android": None,
                "flags": {k: 0 for k in ("a2dp", "map", "pbap", "hfp", "opp", "did")}},
        cod_hex="N/A", prior_encounter=prior_encounter)


def test_matching_re_encounter_does_not_raise_confidence():
    without = base_args(None)
    with_match = base_args(store.prior_encounter_entry(observation(), [observation()]))
    assert with_match["confidence"] == without["confidence"]
    assert with_match["confidence_score"] <= without["confidence_score"]
    assert with_match["has_conflicting_signals"] is False


def test_conflicting_re_encounter_lowers_confidence():
    without = base_args(None)
    conflicting = store.prior_encounter_entry(
        observation(vendor="Samsung Electronics"), [observation()])
    with_conflict = base_args(conflicting)
    assert with_conflict["has_conflicting_signals"] is True
    assert with_conflict["confidence_score"] < without["confidence_score"]


def test_re_encounter_never_changes_the_prediction():
    """Post-hoc means post-hoc: type, OS and version must be untouched."""
    without = base_args(None)
    conflicting = store.prior_encounter_entry(
        observation(vendor="Samsung Electronics"), [observation()])
    with_conflict = base_args(conflicting)
    for field in ("device_type", "os", "major_minor_version"):
        assert with_conflict[field] == without[field], field


# --- store round-trip -------------------------------------------------------

def test_record_and_load_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "store.jsonl")
        assert store.load_prior_observations("dev-test000", path=path) == []
        store.record_observation(observation(), path=path)
        store.record_observation(observation(device_key="dev-other"), path=path)
        mine = store.load_prior_observations("dev-test000", path=path)
        assert len(mine) == 1
        assert mine[0]["modalias"] == "bluetooth:v004Cp7410d1A50"


def test_unreadable_store_does_not_raise():
    """A broken store must degrade to 'no prior encounter', not fail a scan."""
    assert store.load_prior_observations("dev-x", path="/nonexistent/store.jsonl") == []


if __name__ == "__main__":
    from _runner import run

    raise SystemExit(run())
