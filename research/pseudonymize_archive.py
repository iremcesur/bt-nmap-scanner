#!/usr/bin/env python3
"""
Whole-archive pseudonymizer (B3).

pseudonymize_macs.py is schema-aware: it walks JSONL records and rewrites the
"mac" field. That covers the availability sweep, but the project holds third-
party MACs in three other shapes it cannot touch:

  * research/candidates.json          - a JSON object KEYED by MAC
  * historical_scans.jsonl            - MACs nested inside features/packet_metrics
  * research_evaluation.csv           - a CSV column

and those archives additionally carry advertised device names, which are
frequently personal ("Irem's AirPods", "<firstname>'s iPhone") or
model-identifying ("OPPO A5 2020"). A device name is as re-identifying as the
MAC and must be handled in the same pass.

This tool is shape-agnostic by design: it rewrites every MAC-shaped substring
anywhere in a file, using the SAME salted-hash pseudonym function as
pseudonymize_macs.py, so a device keeps one pseudonym across every archive as
long as one salt is used. Names are handled separately (see --names).

    # one salt for everything, so pseudonyms line up across archives
    python3 pseudonymize_archive.py --salt-file SALT.bin \
        historical_scans.jsonl        release/historical_scans.pseudonymized.jsonl

    python3 pseudonymize_archive.py --salt-file SALT.bin \
        research/candidates.json      research/release/candidates.pseudonymized.json

Because it works on raw text it makes no assumption about the schema, but for
the same reason it cannot know which free-text field is safe. Review the output
by hand before release; at n of a few dozen no automated pass can guarantee
non-identifiability.

The salt file must never be released. With it, the mapping is reversible; the
salt is the only thing standing between the release and the raw MACs.
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from pseudonymize_macs import hash_pseudonym, load_or_make_salt  # noqa: E402

MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")

# Device names are free text chosen by the device owner. Rather than guess at a
# safe-list, the default is to replace the whole value of any field that looks
# like a device name with a stable pseudonym derived from the name itself, so
# repeat appearances stay linkable without the text surviving.
NAME_FIELD_RE = re.compile(
    r'("(?:name|Device Name|device_name|alias)"\s*:\s*)"((?:[^"\\]|\\.)*)"'
)


def pseudonymize_text(text, salt, do_names=True):
    macs = {}

    def _mac(m):
        raw = m.group(0)
        key = raw.upper().replace("-", ":")
        if key not in macs:
            macs[key] = hash_pseudonym(key, salt)
        return macs[key]

    out = MAC_RE.sub(_mac, text)

    names = {}
    if do_names:
        def _name(m):
            prefix, value = m.group(1), m.group(2)
            if not value or value in ("Unknown", "N/A"):
                return m.group(0)
            # A name that is just the MAC in dashed form was already rewritten
            # above; leave those alone rather than double-pseudonymizing.
            if value.startswith("dev-"):
                return m.group(0)
            if value not in names:
                names[value] = "name-" + hash_pseudonym(value, salt)[4:]
            return f'{prefix}"{names[value]}"'

        out = NAME_FIELD_RE.sub(_name, out)

        # Second pass: replace the collected names wherever else they appear.
        #
        # Anchoring on the "name": field alone is not enough, and the release
        # gate caught this: the evidence chain embeds the advertised name inside
        # a free-text audit string, e.g.
        #     "observed_value": "CoD major=0x02, name='<advertised name>'"
        # which no field-anchored pattern sees. Any derived or human-readable
        # field can carry a name this way, so once a name is known it is
        # substituted everywhere in the document. Longest first, so a name that
        # contains a shorter one is not left half-rewritten.
        for value in sorted(names, key=len, reverse=True):
            out = out.replace(value, names[value])

    return out, len(macs), len(names)


def pseudonymize_csv_names(text, salt, column="Device Name"):
    """CSV has no JSON key to anchor on, so the name column is located by header."""
    import csv
    import io

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or column not in reader.fieldnames:
        return text, 0
    rows = list(reader)
    names = {}
    for row in rows:
        value = (row.get(column) or "").strip()
        if not value or value in ("Unknown", "N/A") or value.startswith("dev-"):
            continue
        if value not in names:
            names[value] = "name-" + hash_pseudonym(value, salt)[4:]
        row[column] = names[value]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue(), len(names)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--salt-file", required=True,
                    help="shared salt. Use ONE salt across every archive so a "
                         "device keeps one pseudonym everywhere. Never release it.")
    ap.add_argument("--keep-names", action="store_true",
                    help="leave advertised device names in the clear. Off by "
                         "default: names are routinely personal.")
    args = ap.parse_args()

    if os.path.abspath(args.infile) == os.path.abspath(args.outfile):
        sys.exit("Refusing to overwrite the input in place; choose a different OUT.")

    salt = load_or_make_salt(args.salt_file)
    text = open(args.infile, encoding="utf-8").read()

    if args.infile.lower().endswith(".csv"):
        out, n_macs, _ = pseudonymize_text(text, salt, do_names=False)
        n_names = 0
        if not args.keep_names:
            out, n_names = pseudonymize_csv_names(out, salt)
    else:
        out, n_macs, n_names = pseudonymize_text(text, salt,
                                                 do_names=not args.keep_names)

    os.makedirs(os.path.dirname(os.path.abspath(args.outfile)), exist_ok=True)
    with open(args.outfile, "w", encoding="utf-8") as fh:
        fh.write(out)
    try:
        os.chmod(args.outfile, 0o600)
    except OSError:
        pass

    print(f"[done] {args.infile} -> {args.outfile}")
    print(f"       {n_macs} distinct MAC(s) pseudonymized, {n_names} name(s)")
    leftover = MAC_RE.findall(out)
    if leftover:
        print(f"[WARN] {len(leftover)} MAC-shaped string(s) survived - inspect before release")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
