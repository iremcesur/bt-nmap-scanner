#!/usr/bin/env python3
"""
Pseudonymize MAC addresses in an availability_audit JSONL archive before
release, so the artifact can be published without exposing the raw
third-party MACs the sweep recorded. A Bluetooth MAC can itself be
personal data (see the CNIL guidance cited in the paper), so this is a
release prerequisite, not an option.

Each record's "mac" field is replaced with a stable pseudonym derived
from a SALTED hash: pseudo = "dev-" + first 10 hex chars of
HMAC-SHA256(salt, mac_uppercased). The salt is generated once and written
to a sibling file that is NOT part of the release; without it the mapping
cannot be reversed, and with the same salt the mapping is stable across
files/rounds (so a device seen in two rounds keeps one pseudonym).

As a lighter alternative, --scheme oui-index keeps the OUI (vendor
prefix, first 3 octets) in the clear and replaces the device-specific
half with a per-OUI running index (e.g. "AC:23:3F:dev-1"). This is weaker,
not privacy-preserving: the OUI still reveals the vendor, and in a small
single-location capture a vendor prefix plus a coarse timestamp can be
near-identifying. Use it only for vendor-level analysis where that
residual risk is acceptable; prefer salted-hash for release.

Beyond the MAC, other fields can re-identify a device: by default this
tool also coarsens timestamps to date only (--keep-time to disable) and
drops or booleanizes free-text fields such as modalias_raw,
sdp_records_raw, and sdp_service_name (--keep-freetext to disable).
Even so, review a small archive by hand before release---no automated
pass guarantees non-identifiability at n of a few dozen.

Usage:
  python3 pseudonymize_macs.py IN.jsonl OUT.jsonl                # salted-hash (default)
  python3 pseudonymize_macs.py IN.jsonl OUT.jsonl --scheme oui-index
  python3 pseudonymize_macs.py IN.jsonl OUT.jsonl --salt-file mysalt.bin

The output is written with the same one-record-per-line JSON shape as the
input; every non-mac field is passed through unchanged.
"""

import sys
import os
import json
import hmac
import hashlib
import secrets
import argparse


def load_or_make_salt(path):
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()
    salt = secrets.token_bytes(32)
    with open(path, "wb") as f:
        f.write(salt)
    # Owner-read/write only; this file must NOT be part of the release.
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print(f"[salt] new salt written to {path} (keep private; do NOT release)")
    return salt


def hash_pseudonym(mac, salt):
    norm = mac.strip().upper()
    digest = hmac.new(salt, norm.encode(), hashlib.sha256).hexdigest()
    return "dev-" + digest[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--scheme", choices=("salted-hash", "oui-index"),
                    default="salted-hash")
    ap.add_argument("--salt-file", default=None,
                    help="salt file for salted-hash. Default: "
                         "pseudonymize_salt.DO_NOT_RELEASE.bin in the CWD, "
                         "deliberately NOT next to OUT so it is not packaged by accident.")
    ap.add_argument("--keep-time", action="store_true",
                    help="keep full timestamps. Default: coarsen to date only, "
                         "since second-resolution times plus location aid re-identification.")
    ap.add_argument("--keep-freetext", action="store_true",
                    help="keep raw free-text fields (modalias_raw, sdp_records_raw, "
                         "sdp_service_name). Default: drop/booleanize them; a raw "
                         "Modalias or SDP name can itself identify a device.")
    args = ap.parse_args()

    if args.infile == args.outfile:
        sys.exit("Refusing to overwrite the input in place; choose a different OUT.jsonl.")

    # Free-text fields that can re-identify a device even after the MAC is hashed.
    FREETEXT_DROP = ("modalias_raw", "sdp_records_raw")
    FREETEXT_BOOLIZE = ("sdp_service_name",)

    salt = None
    if args.scheme == "salted-hash":
        salt_path = args.salt_file or "pseudonymize_salt.DO_NOT_RELEASE.bin"
        salt = load_or_make_salt(salt_path)

    oui_index = {}   # oui -> {mac -> index}
    n = 0
    with open(args.infile) as fin, open(args.outfile, "w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("mac_pseudonymized"):
                # idempotent: already processed, pass through unchanged
                fout.write(json.dumps(rec) + "\n")
                n += 1
                continue
            mac = rec.get("mac")
            if mac and mac != "Unknown":
                if args.scheme == "salted-hash":
                    rec["mac"] = hash_pseudonym(mac, salt)
                else:  # oui-index
                    norm = mac.strip().upper()
                    oui = norm[:8] if len(norm) >= 8 else norm
                    bucket = oui_index.setdefault(oui, {})
                    if norm not in bucket:
                        bucket[norm] = len(bucket) + 1
                    rec["mac"] = f"{oui}:dev-{bucket[norm]}"
            if not args.keep_time and isinstance(rec.get("timestamp"), str):
                # coarsen "2026-08-17 15:23:20" / ISO to date only
                rec["timestamp"] = rec["timestamp"].replace("T", " ").split(" ")[0]
            if not args.keep_freetext:
                for k in FREETEXT_DROP:
                    rec.pop(k, None)
                for k in FREETEXT_BOOLIZE:
                    if k in rec:
                        rec[k] = bool(rec[k])
            rec["mac_pseudonymized"] = True
            fout.write(json.dumps(rec) + "\n")
            n += 1

    print(f"[done] wrote {n} record(s) to {args.outfile} (scheme={args.scheme})")
    if args.scheme == "salted-hash":
        print("[note] release OUT.jsonl only; never release the .salt file.")


if __name__ == "__main__":
    main()
