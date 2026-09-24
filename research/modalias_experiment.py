#!/usr/bin/env python3
"""
M1 / M2 — controlled experiments on what actually populates the Modalias field.

Why these exist. The paper claims Modalias "comes from a prior pairing". That
claim is not supported by anything in the code: the scanner only ever reads
BlueZ's cached Device1 properties and cannot see how that cache was filled. The
sweep is consistent with several different mechanisms and cannot separate them,
because every variable moved at once - different devices, different rooms,
different adapter states, no record of which devices had ever been paired.

These two protocols hold everything constant except one thing at a time.

  M1  One location, one adapter, one device set. For each device, read Modalias
      across four adapter/pairing states. If Modalias only appears in the bonded
      state, the paper's claim is supported. If it appears after a plain
      connect, or straight out of a cold cache, it is not.

  M2  A known-pairable positive control plus a SECOND adapter. M1 alone cannot
      distinguish "this device never exposes Modalias" from "this adapter or
      this BlueZ build never records it" - a null result there is unpublishable
      because it has two explanations. The positive control device is one you
      have deliberately bonded, so Modalias MUST appear; if it does not, the
      instrument is broken and every other null in the study is uninterpretable.

Both take a device list you own or have explicit permission to use. Neither
targets third parties: these are instrument-calibration runs, and running them
against strangers' devices would add ethical cost for no scientific gain (see
research/DATA_RETENTION.md).

    python3 modalias_experiment.py --m1 --devices AA:BB:.. CC:DD:.. --state cold
    python3 modalias_experiment.py --m2 --control AA:BB:.. --adapter hci1

Results append to modalias_experiment.jsonl. Each record carries the state the
operator declared, because the script cannot verify it - see --state.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHONFILES_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "backend", "routes", "pythonfiles"))
sys.path.insert(0, PYTHONFILES_DIR)

from advanced_nmap_scanner import (  # noqa: E402
    query_dbus_properties,
    decode_modalias,
    enrich_modalias_with_chipset,
    lookup_company_id,
)

RESULTS_FILE = os.path.join(SCRIPT_DIR, "modalias_experiment.jsonl")

# The four states M1 walks. The script cannot verify which one it is in - only
# the operator knows whether the cache was really cleared - so the state is
# declared on the command line and recorded verbatim with the reading. A run
# whose declared state is wrong produces a wrong conclusion silently, which is
# why the protocol below asks you to log the exact commands you ran.
M1_STATES = {
    "cold": "BlueZ cache cleared (bluetoothd stopped, /var/lib/bluetooth/<adapter>/ "
            "emptied, bluetoothd restarted), device NEVER paired on this adapter, "
            "no connection made - only a passive scan",
    "scanned": "as cold, then the device was discovered by a passive scan only",
    "connected": "an ACL connection was made (bluetoothctl connect) but the "
                 "device was NOT bonded - no pairing, no link key",
    "bonded": "the device was paired/bonded (bluetoothctl pair) and a link key exists",
}


def adapter_info(adapter):
    """Records which controller produced a reading - M2 turns on this."""
    info = {"adapter": adapter}
    try:
        out = subprocess.run(["hciconfig", adapter, "version"],
                             capture_output=True, text=True, timeout=10).stdout
        info["hciconfig_version"] = out.strip()
    except Exception as e:
        info["hciconfig_version"] = f"unavailable: {e}"
    try:
        out = subprocess.run(["bluetoothctl", "--version"],
                             capture_output=True, text=True, timeout=10).stdout
        info["bluez_version"] = out.strip()
    except Exception as e:
        info["bluez_version"] = f"unavailable: {e}"
    return info


def read_modalias(mac):
    """One reading. Reports the raw field and each resolution stage separately,
    so 'device exposed nothing' is never confused with 'our chipset table has
    no entry for it' - the distinction availability_audit.py also insists on."""
    props = query_dbus_properties(mac) or {}
    raw = props.get("modalias")
    # query_dbus_properties() returns the STRING "N/A" for an absent field, not
    # None, so a bare truthiness test counts "no Modalias" as "Modalias present".
    # availability_audit.py guards this correctly; this tool did not, and scored
    # a watch with no Modalias at all as having one. Normalise to None here so
    # every downstream check sees one representation of "absent".
    if raw in (None, "", "N/A"):
        raw = None
    out = {
        "modalias_present": bool(raw),
        "modalias_raw": raw,
        "modalias_vendor_resolved": None,
        "modalias_chipset_resolved": None,
        "paired_flag": props.get("paired"),
        "connected_flag": props.get("connected"),
    }
    if raw:
        decoded = decode_modalias(raw)
        if decoded:
            decoded["vendor_name"] = lookup_company_id(decoded["vendor_id"])
            decoded = enrich_modalias_with_chipset(decoded)
            out["modalias_vendor_resolved"] = decoded.get("vendor_name")
            out["modalias_chipset_resolved"] = decoded.get("chipset_model")
    return out


def record(entry):
    with open(RESULTS_FILE, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def run_m1(devices, state, adapter, location, note):
    print(f"M1 | state={state} | adapter={adapter} | location={location}")
    print(f"   {M1_STATES[state]}\n")
    for mac in devices:
        reading = read_modalias(mac)
        entry = {
            "experiment": "M1",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "mac": mac,
            "declared_state": state,
            "declared_state_meaning": M1_STATES[state],
            "location": location,
            "note": note,
            **adapter_info(adapter),
            **reading,
        }
        record(entry)
        flag = "MODALIAS" if reading["modalias_present"] else "  ----  "
        print(f"  {flag}  {mac}  paired={reading['paired_flag']} "
              f"connected={reading['connected_flag']}  raw={reading['modalias_raw']}")
    print(f"\nappended to {RESULTS_FILE}")


def run_m2(control, devices, adapter, location, note):
    print(f"M2 | adapter={adapter} | location={location}")
    print(f"   positive control: {control} (must be bonded on this adapter)\n")

    control_reading = read_modalias(control)
    record({
        "experiment": "M2",
        "role": "positive_control",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mac": control,
        "location": location,
        "note": note,
        **adapter_info(adapter),
        **control_reading,
    })

    if not control_reading["modalias_present"]:
        print("  INSTRUMENT FAILURE: the bonded positive control exposed no")
        print("  Modalias on this adapter. Every null reading from this adapter")
        print("  is uninterpretable - it cannot be told apart from this fault.")
        print("  Do not report Modalias availability from this run. Check the")
        print("  bond actually exists (bluetoothctl info <mac> -> Paired: yes)")
        print("  and re-run before touching the test devices.")
        return 1

    print(f"  control OK: {control_reading['modalias_raw']}\n")
    for mac in devices:
        reading = read_modalias(mac)
        record({
            "experiment": "M2",
            "role": "test",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "mac": mac,
            "location": location,
            "note": note,
            **adapter_info(adapter),
            **reading,
        })
        flag = "MODALIAS" if reading["modalias_present"] else "  ----  "
        print(f"  {flag}  {mac}  raw={reading['modalias_raw']}")
    print(f"\nappended to {RESULTS_FILE}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--m1", action="store_true", help="controlled state sweep")
    mode.add_argument("--m2", action="store_true", help="positive control + second adapter")
    ap.add_argument("--devices", nargs="*", default=[],
                    help="MACs of devices you own or have permission to use")
    ap.add_argument("--control", help="M2: MAC of the deliberately bonded control device")
    ap.add_argument("--state", choices=sorted(M1_STATES),
                    help="M1: which state the adapter/device is in. Declared, not verified.")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--location", default="unspecified",
                    help="free-text location label; keep it constant within an M1 series")
    ap.add_argument("--note", default="", help="anything unusual about this run")
    args = ap.parse_args()

    if args.m1:
        if not args.state:
            ap.error("--m1 requires --state (cold/scanned/connected/bonded)")
        if not args.devices:
            ap.error("--m1 requires --devices")
        run_m1(args.devices, args.state, args.adapter, args.location, args.note)
        return 0

    if not args.control:
        ap.error("--m2 requires --control")
    return run_m2(args.control, args.devices, args.adapter, args.location, args.note)


if __name__ == "__main__":
    raise SystemExit(main())
