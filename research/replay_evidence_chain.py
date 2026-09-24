#!/usr/bin/env python3
"""
Offline replay of the evidence chain over the archived scans (B2).

The paper currently says the evidence chain "never triggered across 43 real
scans" and explains that as conflicts being rare. This tool re-derives the
chain from the archive to find out what actually happened, and reports, per
signal, how often it fired and - when it did not - which precondition was
missing. That distinction matters: a signal that is silent because its input
was never captured is a Layer-2 availability result (the paper's own thesis),
whereas a signal silent despite its input being present would be a code bug.

    python3 replay_evidence_chain.py
    python3 replay_evidence_chain.py --json out.json

Reads historical_scans.jsonl (full scans: CoD, name, services, Modalias) and
research/availability_raw.jsonl (the availability sweep: Appearance, connection
parameters, Modalias, SDP names, but no CoD and no device name - so the pairs
that need CoD are structurally unavailable there and are reported as such
rather than counted as failures).
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles"))

import advanced_nmap_scanner as scanner  # noqa: E402

# The scanner writes historical_scans.jsonl to a RELATIVE path, so an archive
# lands wherever it was run from. Three copies accumulated in three directories
# before this was noticed, and only the first was ever measured. All known
# locations are replayed together; check_release_clean.py's find_stray_archives()
# catches any new one.
FULL_ARCHIVES = [
    ("repo root", os.path.join(REPO_ROOT, "historical_scans.jsonl")),
    ("backend/", os.path.join(REPO_ROOT, "backend", "historical_scans.jsonl")),
    ("pythonfiles/", os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles",
                                  "historical_scans.jsonl")),
]
FULL_ARCHIVE = FULL_ARCHIVES[0][1]
SWEEP_ARCHIVE = os.path.join(SCRIPT_DIR, "availability_raw.jsonl")
PILOT_ARCHIVES = [
    ("pilot, cleaned", os.path.join(SCRIPT_DIR, "availability_raw_pilot_cleaned.jsonl")),
    ("pilot, own devices", os.path.join(SCRIPT_DIR, "availability_raw_pilot_own_devices.jsonl")),
]

# Which inputs each evidence-chain signal needs before it can fire at all.
SIGNAL_PRECONDITIONS = {
    "lmp_features_simultaneous_le_bredr": ["lmp_features", "os_is_android"],
    "modalias_chipset": ["chipset_model"],
    "gatt_appearance": ["gatt_appearance", "cod_absent"],
    "gatt_preferred_conn_params": ["gatt_conn_params", "os_is_android"],
    # Not merely "SDP records were captured": signal 5 fires per vendor_keyword
    # hint, so the real precondition is that extract_sdp_hints() found a brand
    # string in the raw text. Two sweep records carried SDP records whose only
    # vendor-ish names were "MFi Bluetooth" and "AAP Client" - Apple-specific
    # protocol names that contain no literal brand keyword, so the extractor
    # correctly produced no hint. Modelling the precondition as "records
    # present" would misreport that as a code defect.
    "sdp_service_name": ["sdp_vendor_keyword_hint"],
    "behavioral_advertising_interval_shift": ["behavioral_summary"],
    "behavioral_rssi_variance": ["behavioral_summary"],
    "cod_vs_gatt_appearance": ["cod_present", "gatt_appearance"],
    "name_vs_gatt_appearance": ["name_category", "gatt_appearance"],
    # The Appearance-free pair added after the first replay showed pairs 7 and 8
    # were both gated on the scarcest signal in the study.
    "cod_vs_device_name": ["cod_present", "name_category"],
}


def inputs_present(rec):
    """Which chain inputs a given replayed scan actually carries."""
    feat = rec.get("features", {}) or {}
    inf = rec.get("inferences", {}) or {}
    cod = (feat.get("dbus_cache", {}) or {}).get("class_of_device", "N/A")
    cod_major = scanner.decode_cod_major_class(cod)
    chipset = (feat.get("dbus_cache", {}) or {}).get("device_id_profile") or {}
    return {
        "lmp_features": bool(feat.get("lmp_features")),
        "os_is_android": inf.get("os") == "Android",
        "chipset_model": bool(chipset.get("chipset_model")),
        "gatt_appearance": bool((feat.get("gatt_appearance") or {}).get("gatt_appearance_category")),
        "cod_present": cod_major is not None,
        "cod_absent": cod_major is None,
        "gatt_conn_params": (feat.get("gatt_preferred_conn_params") or {}).get(
            "preferred_conn_interval_min_ms") is not None,
        "sdp_full_records": bool(feat.get("sdp_full_service_records")),
        "sdp_vendor_keyword_hint": any(
            h.startswith("vendor_keyword:")
            for r in (feat.get("sdp_full_service_records") or [])
            for h in (r.get("sdp_extracted_hints") or [])
        ),
        "behavioral_summary": bool(rec.get("behavioral_summary")),
        "name_category": scanner.infer_device_category_from_name(feat.get("name") or "") is not None,
    }


def replay_full_scan(rec):
    feat = rec.get("features", {}) or {}
    inf = dict(rec.get("inferences", {}) or {})
    cod = (feat.get("dbus_cache", {}) or {}).get("class_of_device", "N/A")
    chipset = (feat.get("dbus_cache", {}) or {}).get("device_id_profile") or None
    chain = scanner.build_evidence_chain(
        inf,
        cod,
        feat.get("vendor") or "",
        feat.get("name") or "",
        feat.get("lmp_features"),
        chipset,
        feat.get("gatt_appearance"),
        feat.get("gatt_preferred_conn_params"),
        feat.get("sdp_full_service_records"),
        rec.get("behavioral_summary"),
    )
    return chain, inputs_present(rec)


def sweep_record_to_scan(r):
    """
    Adapt an availability-sweep record onto the shape replay_full_scan expects.
    The sweep never recorded CoD or a device name, so those stay absent - which
    is itself the point: the CoD/Appearance pair could not have fired on this
    archive no matter what the code did.
    """
    appearance = r.get("gatt_appearance")
    if isinstance(appearance, str):
        appearance = {"gatt_appearance_category": appearance}
    conn = r.get("gatt_conn_params")
    if isinstance(conn, (int, float)):
        conn = {"preferred_conn_interval_min_ms": conn}
    chipset = None
    if r.get("modalias_chipset_resolved"):
        chipset = {"chipset_model": r["modalias_chipset_resolved"],
                   "estimated_chipset_release_year": None,
                   "estimated_min_os_hint": None}
    sdp_records = None
    if r.get("sdp_records_raw"):
        sdp_records = r["sdp_records_raw"] if isinstance(r["sdp_records_raw"], list) else None
    return {
        "features": {
            "vendor": r.get("modalias_vendor_resolved") or "",
            "name": "",
            "dbus_cache": {"class_of_device": "N/A", "device_id_profile": chipset},
            "gatt_appearance": appearance,
            "gatt_preferred_conn_params": conn,
            "sdp_full_service_records": sdp_records,
            "lmp_features": None,
        },
        "inferences": {"device_type": "Unknown Peripheral", "os": "Unknown",
                       "major_minor_version": "Unknown", "confidence": "Low"},
    }


def load(path, adapter=None):
    out = []
    if not os.path.exists(path):
        return out
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            out.append(adapter(rec) if adapter else rec)
    return out


def report(label, scans, stored_chain_counts=None):
    fired = {name: 0 for name in SIGNAL_PRECONDITIONS}
    # Direction matters as much as the count: the chain is specified to record
    # agreement as well as disagreement, so "fired" alone would hide whether it
    # is doing both jobs or only one.
    directions = {name: {} for name in SIGNAL_PRECONDITIONS}
    blocked_by = {name: {} for name in SIGNAL_PRECONDITIONS}
    nonempty = 0
    total_entries = 0

    for rec in scans:
        chain, present = replay_full_scan(rec)
        if chain:
            nonempty += 1
        total_entries += len(chain)
        seen = {e["signal_name"] for e in chain}
        for e in chain:
            d = directions.setdefault(e["signal_name"], {})
            d[e["direction"]] = d.get(e["direction"], 0) + 1
        for name, needs in SIGNAL_PRECONDITIONS.items():
            if name in seen:
                fired[name] += 1
                continue
            missing = [n for n in needs if not present.get(n)]
            key = ", ".join(missing) if missing else "(inputs present - INVESTIGATE)"
            blocked_by[name][key] = blocked_by[name].get(key, 0) + 1

    n = len(scans)
    print(f"=== {label} ===")
    print(f"scans replayed:            {n}")
    if stored_chain_counts is not None:
        print(f"scans whose stored record  {stored_chain_counts} "
              f"(the rest predate the feature)")
        print("already had an evidence_chain field")
    print(f"scans with >=1 chain entry: {nonempty}"
          + (f"  ({100.0 * nonempty / n:.1f}%)" if n else ""))
    print(f"total chain entries:        {total_entries}")
    print()
    print(f"{'signal':<40}{'fired':>7}   blocked because")
    for name in SIGNAL_PRECONDITIONS:
        reasons = sorted(blocked_by[name].items(), key=lambda kv: -kv[1])
        dirs = directions.get(name) or {}
        dir_note = ""
        if dirs:
            dir_note = " [" + ", ".join(f"{k} {v}" for k, v in sorted(dirs.items())) + "]"
        head = f"{name:<40}{str(fired[name]) + dir_note:>7}   "
        if not reasons:
            print(head + "-")
        else:
            print(head + f"missing {reasons[0][0]} ({reasons[0][1]})")
            for r, c in reasons[1:]:
                print(" " * 50 + f"missing {r} ({c})")
    print()
    return {"scans": n, "scans_with_entries": nonempty,
            "total_entries": total_entries, "fired": fired,
            "directions": directions, "blocked_by": blocked_by}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="write the full replay summary here")
    args = ap.parse_args()

    full = []
    for label, path in FULL_ARCHIVES:
        part = load(path)
        if part:
            print(f"  loaded {len(part):>3} scan(s) from {label}")
            full.extend(part)
    print()
    stored = sum(1 for r in full if "evidence_chain" in (r.get("inferences") or {}))
    devices = {(r.get("features") or {}).get("mac") for r in full}
    res_full = report(f"all full-scan archives ({len(devices)} distinct devices)", full,
                      stored_chain_counts=f"{stored} of {len(full)}")

    sweep = load(SWEEP_ARCHIVE, adapter=sweep_record_to_scan)
    res_sweep = report("research/availability_raw.jsonl (availability sweep)", sweep)

    res_pilots = {}
    for label, path in PILOT_ARCHIVES:
        recs = load(path, adapter=sweep_record_to_scan)
        if recs:
            res_pilots[label] = report(f"{os.path.basename(path)} ({label})", recs)

    print("Any row above reading '(inputs present - INVESTIGATE)' is a code")
    print("defect: the signal's preconditions held and it still did not fire.")
    print("Every other zero is an availability result, not a bug.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"historical_scans": res_full,
                       "availability_sweep": res_sweep,
                       "pilots": res_pilots}, fh, indent=2)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
