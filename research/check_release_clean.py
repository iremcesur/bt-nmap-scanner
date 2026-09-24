#!/usr/bin/env python3
"""
Release gate (B3): fails if anything in research/release/ still carries a raw
MAC, an advertised device name, or the salt itself.

Run this before packaging an artifact. It is deliberately a separate check from
the pseudonymizers: a tool that both transforms and certifies its own output
proves nothing. This one re-reads the files on disk and looks for identifiers
without knowing how they were supposed to have been removed.

    python3 check_release_clean.py          # exit 0 = safe to release

Checks:
  1. no MAC-shaped string anywhere in research/release/
  2. no device name that appears in the raw archives survives in the release
  3. no salt / key material inside research/release/
  4. every raw archive in the repo has a corresponding release file
"""

import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RELEASE_DIR = os.path.join(SCRIPT_DIR, "release")

MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")

# raw archive -> the release file that is supposed to cover it. Written out
# explicitly rather than matched by filename prefix: two pilot archives are
# deliberately renamed on release, and a prefix heuristic reports those as
# uncovered while quietly accepting a genuinely missing file elsewhere.
RELEASE_COVERAGE = {
    os.path.join(REPO_ROOT, "historical_scans.jsonl"):
        "historical_scans.pseudonymized.jsonl",
    os.path.join(REPO_ROOT, "research_evaluation.csv"):
        "research_evaluation.pseudonymized.csv",
    os.path.join(SCRIPT_DIR, "candidates.json"):
        "candidates.pseudonymized.json",
    os.path.join(SCRIPT_DIR, "candidates_own_devices.json"):
        "candidates_own_devices.pseudonymized.json",
    os.path.join(SCRIPT_DIR, "availability_raw.jsonl"):
        "availability_raw.pseudonymized.jsonl",
    os.path.join(SCRIPT_DIR, "availability_raw_pilot_cleaned.jsonl"):
        "availability_pilot.pseudonymized.jsonl",
    os.path.join(SCRIPT_DIR, "availability_raw_pilot_own_devices.jsonl"):
        "availability_pilot_own_devices.pseudonymized.jsonl",
    # The scanner writes historical_scans.jsonl / research_evaluation.csv to
    # RELATIVE paths, so an archive lands wherever it happened to be run from.
    # Three separate copies existed before this was noticed, and only the
    # repo-root pair was ever pseudonymized or checked. Every known location is
    # listed here; see find_stray_archives() for the check that catches new ones.
    os.path.join(REPO_ROOT, "backend", "historical_scans.jsonl"):
        "backend_historical_scans.pseudonymized.jsonl",
    os.path.join(REPO_ROOT, "backend", "research_evaluation.csv"):
        "backend_research_evaluation.pseudonymized.csv",
    os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles", "historical_scans.jsonl"):
        "pythonfiles_historical_scans.pseudonymized.jsonl",
    os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles", "research_evaluation.csv"):
        "pythonfiles_research_evaluation.pseudonymized.csv",
    # The cross-encounter observation store. Unlike every archive above it is
    # already pseudonymous at write time - salted HMAC device keys, no MAC, no
    # advertised name - so it needs no pseudonymizer pass. It is listed anyway
    # because it is still a per-device record built from third-party scans, and
    # an archive left out of this table is outside the gate by omission.
    os.path.join(REPO_ROOT, "backend", "routes", "pythonfiles", "observation_store.jsonl"):
        "observation_store.jsonl",
}


def find_stray_archives():
    """
    Walks the repo for any historical_scans.jsonl / research_evaluation.csv that
    RELEASE_COVERAGE does not know about. Listing known paths is not enough when
    the writer uses relative paths: the next run from a new directory creates a
    new archive that no pseudonymizer and no gate would ever see.
    """
    wanted = {"historical_scans.jsonl", "research_evaluation.csv",
              "observation_store.jsonl"}
    known = {os.path.normpath(p) for p in RELEASE_COVERAGE}
    strays = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs
                   if d not in {".git", "node_modules", "__pycache__", "release"}]
        for name in files:
            if name in wanted:
                full = os.path.normpath(os.path.join(root, name))
                if full not in known:
                    strays.append(os.path.relpath(full, REPO_ROOT))
    return strays
RAW_ARCHIVES = list(RELEASE_COVERAGE)


def raw_device_names():
    """Every advertised name present in the raw archives, as literal strings."""
    names = set()
    name_re = re.compile(r'"(?:name|Device Name|device_name|alias)"\s*:\s*"((?:[^"\\]|\\.)*)"')
    for path in RAW_ARCHIVES:
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in name_re.finditer(text):
            value = m.group(1).strip()
            # A name that is just the device's own MAC in dashed form carries no
            # information beyond the MAC, which check 1 already covers.
            if value and value not in ("Unknown", "N/A") and not MAC_RE.fullmatch(value.replace("-", ":")):
                names.add(value)
    # The CSV column, which has no JSON key to anchor on.
    csv_path = os.path.join(REPO_ROOT, "research_evaluation.csv")
    if os.path.exists(csv_path):
        import csv
        with open(csv_path, encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                value = (row.get("Device Name") or "").strip()
                if value and value not in ("Unknown", "N/A") and not MAC_RE.fullmatch(value.replace("-", ":")):
                    names.add(value)
    return names


def main():
    failures = []

    if not os.path.isdir(RELEASE_DIR):
        print(f"no release directory at {RELEASE_DIR}")
        return 1

    release_files = sorted(
        os.path.join(RELEASE_DIR, f) for f in os.listdir(RELEASE_DIR)
        if os.path.isfile(os.path.join(RELEASE_DIR, f))
    )
    if not release_files:
        print("release directory is empty")
        return 1

    names = raw_device_names()
    print(f"checking {len(release_files)} release file(s) "
          f"against {len(names)} device name(s) from the raw archives\n")

    for path in release_files:
        rel = os.path.relpath(path, REPO_ROOT)
        problems = []

        if "salt" in os.path.basename(path).lower():
            problems.append("salt/key material must not live in the release directory")

        try:
            text = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            problems.append("binary file in the release directory - inspect by hand")
            text = ""

        macs = set(MAC_RE.findall(text))
        if macs:
            problems.append(f"{len(macs)} raw MAC(s), e.g. {sorted(macs)[0]}")

        leaked = sorted(n for n in names if n in text)
        if leaked:
            problems.append(f"{len(leaked)} device name(s) survived, e.g. {leaked[0]!r}")

        if problems:
            failures.append((rel, problems))
            print(f"FAIL {rel}")
            for p in problems:
                print(f"       {p}")
        else:
            print(f"ok   {rel}")

    present = {os.path.basename(r) for r in release_files}
    missing = [f"{os.path.relpath(raw, REPO_ROOT)} -> {expected}"
               for raw, expected in RELEASE_COVERAGE.items()
               if os.path.exists(raw) and expected not in present]
    if missing:
        print("\nraw archives with no corresponding release file:")
        for m in missing:
            print(f"  {m}")
        failures.append(("coverage", missing))

    strays = find_stray_archives()
    if strays:
        print("\nscan archives in locations nothing knows about:")
        for st in strays:
            print(f"  {st}")
        print("  (the scanner writes to relative paths - these were created by")
        print("   running it from a different working directory)")
        failures.append(("stray archives", strays))

    print()
    if failures:
        print(f"NOT SAFE TO RELEASE - {len(failures)} problem file(s)")
        return 1
    print("release directory is clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
