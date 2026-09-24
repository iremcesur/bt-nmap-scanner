#!/usr/bin/env python3
"""
Test-retest stability over repeated scans of the same device.

This measures RELIABILITY, not accuracy. It asks a question that needs no
ground truth: when the same physical device is scanned more than once, does
the pipeline return the same answer? Two scans of one device that disagree
cannot both be right, so a disagreement falsifies something without anyone
having to know what the device actually runs. Agreement, by contrast, proves
nothing at all - a systematically biased scorer agrees with itself - which is
why this script reports disagreement counts and never an "agreement rate".

Two quantities are reported per device:

  signal availability   which Layer 0-2 signals resolved on each scan. Signals
                        that come and go are the mechanism behind unstable
                        predictions: a branch condition that depends on a
                        signal missing from one scan takes a different path.

  prediction stability  distinct (device type, OS) pairs emitted across that
                        device's scans. More than one means the pipeline
                        contradicted itself.

The archive spans several weeks and several revisions of the scorer, so a
device scanned in June and again in August can differ simply because the code
changed in between - that is a version difference, not an instability. The
headline figure is therefore computed WITHIN a session window (default: one
calendar day), where the code is necessarily identical. Cross-session
disagreements are reported separately and marked as confounded.

Usage:  python3 research/retest_stability.py [--csv research_evaluation.csv]
                                             [--session-window DAYS]
"""

import argparse
import collections
import csv
import os
import sys

# Signals whose presence/absence can change which branch predict_device_core
# takes. "Resolved" is per-signal because each has its own empty encoding.
ABSENT = {"", "N/A", "None", "Unknown", "0", "[]", "{}"}


def resolved(row, column):
    return str(row.get(column, "")).strip() not in ABSENT


def signal_profile(row):
    """The set of branch-relevant signals that resolved on this scan."""
    profile = set()
    if resolved(row, "Class of Device"):
        profile.add("cod")
    if resolved(row, "Modalias"):
        profile.add("modalias")
    if resolved(row, "Device Name"):
        profile.add("name")
    if resolved(row, "GATT UUIDs"):
        profile.add("gatt_uuids")
    if resolved(row, "SDP Handles"):
        profile.add("sdp")
    if resolved(row, "GATT Appearance Category"):
        profile.add("appearance")
    # LMP is reported as a version string; "(0x0)" / absent both mean no read.
    lmp = str(row.get("LMP Version", "")).strip()
    if lmp not in ABSENT and "0x0)" not in lmp:
        profile.add("lmp")
    return profile


def session_key(row, window_days):
    """
    Scans grouped into a session, within which the scorer revision is assumed
    constant. Timestamps are 'YYYY-MM-DD HH:MM:SS', so the date prefix is the
    day; a wider window buckets consecutive days together.
    """
    stamp = str(row.get("Timestamp", "")).strip()
    date = stamp.split(" ")[0]
    if window_days <= 1 or not date:
        return date
    try:
        year, month, day = (int(p) for p in date.split("-"))
    except ValueError:
        return date
    import datetime
    ordinal = datetime.date(year, month, day).toordinal()
    return f"bucket-{ordinal // window_days}"


def prediction(row):
    return (
        str(row.get("Predicted Device Type", "")).strip(),
        str(row.get("Predicted OS", "")).strip(),
    )


def main():
    ap = argparse.ArgumentParser()
    default_csv = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research_evaluation.csv",
    )
    ap.add_argument("--csv", default=default_csv)
    ap.add_argument("--min-scans", type=int, default=2,
                    help="only devices scanned at least this many times")
    ap.add_argument("--session-window", type=int, default=1,
                    help="days of scans treated as one session, within which "
                         "the scorer revision is assumed constant (default 1)")
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        print(f"no such file: {args.csv}", file=sys.stderr)
        return 1

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    by_mac = collections.OrderedDict()
    for row in rows:
        mac = str(row.get("MAC Address", "")).strip()
        if mac:
            by_mac.setdefault(mac, []).append(row)

    repeated = {m: rs for m, rs in by_mac.items() if len(rs) >= args.min_scans}

    print(f"source:            {args.csv}")
    print(f"scans:             {len(rows)}")
    print(f"distinct devices:  {len(by_mac)}")
    print(f"scanned >= {args.min_scans}x:    {len(repeated)}")
    print(f"session window:    {args.session_window} day(s)")
    print()
    print("This is test-retest RELIABILITY, not accuracy. A disagreement means")
    print("at least one of the two scans is wrong; an agreement means nothing,")
    print("because a biased scorer agrees with itself. Only disagreements are")
    print("evidence. Within-session figures are the headline: across sessions")
    print("the scorer revision may differ, which confounds the comparison.")
    print()

    within_devices = 0            # devices with a repeated session at all
    within_unstable = []          # ... that disagreed inside one session
    cross_only_unstable = []      # disagreed only across sessions (confounded)
    volatile_signals = collections.Counter()
    total_sessions = 0
    unstable_sessions = 0

    for mac, scans in repeated.items():
        name = next((str(r.get("Device Name", "")).strip() for r in scans
                     if resolved(r, "Device Name")), "Unknown")

        sessions = collections.OrderedDict()
        for row in scans:
            sessions.setdefault(session_key(row, args.session_window), []).append(row)
        repeat_sessions = {k: v for k, v in sessions.items() if len(v) >= 2}

        profiles = [signal_profile(r) for r in scans]
        always = set.intersection(*profiles)
        flaky = set.union(*profiles) - always
        for signal in flaky:
            volatile_signals[signal] += 1

        all_preds = collections.Counter(prediction(r) for r in scans)
        session_unstable = {}
        for key, group in repeat_sessions.items():
            total_sessions += 1
            preds = collections.Counter(prediction(r) for r in group)
            if len(preds) > 1:
                unstable_sessions += 1
                session_unstable[key] = preds

        if repeat_sessions:
            within_devices += 1

        verdict = ""
        if session_unstable:
            verdict = "  <-- UNSTABLE within a session"
        elif len(all_preds) > 1:
            verdict = "  <-- differs across sessions only (confounded)"
        print(f"{mac}  n={len(scans):<3} {name}{verdict}")
        print(f"    signals always present:     {sorted(always) or '-'}")
        if flaky:
            print(f"    signals that came and went: {sorted(flaky)}")
        print(f"    sessions: {len(sessions)} "
              f"({len(repeat_sessions)} with a repeat scan)")
        for (dtype, os_str), count in all_preds.most_common():
            print(f"    [{count}x] {dtype:<28} | {os_str}")
        for key, preds in session_unstable.items():
            answers = " / ".join(f"{d}" for d, _o in preds)
            print(f"    session {key}: {len(preds)} different answers -> {answers}")
        print()

        if session_unstable:
            within_unstable.append((mac, name, session_unstable, flaky))
        elif len(all_preds) > 1:
            cross_only_unstable.append((mac, name, all_preds))

    print("=" * 66)
    print(f"devices with a same-session repeat scan:   {within_devices}")
    print(f"  ... that contradicted themselves:        {len(within_unstable)}")
    print(f"sessions containing a repeat scan:         {total_sessions}")
    print(f"  ... that contained a contradiction:      {unstable_sessions}")
    print(f"devices differing only across sessions:    "
          f"{len(cross_only_unstable)} (confounded by code revision)")
    if volatile_signals:
        print()
        print("signals that varied across scans of one device (device count):")
        for signal, count in volatile_signals.most_common():
            print(f"    {signal:<12} {count}")
    print()
    for mac, name, session_unstable, flaky in within_unstable:
        print(f"{mac} ({name}): contradicted itself in "
              f"{len(session_unstable)} session(s); "
              f"unstable signals: {sorted(flaky) or 'none - branch is unstable '
              'under identical signal availability'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
