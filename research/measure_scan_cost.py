#!/usr/bin/env python3
"""
Count the radio-facing operations one scan issues.

WHY THIS EXISTS. The comparison table (paper Table III) carries an interaction
cost for every other method and, until this script, only prose for ours: the
flooding strategy we compare against states ~3000 packets and a measured
connection-reset rate, while our own cell said "not measured". That is the one
axis where a rival has a number and we do not, and it needs no ground truth to
fix - the scanner's own behaviour is fully observable to us.

WHAT IS AND IS NOT MEASURED. This counts *operations issued*: each external
probe the scanner invokes on the target, grouped by transport. It does not
count packets. An `sdptool browse` is one operation here but several packets on
air, so these numbers are NOT comparable to a packet count, and the paper must
not present them as one. What they do support is the claim the table actually
makes: that the scan is a bounded number of ordinary queries rather than a
flood, and that the count does not grow with the target's responsiveness.

HOW. The scanner is imported and run against a synthetic address with
`subprocess.run` and the D-Bus bindings replaced by recorders. Every invocation
is logged and a canned reply is returned so the pipeline proceeds down its
normal path instead of aborting at the first failure. Two profiles are run:

  reachable    every probe answers, so the scan follows its longest path
  unreachable  every probe fails, so the scan follows its shortest path

Reporting both is the honest form, and the result is the opposite of what we
assumed when writing this: the UNREACHABLE profile is the expensive one. A
target that answers nothing costs more than one that answers everything,
because the scanner retries connection setup on failure. The population where
this matters is precisely the one a cold public sweep meets, so the upper bound
is the figure a reviewer should hold us to, and it is not the friendly case.

Usage:  python3 research/measure_scan_cost.py [--json]
"""

import argparse
import collections
import json
import os
import sys
import types

SCANNER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "routes", "pythonfiles",
)

# Which transport each external command touches. Used only to group the counts;
# an unlisted command is reported under "other" rather than silently dropped.
TRANSPORT = {
    "hcitool": "BR/EDR (HCI)",
    "l2ping": "BR/EDR (L2CAP)",
    "sdptool": "BR/EDR (SDP)",
    "gatttool": "LE (GATT)",
    "bluetoothctl": "local (BlueZ control)",
    "version_finder": "BR/EDR (HCI, C helper)",
    # dbus-send reads BlueZ's cached Device1 properties over local IPC. It is
    # not radio-facing: the daemon answers from its own state, which is exactly
    # why Modalias is described as a cache read in the paper.
    "dbus-send": "local (D-Bus IPC)",
}

# Transports that put something on air. Everything else is host-local and is
# counted separately, so the headline figure is not inflated by IPC.
RADIO_TRANSPORTS = {"BR/EDR (HCI)", "BR/EDR (L2CAP)", "BR/EDR (SDP)",
                    "LE (GATT)", "BR/EDR (HCI, C helper)"}

# Canned stdout per command, used in the "reachable" profile so parsers accept
# the reply and the scan continues. These are shaped like real output, not real
# captures - their only job is to keep the control flow on its longest path.
CANNED = {
    "hcitool": (
        "Requesting information ...\n"
        "\tBD Address:  AA:BB:CC:DD:EE:FF\n"
        "\tDevice Name: TestDevice\n"
        "\tLMP Version: 5.3 (0xc) Subversion: 0x1234\n"
        "\tManufacturer: Test (1)\n"
        "\tFeatures page 0: 0xbf 0xfe 0xcf 0xfe 0xdb 0xff 0x7b 0x87\n"
    ),
    "l2ping": (
        "Ping: AA:BB:CC:DD:EE:FF from AA:BB:CC:DD:EE:FF (data size 44) ...\n"
        "44 bytes from AA:BB:CC:DD:EE:FF id 0 time 12.34ms\n"
        "1 sent, 1 received, 0% loss\n"
        "rtt min/avg/max/mdev = 12.340/12.340/12.340/0.000 ms\n"
    ),
    "sdptool": (
        "Browsing AA:BB:CC:DD:EE:FF ...\n"
        "Service Name: Headset\n"
        "Service RecHandle: 0x10000\n"
        'Service Class ID List:\n  "Headset" (0x1108)\n'
    ),
    "gatttool": "handle: 0x0002, char properties: 0x02, uuid: 00002a00-0000-1000-8000-00805f9b34fb\n",
    "bluetoothctl": "Device AA:BB:CC:DD:EE:FF TestDevice\n",
    "version_finder": (
        "LMP Version: 12\n"
        "Device ID Profile: Present\n"
        "A2DP: Y\nMAP: N\nPBAP: Y\nHFP: Y\nOPP: N\n"
        "Estimated Android Version: Android 13 (Tiramisu)\n"
    ),
}


class Recorder:
    """Records every external invocation the scan makes."""

    def __init__(self, reachable):
        self.reachable = reachable
        self.calls = []
        self.dbus_calls = []

    def command_key(self, argv):
        if not argv:
            return "other"
        name = os.path.basename(str(argv[0]))
        return name if name in TRANSPORT else (
            "version_finder" if "version_finder" in name else "other")

    def fake_run(self, argv, *args, **kwargs):
        key = self.command_key(argv if isinstance(argv, (list, tuple)) else [argv])
        self.calls.append((key, list(argv) if isinstance(argv, (list, tuple)) else [argv]))
        out = CANNED.get(key, "") if self.reachable else ""
        result = types.SimpleNamespace()
        result.stdout = out
        result.stderr = ""
        result.returncode = 0 if self.reachable else 1
        return result

    def record_dbus(self, what):
        self.dbus_calls.append(what)


def install_fakes(scanner, recorder):
    """Replace every outward-facing call with a recorder."""
    scanner.subprocess.run = recorder.fake_run

    # D-Bus: the scanner reads BlueZ properties and the GATT database. Both are
    # local IPC to the host daemon, but the GATT database is only populated by
    # an LE connection, so GATT reads are counted as radio-facing and the
    # property reads as local (this is the split the paper's transport table
    # already makes).
    class FakeIface:
        def __init__(self, outer, path, iface):
            self.outer, self.path, self.iface = outer, path, iface

        def GetManagedObjects(self):
            recorder.record_dbus("dbus:GetManagedObjects")
            if not recorder.reachable:
                return {}
            # A device with GATT services resolved, so the characteristic walk
            # succeeds and the Appearance / connection-parameter reads are
            # actually issued. With an empty tree they are skipped and the
            # measurement silently omits the whole LE branch.
            dev = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"
            return {
                f"{dev}/service0001/char0002": {
                    "org.bluez.GattCharacteristic1":
                        {"UUID": "00002a01-0000-1000-8000-00805f9b34fb"}},
                f"{dev}/service0001/char0004": {
                    "org.bluez.GattCharacteristic1":
                        {"UUID": "00002a04-0000-1000-8000-00805f9b34fb"}},
            }

        def GetAll(self, _name):
            recorder.record_dbus("dbus:Device1.GetAll")
            if not recorder.reachable:
                raise RuntimeError("device not available")
            return {"Address": "AA:BB:CC:DD:EE:FF", "Name": "TestDevice",
                    "Class": 0x240404, "Modalias": "bluetooth:v004Cp7410d1A50",
                    "UUIDs": [], "RSSI": -55}

        def ReadValue(self, _opts):
            recorder.record_dbus("dbus:GattCharacteristic1.ReadValue")
            if not recorder.reachable:
                raise RuntimeError("characteristic not found")
            return [0x00, 0x01]

    class FakeBus:
        def get_object(self, _svc, path):
            return path

    fake_dbus = types.SimpleNamespace(
        SystemBus=lambda: FakeBus(),
        Interface=lambda obj, iface: FakeIface(None, obj, iface),
        DBusException=Exception,
    )
    scanner.dbus = fake_dbus

    # Keep the run off the network and off the real archives.
    #
    # The archive guard below is not belt-and-braces, it is load-bearing. An
    # earlier version of this script stubbed only the observation store and the
    # CSV helper, and eight synthetic scans of AA:BB:CC:DD:EE:FF were appended
    # to the real historical_scans.jsonl before anyone noticed - main() opens
    # that file by a bare relative path (`open("historical_scans.jsonl", "a")`),
    # which no amount of stubbing higher up prevents. Measuring the scanner must
    # never mutate the corpus the scanner produced, so `open` is intercepted and
    # any append to a research archive is redirected to os.devnull.
    scanner.urllib.request.urlopen = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("network disabled during measurement"))
    scanner.observation_store.record_observation = lambda *a, **k: True
    scanner.observation_store.load_prior_observations = lambda *a, **k: []
    scanner.ensure_csv_columns = lambda *a, **k: None
    scanner.log = lambda *a, **k: None

    import builtins
    real_open = builtins.open
    guarded = ("historical_scans.jsonl", "research_evaluation.csv",
               "observation_store.jsonl")

    def guarded_open(file, mode="r", *args, **kwargs):
        name = os.path.basename(str(file))
        if name in guarded and any(m in str(mode) for m in ("a", "w", "+")):
            return real_open(os.devnull, mode, *args, **kwargs)
        return real_open(file, mode, *args, **kwargs)

    scanner.open = guarded_open
    builtins.open = guarded_open
    return real_open


def measure(reachable):
    sys.path.insert(0, SCANNER_DIR)
    for stale in ("advanced_nmap_scanner",):
        sys.modules.pop(stale, None)
    import advanced_nmap_scanner as scanner

    recorder = Recorder(reachable)
    real_open = install_fakes(scanner, recorder)

    original_argv = sys.argv
    original_stdout = sys.stdout
    sys.argv = ["advanced_nmap_scanner.py", "AA:BB:CC:DD:EE:FF", "false"]
    try:
        sys.stdout = open(os.devnull, "w")
        try:
            scanner.main()
        except SystemExit:
            pass
        except Exception as exc:  # a canned reply the parser rejected
            sys.stdout = original_stdout
            print(f"  note: scan aborted at {type(exc).__name__}: {exc}",
                  file=sys.stderr)
    finally:
        import builtins
        builtins.open = real_open
        if sys.stdout is not original_stdout:
            sys.stdout.close()
        sys.stdout = original_stdout
        sys.argv = original_argv

    return recorder


def summarize(recorder):
    by_command = collections.Counter(key for key, _argv in recorder.calls)
    by_transport = collections.Counter()
    for key, _argv in recorder.calls:
        by_transport[TRANSPORT.get(key, "other")] += 1
    gatt_reads = sum(1 for d in recorder.dbus_calls if "Gatt" in d)
    local_reads = len(recorder.dbus_calls) - gatt_reads
    radio_commands = sum(n for transport, n in by_transport.items()
                         if transport in RADIO_TRANSPORTS)
    return {
        "external_commands": len(recorder.calls),
        "by_command": dict(by_command),
        "by_transport": dict(by_transport),
        "dbus_gatt_reads": gatt_reads,
        "dbus_local_reads": local_reads,
        "local_commands": len(recorder.calls) - radio_commands,
        "radio_facing_total": radio_commands + gatt_reads,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = {}
    for label, reachable in (("reachable", True), ("unreachable", False)):
        results[label] = summarize(measure(reachable))

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print("Radio-facing operations issued by one scan.")
    print("Counts are OPERATIONS, not packets - not comparable to a packet count.")
    print()
    for label in ("reachable", "unreachable"):
        r = results[label]
        print(f"[{label}] target answers every probe" if label == "reachable"
              else f"[{label}] target answers nothing")
        print(f"  external commands:        {r['external_commands']}")
        for cmd, n in sorted(r["by_command"].items(), key=lambda kv: -kv[1]):
            print(f"      {cmd:<16} {n}")
        print(f"  D-Bus GATT reads (LE):    {r['dbus_gatt_reads']}")
        print(f"  D-Bus local prop reads:   {r['dbus_local_reads']}")
        print(f"  radio-facing total:       {r['radio_facing_total']}")
        print()
    reach = results["reachable"]["radio_facing_total"]
    unreach = results["unreachable"]["radio_facing_total"]
    lo, hi = min(reach, unreach), max(reach, unreach)
    print(f"Bounded range: {lo}-{hi} radio-facing operations per scan.")
    print("The count is bounded by the scanner's own control flow - no loop")
    print("repeats while a probe keeps succeeding - so there is a hard ceiling")
    print("regardless of how the target behaves.")
    if unreach > reach:
        print()
        print(f"Note: the UNREACHABLE case is the expensive one "
              f"({unreach} vs {reach}).")
        print("Failed probes trigger connection-setup retries, so a device that")
        print("ignores us costs more than one that answers. A cold sweep of")
        print("unfamiliar devices is therefore the upper-bound case, not the")
        print("lower-bound one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
