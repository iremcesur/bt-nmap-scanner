"""
Regression tests for three defects where the running code disagreed with the
paper's own description of it (paper Sections III-C "Evidence chain" and III-D
"Scoring model"). Each test fails against the pre-fix code.

  B4  The Android branch returned the C helper's estimated_android string
      verbatim whenever the helper binary was present, bypassing the corrected
      ladder. The helper carries its own copy of the table, still containing
      both defects the ladder was fixed for, so the invariants asserted by
      test_android_score_ladder.py held only on the path nothing took.

  B5  The chronology check compared the chipset's release year against the
      predicted OS bucket's EARLIEST plausible year, which is true of nearly
      every device and therefore means nothing. The paper specifies the LATEST
      plausible year - the only direction that is a genuine contradiction.

  B6  A conflict lowered confidence only when it was already "High", so a
      Medium prediction with a conflicting signal was labelled identically to
      a Medium prediction with none. The paper's Algorithm 1 specifies
      LowerOneLevel: High -> Medium -> Low.
"""

import _runner_bootstrap  # noqa: F401  (sys.path setup)
import advanced_nmap_scanner as scanner


def c_data(success=True, lmp=13, estimated_android=None, **flags):
    """A run_c_version_finder() result with every profile flag off by default."""
    base = {"a2dp": 0, "map": 0, "pbap": 0, "hfp": 0, "opp": 0, "did": 0}
    base.update({k: 1 for k in flags})
    return {"lmp_integer": lmp, "flags": base,
            "estimated_android": estimated_android, "success": success}


def sdp_flags(**flags):
    base = {k: 0 for k in ("a2dp", "map", "pbap", "hfp", "opp", "did",
                           "hid", "pan", "failed")}
    base.update({k: 1 for k in flags})
    return base


def predict_android(helper_label=None, lmp=13):
    """
    predict_device_core on a device that reaches the Android branch: PBAP is
    present, so the branch fires regardless of vendor or Class-of-Device.
    """
    return scanner.predict_device_core(
        hw_info={"lmp_integer": lmp, "manufacturer": "Unknown"},
        services=[],
        sdp_flags=sdp_flags(pbap=True),
        sdp_handles=[],
        gatt_uuids=[],
        vendor="Samsung Electronics",
        name="Galaxy",
        c_data=c_data(lmp=lmp, estimated_android=helper_label, pbap=True),
    )


# --- B4: the ladder is the only Android scorer ------------------------------

def test_c_helper_label_does_not_override_the_ladder():
    """
    The helper's string must not be emitted as the prediction. We feed a label
    the ladder can never produce, so a match proves the short-circuit is gone
    rather than the two paths happening to agree.
    """
    inference = predict_android(helper_label="Android 3.0 (Honeycomb)")
    assert inference["major_minor_version"] != "Android 3.0 (Honeycomb)", (
        "the C helper's estimated_android string was returned verbatim, "
        "bypassing the corrected ladder"
    )
    assert inference["major_minor_version"] in dict(
        (label, threshold) for threshold, label in scanner.ANDROID_VERSION_BANDS
    ) or "older" in inference["major_minor_version"]


def test_prediction_is_identical_with_and_without_the_helper_label():
    """
    Presence of the helper binary must not change the outcome. This is what
    makes the archive replay (research/replay_predictions.py) comparable to a
    live scan at all - the replay has no helper string to feed in.
    """
    with_label = predict_android(helper_label="Android 16 (Baklava)")
    without_label = predict_android(helper_label=None)
    assert with_label["major_minor_version"] == without_label["major_minor_version"]
    assert with_label["confidence"] == without_label["confidence"]


def test_ladder_scores_a_device_the_helper_would_have_misranked():
    """
    The helper's table scores LMP 9 above LMP 10 (85 vs 68), so it maps a
    Bluetooth 5.1 controller to an older Android than a 5.0 one. The ladder
    must be monotone here - this is the OPPO A5 2020 case from the paper.
    """
    lmp9 = predict_android(lmp=9)["android_score_raw"]
    lmp10 = predict_android(lmp=10)["android_score_raw"]
    assert lmp9 < lmp10, f"LMP 9 scored {lmp9}, LMP 10 scored {lmp10}"


# --- B5: chronology check uses the upper edge -------------------------------

def test_chipset_older_than_the_prediction_is_not_a_conflict():
    """Old silicon runs new software - an ordinary, long-supported device."""
    assert scanner.check_chipset_os_consistency(
        "Android 14 (Upside Down Cake)", 2016) == []


def test_chipset_newer_than_the_buckets_earliest_year_is_not_a_conflict():
    """
    The pre-fix check fired here. Hardware almost always postdates the first
    release of the OS it runs, so this must stay silent or the flag is noise.
    """
    assert scanner.check_chipset_os_consistency(
        "Android 11 (Red Velvet Cake)", 2021) == [], (
        "flagged a chipset that merely postdates the bucket's first release"
    )


def test_chipset_newer_than_the_buckets_latest_year_is_a_conflict():
    """A 2024 chipset cannot be in a device that shipped running Android 11."""
    assert scanner.check_chipset_os_consistency(
        "Android 11 (Red Velvet Cake)", 2024) == ["chipset_newer_than_predicted_os"]


def test_open_ended_buckets_are_never_flagged():
    """
    "iOS 17+" and the newest Android band have no upper edge, so no chipset
    date can contradict them.
    """
    for label in ("iOS 17+", "Windows 11", "Android 16 (Baklava)"):
        assert scanner.check_chipset_os_consistency(label, 2030) == [], label


def test_every_bucket_the_scorer_can_emit_has_a_chronology_entry():
    """
    A version label with no table entry silently skips the check. The Android
    bands and the LMP floor labels are the buckets predict_device_core emits.
    """
    emitted = [label for _threshold, label in scanner.ANDROID_VERSION_BANDS]
    emitted += ["Android 7.0 or older", "Windows 11", "Windows 10",
                "Windows 8.1 / 10", "Windows 7 or older",
                "iOS 17+", "iOS 16+", "iOS 15+", "iOS 14 or older",
                "macOS 14+", "macOS 13+", "macOS 12+", "macOS 11 or older",
                "iPadOS 17+", "iPadOS 16+", "iPadOS 15+", "iPadOS 14 or older"]
    missing = [label for label in emitted
               if label not in scanner.OS_VERSION_PLAUSIBLE_YEARS]
    assert not missing, f"no chronology span for: {missing}"


def test_plausible_spans_are_ordered():
    """A bucket's latest year cannot precede its earliest."""
    bad = [(label, span) for label, span in scanner.OS_VERSION_PLAUSIBLE_YEARS.items()
           if span[1] is not None and span[1] < span[0]]
    assert not bad, bad


# --- B6: confidence drops exactly one level ---------------------------------

def test_conflict_lowers_high_to_medium():
    assert scanner._lower_confidence_one_level("High", "x").startswith("Medium")


def test_conflict_lowers_medium_to_low():
    """
    The pre-fix code left this untouched, so a Medium prediction with a
    conflicting signal read the same as one without.
    """
    assert scanner._lower_confidence_one_level(
        "Medium (Name Heuristic)", "x").startswith("Low"), (
        "a conflict on an already-Medium prediction was silently ignored"
    )


def test_low_is_the_floor():
    assert scanner._lower_confidence_one_level("Low", "x").startswith("Low")


def test_lowered_label_carries_the_reason():
    assert "Conflicting Evidence Signals" in scanner._lower_confidence_one_level(
        "High", "Conflicting Evidence Signals")


def test_numeric_score_tracks_the_qualitative_label():
    """
    confidence_score is derived from the label, not decremented separately -
    the two must not be able to disagree about how bad a prediction is.
    """
    for label in ("High", "Medium (Conflicting Evidence Signals)", "Low (x)"):
        lowered = scanner._lower_confidence_one_level(label, "x")
        assert (scanner._confidence_string_to_score(lowered)
                <= scanner._confidence_string_to_score(label)), label


if __name__ == "__main__":
    from _runner import run

    raise SystemExit(run())
