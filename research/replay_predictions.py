#!/usr/bin/env python3
"""
Offline replay of every archived scan through the prediction engine, so the
numbers quoted in the paper can be regenerated from the archive instead of
being carried forward by hand.

Written for B1: the Android version ladder was rebuilt (integer raw score,
non-decreasing LMP base, clipped after bonuses - see ANDROID_VERSION_BANDS in
advanced_nmap_scanner.py). This tool reruns the archive under BOTH the old and
the new ladder and prints every prediction that moved, so the change is
auditable rather than asserted.

    python3 replay_predictions.py                 # summary + changed rows
    python3 replay_predictions.py --json out.json # machine-readable dump

No network and no Bluetooth adapter are touched: every input is read back out
of historical_scans.jsonl. Records the archive doesn't carry (the C helper's
own estimate, LMP feature bitmap, GATT connection parameters) are replayed as
absent, which is how they were on those scans.
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles"))

import advanced_nmap_scanner as scanner  # noqa: E402

ARCHIVE = os.path.join(REPO_ROOT, "historical_scans.jsonl")


# --- the pre-B1 ladder, kept verbatim for comparison only -------------------
# Reproduced exactly as it stood before the fix (git a0f8c64) so the "what
# changed" column is a real diff and not a reconstruction from memory.
OLD_LMP_BASE = {14: 105, 13: 98, 12: 88, 11: 85, 10: 68, 9: 85,
                8: 48, 7: 25, 6: 15, 5: 10, 4: 5}


def old_ladder_version(lmp_int, flags, is_missing_data):
    score = 0
    if lmp_int >= 14:
        score += 105
    else:
        score += OLD_LMP_BASE.get(lmp_int, 0)
    if flags["a2dp"]: score += 2
    if flags["hfp"]: score += 2
    if flags["map"]: score += 2
    if flags["pbap"]: score += 2
    if flags["opp"]: score += 1
    if flags["did"]: score += 6
    if lmp_int >= 11 and flags["did"]: score += 6

    weighted = (score / 105.0) * 10.0
    if weighted >= 9.8: return score, "Android 16 (Baklava)"
    if weighted >= 9.2: return score, "Android 15 (Vanilla Ice Cream)"
    if weighted >= 8.2: return score, "Android 14 (Upside Down Cake)"
    if weighted >= 7.2: return score, "Android 13 (Tiramisu)"
    if weighted >= 7.15: return score, "Android 12 (Snow Cone)"
    if weighted >= 7.0: return score, "Android 11 (Red Velvet Cake)"
    if weighted >= 4.0: return score, "Android 10 (Q)"
    if weighted >= 3.5: return score, "Android 9.0 (Pie)"
    if weighted >= 3.0: return score, "Android 8.0/8.1 (Oreo)"
    return score, ("Android (Unknown Version - Hardware Profile Missing)"
                   if is_missing_data else "Android 7.0 or older")


def new_ladder_version(lmp_int, flags, is_missing_data):
    score = scanner.android_lmp_base(lmp_int)
    b = scanner.ANDROID_BONUSES
    if flags["a2dp"]: score += b["a2dp"]
    if flags["hfp"]: score += b["hfp"]
    if flags["map"]: score += b["map"]
    if flags["pbap"]: score += b["pbap"]
    if flags["opp"]: score += b["opp"]
    if flags["did"]: score += b["did"]
    if lmp_int >= 11 and flags["did"]: score += b["did_modern_lmp"]
    score = max(0, min(score, scanner.ANDROID_SCORE_MAX))
    version = scanner.android_version_from_score(score)
    if version is None:
        version = ("Android (Unknown Version - Hardware Profile Missing)"
                   if is_missing_data else "Android 7.0 or older")
    return score, version


def replay_record(rec):
    """Rebuild one archived scan's scoring inputs. Returns None if it never
    reached the Android branch (so the ladder was irrelevant to it)."""
    feat = rec.get("features", {})
    hw = feat.get("hardware_info", {}) or {}
    lmp_int = hw.get("lmp_integer", 0) or 0
    services = feat.get("services", []) or []
    vendor = feat.get("vendor", "") or ""
    name = feat.get("name", "") or ""
    cod_hex = (feat.get("dbus_cache", {}) or {}).get("class_of_device", "N/A")

    flags = scanner.sdp_flags_from_service_names(services)

    # Reproduce predict_device_core's own Android-branch gate.
    is_apple = "apple" in vendor.lower() or "apple" in (hw.get("manufacturer", "") or "").lower()
    if is_apple:
        return None
    cod_major = scanner.decode_cod_major_class(cod_hex)
    cod_says_not_phone = cod_major is not None and cod_major != 2
    vendor_phone = any(x in vendor.lower() for x in
                       ["samsung", "pixel", "motorola", "xiaomi", "oneplus", "huawei", "oppo", "vivo"])
    is_android_phone = (flags["pbap"] or flags["map"] or "android" in name.lower()
                        or (not cod_says_not_phone and vendor_phone))
    if not is_android_phone:
        return None

    is_missing_data = lmp_int == 0
    old_score, old_version = old_ladder_version(lmp_int, flags, is_missing_data)
    new_score, new_version = new_ladder_version(lmp_int, flags, is_missing_data)
    return {
        "mac": feat.get("mac"),
        "name": name,
        "vendor": vendor,
        "lmp_integer": lmp_int,
        "flags": {k: v for k, v in flags.items() if k != "failed"},
        "old_score": old_score,
        "old_version": old_version,
        "new_score": new_score,
        "new_version": new_version,
        "changed": old_version != new_version,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", default=ARCHIVE)
    ap.add_argument("--json", help="write the full per-record replay here")
    args = ap.parse_args()

    total = 0
    replayed = []
    with open(args.archive) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            total += 1
            out = replay_record(json.loads(line))
            if out is not None:
                replayed.append(out)

    changed = [r for r in replayed if r["changed"]]
    print(f"archive:            {args.archive}")
    print(f"scans in archive:   {total}")
    print(f"reached Android:    {len(replayed)}")
    print(f"prediction changed: {len(changed)}")
    print()
    print("NOTE: the ladder is replayed without the C helper's own")
    print("estimated_android string, which the archive does not record. That")
    print("string used to short-circuit the ladder on a live scan, so labels")
    print("replayed here could differ from what the live pipeline emitted.")
    print("It no longer does: predict_device_core now scores every device on")
    print("this one ladder and uses the helper only for the LMP integer and")
    print("the profile flags, so a replay and a live scan agree by construction.")
    print()

    if changed:
        print("changed predictions (old -> new):")
        for r in changed:
            print(f"  {r['mac']}  LMP {r['lmp_integer']:>2}  "
                  f"score {r['old_score']} -> {r['new_score']}")
            print(f"      {r['name']}")
            print(f"      {r['old_version']}  ->  {r['new_version']}")
    else:
        print("no archived prediction changed under the new ladder.")

    print()
    print("distribution under the new ladder:")
    dist = {}
    for r in replayed:
        dist[r["new_version"]] = dist.get(r["new_version"], 0) + 1
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>3}  {k}")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"total_scans": total, "records": replayed}, fh, indent=2)
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
