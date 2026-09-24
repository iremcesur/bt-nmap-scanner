"""
Invariants for the Android version score ladder (paper Section III, "Scoring
model"). These are the three defects B1 was opened for; each test fails
against the pre-fix table, so they are regression tests, not restatements.
"""

import itertools

import _runner_bootstrap  # noqa: F401  (sys.path setup)
import advanced_nmap_scanner as scanner


def reachable_scores():
    """
    Every integer raw score the scorer can actually emit, by brute force over
    the full cross product of LMP version x bonus subset. Bonuses are not all
    independent - did_modern_lmp only applies when did is set AND lmp >= 11 -
    so the dependency is modelled here rather than assumed away.
    """
    seen = set()
    optional = ["a2dp", "hfp", "map", "pbap", "opp", "did",
                "lmp_simultaneous_le_bredr", "gatt_conn_interval_sub_15ms"]
    for lmp in list(scanner.ANDROID_LMP_BASE) + [15, 20]:
        base = scanner.android_lmp_base(lmp)
        for r in range(len(optional) + 1):
            for subset in itertools.combinations(optional, r):
                score = base + sum(scanner.ANDROID_BONUSES[k] for k in subset)
                if "did" in subset and lmp >= 11:
                    score += scanner.ANDROID_BONUSES["did_modern_lmp"]
                seen.add(max(0, min(score, scanner.ANDROID_SCORE_MAX)))
    return seen


def test_i1_lmp_base_is_non_decreasing():
    """A newer Bluetooth controller must never score lower than an older one."""
    versions = sorted(scanner.ANDROID_LMP_BASE)
    scores = [scanner.ANDROID_LMP_BASE[v] for v in versions]
    offenders = [
        (versions[i], scores[i], versions[i + 1], scores[i + 1])
        for i in range(len(scores) - 1)
        if scores[i + 1] < scores[i]
    ]
    assert offenders == [], f"LMP base score decreases at: {offenders}"


def test_i2_every_version_band_is_reachable():
    """
    Each band must be produced by at least one attainable score. Pre-fix,
    "Android 12 (Snow Cone)" occupied raw scores [75.075, 75.6), an interval
    containing no integer, so it could never be emitted.
    """
    scores = reachable_scores()
    emitted = {scanner.android_version_from_score(s) for s in scores}
    missing = [label for _, label in scanner.ANDROID_VERSION_BANDS if label not in emitted]
    assert missing == [], f"unreachable version bands: {missing}"


def test_i3_provisional_bonuses_cannot_skip_a_version():
    """
    The paper claims the two uncalibrated evidence layers only nudge the
    estimate. Pre-fix that was false: the Android 12 band was 0.05 wide on a
    scale where +1 raw point moved the rescaled score by ~0.095, so a single
    provisional point jumped Android 11 -> Android 13.

    Checked two ways: structurally (no band narrower than the largest
    provisional bonus) and directly (adding the provisional points to any
    attainable score moves the label by at most one band).
    """
    thresholds = [t for t, _ in scanner.ANDROID_VERSION_BANDS]
    assert thresholds == sorted(thresholds, reverse=True), "bands must be ordered high to low"
    widths = {
        scanner.ANDROID_VERSION_BANDS[i + 1][1]: thresholds[i] - thresholds[i + 1]
        for i in range(len(thresholds) - 1)
    }
    too_narrow = {k: w for k, w in widths.items() if w < scanner.MAX_PROVISIONAL_BONUS}
    assert too_narrow == {}, (
        f"bands narrower than the largest provisional bonus "
        f"({scanner.MAX_PROVISIONAL_BONUS}): {too_narrow}"
    )

    rank = {label: i for i, (_, label) in enumerate(reversed(scanner.ANDROID_VERSION_BANDS))}
    rank[None] = -1
    for base_score in reachable_scores():
        nudged = min(base_score + scanner.PROVISIONAL_BONUS_TOTAL, scanner.ANDROID_SCORE_MAX)
        before = scanner.android_version_from_score(base_score)
        after = scanner.android_version_from_score(nudged)
        moved = rank[after] - rank[before]
        assert moved <= 1, (
            f"provisional bonuses moved score {base_score} -> {nudged} "
            f"across {moved} version bands ({before} -> {after})"
        )


def test_score_is_clipped_to_the_documented_ceiling():
    """
    The paper and the code comments both claim a ceiling of 105. Pre-fix the
    bonuses could carry the sum to 128 (105 base + 23 bonus).
    """
    assert max(reachable_scores()) <= scanner.ANDROID_SCORE_MAX
    unclipped = max(scanner.ANDROID_LMP_BASE.values()) + scanner.ANDROID_BONUS_TOTAL
    assert unclipped > scanner.ANDROID_SCORE_MAX, (
        "clipping is now vacuous - if the tables changed so the sum can no "
        "longer exceed the ceiling, this test has stopped testing anything"
    )


def test_version_mapping_is_monotone_in_score():
    """A higher score must never map to an older Android release."""
    order = {label: i for i, (_, label) in enumerate(reversed(scanner.ANDROID_VERSION_BANDS))}
    previous = -1
    for score in range(0, scanner.ANDROID_SCORE_MAX + 1):
        label = scanner.android_version_from_score(score)
        rank = -1 if label is None else order[label]
        assert rank >= previous, f"score {score} maps backwards to {label}"
        previous = rank


if __name__ == "__main__":
    from _runner import run

    raise SystemExit(run())
