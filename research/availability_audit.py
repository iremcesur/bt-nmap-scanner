#!/usr/bin/env python3
"""
Layer 2 signal availability audit.

Answers one question: of the Bluetooth devices actually encountered in the
wild, what fraction expose GATT Appearance, GATT Preferred Connection
Parameters, a Modalias resolvable to a known chipset, and a usable SDP
service name? This is a standalone research tool, not part of the served
app - it imports the relevant query functions directly from
advanced_nmap_scanner.py so there's exactly one implementation of each
query, but runs none of the unrelated deep-scan probes (RTT, baseband
metrics, AFH, MTU test, etc.) that main() normally also runs, since those
aren't needed to answer this question and would only slow this down.

Every candidate MAC address stays in the denominator even when the
connection itself fails outright - dropping unreachable devices would
silently condition the reported percentages on "devices we could connect
to," which is a form of selection bias and would misrepresent Layer 2's
real-world ceiling. A device we can't connect to gives zero Layer 2 signal,
which is itself part of the answer.

Two-phase, run independently and repeatedly:

  python3 availability_audit.py --discover
      One passive scan (~6s, no connections made). Run this several times,
      in different locations/sessions, to accumulate a varied candidate
      list. Newly seen MACs are merged into candidates.json; MACs already
      known are left alone (their first_seen timestamp doesn't change).

  python3 availability_audit.py --measure
      Runs the active Layer 2 queries against every candidate MAC not yet
      measured, appending one JSON record per device to
      availability_raw.jsonl as it goes (so an interruption partway through
      loses nothing already completed), then reprints the aggregate table.

  python3 availability_audit.py --report
      Just reprints the aggregate table from whatever is already in
      availability_raw.jsonl, without discovering or measuring anything new.

No OS inference and no owner mapping is performed or recorded, since this
measures signal *availability*, not device identity. But two identifiers ARE
written to the archive in cleartext and should not be glossed as "no identity":
the MAC address, and the device's own advertised name. Both can be personal
data under GDPR Art. 4(1) where they link to a natural person, and advertised
names often carry one directly. Before any release, run
pseudonymize_archive.py over every archive with one shared salt and then
check_release_clean.py as a gate; see research/DATA_RETENTION.md for the
retention and deletion schedule.

candidates.json and availability_raw.jsonl are never deleted when the
schema or a resolution table changes in a way that makes a prior round no
longer comparable to new data - they are renamed to
<name>.stale_<reason> instead (see availability_raw.jsonl.stale_pre_fix,
.stale_gatttool_broken, .stale_pre_taxonomy for precedent) and a fresh pair
of files is started. This keeps every round's raw output auditable rather
than silently overwritten.
"""

import sys
import os
import json
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHONFILES_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "backend", "routes", "pythonfiles"))
sys.path.insert(0, PYTHONFILES_DIR)

from advanced_nmap_scanner import (  # noqa: E402
    query_gatt_appearance,
    query_gatt_preferred_conn_params,
    query_dbus_properties,
    decode_modalias,
    enrich_modalias_with_chipset,
    lookup_company_id,
    get_sdp_full_service_details,
)

DISCOVER_SCRIPT = os.path.join(PYTHONFILES_DIR, "discover_devices.py")
CANDIDATES_FILE = os.path.join(SCRIPT_DIR, "candidates.json")
RESULTS_FILE = os.path.join(SCRIPT_DIR, "availability_raw.jsonl")


def load_candidates():
    if not os.path.isfile(CANDIDATES_FILE):
        return {}
    with open(CANDIDATES_FILE) as f:
        return json.load(f)


def save_candidates(candidates):
    with open(CANDIDATES_FILE, "w") as f:
        json.dump(candidates, f, indent=2)


def load_measured_macs():
    measured = set()
    if os.path.isfile(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    measured.add(json.loads(line)["mac"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return measured


def run_discover():
    print("[discover] Running passive scan (~6s, no connections made)...")
    try:
        result = subprocess.run(["python3", DISCOVER_SCRIPT], capture_output=True, text=True, timeout=20)
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"[discover] Failed: {e}")
        return

    if "error" in data:
        print(f"[discover] BlueZ/D-Bus error: {data['error']}")

    candidates = load_candidates()
    new_count = 0
    for device in data.get("devices", []):
        mac = device.get("mac")
        if not mac or mac == "Unknown":
            continue
        if mac not in candidates:
            candidates[mac] = {
                "name": device.get("name"),
                "device_type": device.get("device_type"),
                "first_seen": datetime.now().isoformat(timespec="seconds"),
            }
            new_count += 1
    save_candidates(candidates)
    print(f"[discover] {len(data.get('devices', []))} device(s) seen this pass, "
          f"{new_count} new. Total candidates so far: {len(candidates)}")
    print("[discover] Run again in a different location/session to add more, "
          "or run --measure when ready.")


def classify_failure_reason(raw_reason):
    """
    Buckets a raw failure string (a D-Bus exception message from the GATT
    queries, or sdptool's stderr from the SDP query) into a coarse failure
    taxonomy category. These map to genuinely different real-world causes -
    a device using non-connectable advertising, one filtering by bond/
    allowlist, an HCI page timeout, or simply being out of range - which the
    pooled "16 of 20 refused a connection" figure otherwise flattens into one
    number. The raw string is always kept alongside the bucket in the record
    (see measure_one) since this mapping is necessarily incomplete and
    reclassification later must not require re-scanning.
    """
    if not raw_reason:
        return None
    msg = raw_reason.lower()
    if "unknownobject" in msg:
        return "device_unknown_to_bluez"
    if "noreply" in msg or "timed out" in msg or "timeout" in msg:
        return "dbus_or_scan_timeout"
    if "notconnected" in msg or "not connected" in msg:
        return "not_connected"
    if "host is down" in msg:
        return "page_timeout_or_out_of_range"
    if "connection refused" in msg:
        return "connection_refused"
    if "no route to host" in msg:
        return "no_route_to_host"
    if "unknownproperty" in msg or "invalidargs" in msg or "does not exist" in msg or "not found in gatt tree" in msg:
        return "signal_not_present"
    return "other"


def reached_from_record(r):
    """
    Was the device actually REACHED this run, independent of whether it
    yielded any of our three Layer 2 signals?

    This is deliberately distinct from "connectable" as recorded in
    measure_one. A device can open a connection / be enumerable and still
    expose none of GATT Appearance, Preferred Connection Parameters, or a
    usable SDP service name - a reachable-but-quiet device. The earlier
    version of this audit set connectable=True only when a signal returned a
    VALUE, so such a device landed in the "connection failed" bucket, which
    (a) inflated the connection-failure count and (b) made "% of connectable
    devices exposing signal X" partly circular, since connectable was itself
    defined by exposing a signal.

    A device is treated as reached if any query returned a value, OR if any
    query failed specifically with a signal_not_present-class reason (the
    characteristic/service was absent from an otherwise-reachable device),
    as opposed to a connection-level failure (UnknownObject, page timeout,
    host down, refused, D-Bus/scan timeout, not-connected).

    Computed only from fields already stored per record, so it applies
    retroactively to records written before this field existed - no
    re-scan needed (same raw-keeping principle as measure_one point 4).
    """
    if (r.get("gatt_appearance") or r.get("gatt_conn_params")
            or r.get("sdp_service_name") or r.get("sdp_records_raw")):
        return True
    # A signal_not_present failure proves reachability ONLY for queries whose
    # error reliably distinguishes "device enumerated, characteristic absent"
    # from "device never reached". The GATT Appearance query does: it returns
    # UnknownObject when BlueZ has no object for the device (not reached) and
    # InvalidArgs/"No such property" when the device is present but exposes no
    # Appearance (reached-but-quiet). The Preferred-Connection-Parameters
    # query does NOT: it reports "characteristic 0x2A04 not found in GATT
    # tree" unconditionally, even when the tree was never resolved because the
    # device was unreachable, so its signal_not_present is spurious and is
    # deliberately excluded here. (That query's own error reporting is a
    # separate bug to fix in advanced_nmap_scanner.py; until then its VALUE is
    # still trustworthy, only its failure_reason is not.)
    for cat_key in ("appearance_failure_category", "sdp_failure_category"):
        if r.get(cat_key) == "signal_not_present":
            return True
    return False


def measure_one(mac):
    """
    Runs only the four Layer 2 queries this audit cares about. Each is
    independent: a failure in one (e.g. GATT read times out) must not
    prevent the others from being attempted, since they use different
    underlying protocols (GATT vs SDP vs D-Bus cache) and can fail
    independently of each other.

    Three deliberate design choices, all corrections after reviewing earlier
    passes of this script:

    1. Modalias resolution is tracked as THREE separate outcomes, not one -
       "field present" (a real availability signal), "vendor resolved" (via
       the Bluetooth SIG company ID / USB-IF vendor tables, which are close
       to comprehensive), and "chipset model resolved" (against our own tiny
       hand-seeded chipset_database.py, which will never be more than
       partially complete). Collapsing these into one "resolved" boolean
       would conflate a real device-behavior signal with our own database's
       current coverage - the first is what Section 4.3 cares about
       measuring, the second just tracks how much of chipset_database.py has
       been filled in so far.

    2. "connectable" is set ONLY by GATT/SDP success, never by Modalias.
       query_dbus_properties() reads BlueZ's cached device properties, which
       can be populated from a PRIOR pairing session without any live
       connection happening right now - most devices in a typical candidate
       list are already `"paired": true` from earlier use, so letting
       Modalias presence count as "connectable" would silently inflate that
       number with devices we didn't actually reach live during this scan.

    3. Each of the three connection-gated queries now returns (value,
       failure_reason) rather than swallowing its exception - failure_reason
       is recorded raw per signal AND run through classify_failure_reason()
       above, so a "16 of 20 refused" figure can be broken down into why
       (non-connectable advertising vs bonded/allowlist filtering vs page
       timeout vs out of range) instead of one opaque bucket.

    4. The raw Modalias string and the full parsed SDP record list are now
       stored alongside their resolved/summarized values (modalias_raw,
       sdp_records_raw below), not just the vendor/chipset name or first
       service name derived from them. Resolution tables
       (bluetooth_company_ids.py, chipset_database.py) will keep improving
       after this data is collected - the pilot round run before this fix
       stored only resolved values, so today's company-ID table expansion
       could not be applied to it retroactively without re-scanning
       hardware (see research/availability_raw.jsonl.stale_pre_taxonomy).
       Keeping the raw signal means a future table improvement can be
       replayed against already-collected records instead of requiring a
       new scan - the same principle Section 4.3's ablation design applies
       to scorer configurations.
    """
    record = {
        "mac": mac,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "reached": False,
        "connectable": False,
        "gatt_appearance": None,
        "gatt_conn_params": None,
        "modalias_present": False,
        "modalias_raw": None,
        "modalias_vendor_resolved": None,
        "modalias_chipset_resolved": None,
        "sdp_service_name": None,
        "sdp_records_raw": None,
        "appearance_failure_reason": None,
        "appearance_failure_category": None,
        "conn_params_failure_reason": None,
        "conn_params_failure_category": None,
        "sdp_failure_reason": None,
        "sdp_failure_category": None,
        "errors": [],
    }

    try:
        appearance, reason = query_gatt_appearance(mac)
        if appearance:
            record["gatt_appearance"] = appearance
            record["connectable"] = True
        else:
            record["appearance_failure_reason"] = reason
            record["appearance_failure_category"] = classify_failure_reason(reason)
    except Exception as e:
        record["errors"].append(f"appearance: {e}")

    try:
        conn_params, reason = query_gatt_preferred_conn_params(mac)
        if conn_params:
            record["gatt_conn_params"] = conn_params
            record["connectable"] = True
        else:
            record["conn_params_failure_reason"] = reason
            record["conn_params_failure_category"] = classify_failure_reason(reason)
    except Exception as e:
        record["errors"].append(f"conn_params: {e}")

    try:
        dbus_props = query_dbus_properties(mac)
        modalias = dbus_props.get("modalias") if dbus_props else None
        if modalias and modalias != "N/A":
            record["modalias_present"] = True
            record["modalias_raw"] = modalias
            # Deliberately NOT setting connectable here - see docstring point 2.
            device_id_info = decode_modalias(modalias)
            if device_id_info:
                device_id_info["vendor_name"] = lookup_company_id(device_id_info["vendor_id"])
                device_id_info = enrich_modalias_with_chipset(device_id_info)
                if device_id_info.get("chipset_vendor"):
                    record["modalias_vendor_resolved"] = device_id_info["chipset_vendor"]
                if device_id_info.get("chipset_model"):
                    record["modalias_chipset_resolved"] = device_id_info["chipset_model"]
    except Exception as e:
        record["errors"].append(f"modalias: {e}")

    try:
        sdp_records, reason = get_sdp_full_service_details(mac)
        if sdp_records:
            record["connectable"] = True
            record["sdp_records_raw"] = sdp_records
            named = [r["service_name_raw"] for r in sdp_records if r.get("service_name_raw")]
            if named:
                record["sdp_service_name"] = named[0]
        if reason:
            record["sdp_failure_reason"] = reason
            record["sdp_failure_category"] = classify_failure_reason(reason)
    except Exception as e:
        record["errors"].append(f"sdp: {e}")

    # "connectable" above means "yielded >=1 Layer 2 signal value". "reached"
    # is the weaker, non-circular fact: we actually talked to the device,
    # even if it exposed none of our three signals (see reached_from_record).
    record["reached"] = reached_from_record(record)

    return record


def run_measure():
    candidates = load_candidates()
    if not candidates:
        print("No candidates yet. Run --discover first (one or more times), then --measure.")
        return

    already_measured = load_measured_macs()
    todo = [mac for mac in candidates if mac not in already_measured]

    if not todo:
        print(f"All {len(candidates)} known candidate(s) already measured. "
              f"Run --discover to find more, or --report to just see the table again.")
    else:
        print(f"Measuring {len(todo)} new device(s) "
              f"({len(already_measured)} already measured in a prior run)...")
        with open(RESULTS_FILE, "a") as f:
            for i, mac in enumerate(todo, 1):
                name = candidates[mac].get("name") or "Unknown"
                print(f"  [{i}/{len(todo)}] {mac} ({name}) ...", end=" ", flush=True)
                record = measure_one(mac)
                f.write(json.dumps(record) + "\n")
                f.flush()
                print("connectable" if record["connectable"] else "NO CONNECTION")

    print_report()


def print_report():
    if not os.path.isfile(RESULTS_FILE):
        print("No measurements yet. Run --discover then --measure first.")
        return

    records = []
    with open(RESULTS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    total = len(records)
    if total == 0:
        print("No measurements yet.")
        return

    # Two distinct facts, kept separate to avoid the circularity in the
    # earlier version of this report:
    #   reached      - we actually talked to the device this run (recomputed
    #                  from stored fields, so it applies to old records too).
    #   connectable  - the device yielded at least one Layer 2 signal VALUE.
    # A device can be reached but expose no signal ("reached but quiet"); the
    # old report counted those as connection failures, which both inflated
    # the failure count and made "% of connectable exposing signal X"
    # partly tautological (connectable was defined by exposing a signal).
    reached = sum(1 for r in records if reached_from_record(r))
    connectable = sum(1 for r in records if r.get("connectable"))
    reached_quiet = sum(1 for r in records
                        if reached_from_record(r) and not r.get("connectable"))

    live_fields = [
        ("GATT Appearance", "gatt_appearance"),
        ("Preferred Conn Params", "gatt_conn_params"),
        ("SDP Service Name", "sdp_service_name"),
    ]

    print("\n" + "=" * 78)
    print(f"AVAILABILITY REPORT  (n={total} attempted, {reached} reached, "
          f"{total - reached} never reached)")
    print(f"  of the {reached} reached: {connectable} exposed >=1 Layer 2 signal, "
          f"{reached_quiet} reached but exposed none")
    print("=" * 78)
    print(f"{'Signal':<30}{'Present':>9}{'% of all':>12}{'% of reached':>20}")
    print("-" * 78)
    for label, key in live_fields:
        present = sum(1 for r in records if r.get(key))
        pct_all = (present / total * 100) if total else 0.0
        pct_reached = (present / reached * 100) if reached else 0.0
        print(f"{label:<30}{present:>9}{pct_all:>11.1f}%{pct_reached:>19.1f}%")

    print("-" * 78)
    print("Modalias (from BlueZ's cache; may be present without reaching the device live):")
    # Two denominators, both printed, because they answer different questions
    # and a single unlabelled percentage silently picks one and reads as the
    # other:
    #   "% of all"     - how often is Modalias available in the wild? The
    #                    operationally honest number, and the one the paper's
    #                    availability claim needs.
    #   "% of reached" - given that we opened a channel at all, how often was
    #                    it there? Conditioned on reachability, so it is NOT a
    #                    population estimate.
    # Modalias is the one signal where these can diverge sharply in BOTH
    # directions: it is a host-cache read, so it can be present on a device we
    # never reached live (inflating "% of all" relative to the live signals)
    # while the reached set stays tiny. The "% of reached" column was
    # previously left blank here for exactly that reason; blank was the wrong
    # call - the fix is to print both and label what each conditions on, not
    # to withhold one.
    modalias_fields = [
        ("  Field present (raw string)", "modalias_present"),
        ("  Vendor resolved", "modalias_vendor_resolved"),
        ("  Chipset model resolved", "modalias_chipset_resolved"),
    ]
    for label, key in modalias_fields:
        present = sum(1 for r in records if r.get(key))
        present_reached = sum(1 for r in records if r.get(key) and reached_from_record(r))
        pct_all = (present / total * 100) if total else 0.0
        pct_reached = (present_reached / reached * 100) if reached else 0.0
        print(f"{label:<30}{present:>9}{pct_all:>11.1f}%{pct_reached:>19.1f}%")
    if reached and reached < 10:
        print(f"  NOTE: n={reached} reached. Report these as raw counts, not")
        print("  percentages - a percentage over single digits reads as an")
        print("  estimate it cannot support.")

    print("-" * 78)
    not_reached = [r for r in records if not reached_from_record(r)]
    print(f"Failure taxonomy ({len(not_reached)} never-reached device(s) - why the connection "
          f"attempt failed, not just that it did; reached-but-quiet devices are "
          f"excluded here and counted above):")
    if not_reached:
        # sdp_failure_category was meant to be the primary signal (it comes
        # from an actual Classic BR/EDR connect attempt), but in practice
        # sdptool exits 0 with empty output - not an error - against most
        # BLE-only devices in this candidate pool, so it's None for nearly
        # every record and can't carry the taxonomy on its own. Fall back
        # through appearance_failure_category then conn_params_failure_category,
        # which measure_one() populates from real GATT D-Bus errors
        # (UnknownObject, characteristic-not-found, timeouts, etc.) on every
        # connection attempt. Only records with ALL THREE categories unset -
        # genuinely pre-taxonomy scans - fall through to
        # "reason_not_recorded (pre-taxonomy scan)".
        from collections import Counter

        def primary_category(r):
            return (
                r.get("sdp_failure_category")
                or r.get("appearance_failure_category")
                or r.get("conn_params_failure_category")
                or "reason_not_recorded (pre-taxonomy scan)"
            )

        categories = Counter(primary_category(r) for r in not_reached)
        for category, count in categories.most_common():
            pct = count / len(not_reached) * 100
            print(f"  {category:<45}{count:>5}  ({pct:.1f}%)")
    print("=" * 78)
    print(f"Raw per-device results : {RESULTS_FILE}")
    print(f"Candidate list         : {CANDIDATES_FILE}")


def main():
    valid_modes = ("--discover", "--measure", "--report")
    if len(sys.argv) < 2 or sys.argv[1] not in valid_modes:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "--discover":
        run_discover()
    elif mode == "--measure":
        run_measure()
    elif mode == "--report":
        print_report()


if __name__ == "__main__":
    main()
