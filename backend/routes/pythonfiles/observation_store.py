"""
Per-device observation store for cross-encounter comparison.

WHAT THIS IS FOR. When a device is scanned again, its earlier scans can be
compared against the current one. The comparison is deliberately narrow:

  * It stores OBSERVATIONS, never predictions. Comparing a new prediction
    against archived predictions produced by the same scorer measures only
    that the scorer is consistent with itself - a systematically biased
    scorer agrees with itself perfectly - so it cannot corroborate anything.
    Raw readings carry no such circularity: two scans reporting different
    Class-of-Device bytes for one MAC disagree about an observation, and at
    most one of them can be right, whatever the device actually is.

  * The result is ASYMMETRIC. A disagreement is evidence (something is
    wrong); an agreement is not (a signal that reads the same way twice may
    be stably right or stably wrong). So a match is recorded at weight zero
    as "unused", exactly as an undatable chipset already is in
    build_evidence_chain, and only a mismatch is recorded as "conflicts".

  * It never feeds the score. Like every other post-hoc check it can lower
    the reported confidence and add an audit entry, and that is all. A
    prediction must not become more confident because the same device was
    scanned before.

FIELD CHOICE. Only fields expected to be INVARIANT for one physical device
are compared: a device's Modalias, Class-of-Device and OUI-resolved vendor
do not legitimately change between two scans minutes apart. Signals that may
legitimately vary (RSSI, RTT, battery, connection parameters, which services
happened to answer) are stored for availability analysis but never compared
for equality - varying is what they do.

PRIVACY. A MAC address is itself personal data (see research/DATA_RETENTION.md),
and this store would otherwise become another archive of raw MACs. Records are
therefore keyed by a salted HMAC pseudonym, using the same construction as
research/pseudonymize_macs.py, so the store is stable per device but does not
contain the addresses. The salt file must never be released. No advertised
device name is stored: names in this project are frequently personal.
"""

import hashlib
import hmac
import json
import os
import secrets
import time

STORE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(STORE_DIR, "observation_store.jsonl")
SALT_PATH = os.path.join(STORE_DIR, "observation_store_salt.DO_NOT_RELEASE.bin")

# Fields compared for equality across encounters. Each must be a property of
# the physical device, not of the scan: if one of these differs between two
# scans of the same MAC, one of the two reads is wrong (or the address is
# shared/randomized, which is itself worth surfacing).
INVARIANT_FIELDS = ("modalias", "cod_hex", "vendor")

# Stored for signal-availability analysis but never equality-compared: these
# legitimately vary between scans and a difference means nothing.
VARIABLE_FIELDS = ("lmp_integer", "sdp_profiles", "gatt_uuid_count",
                   "appearance_category", "name_resolved")


def _load_or_make_salt(path=SALT_PATH):
    if os.path.exists(path):
        with open(path, "rb") as fh:
            salt = fh.read()
        if salt:
            return salt
    salt = secrets.token_bytes(32)
    with open(path, "wb") as fh:
        fh.write(salt)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return salt


def device_key(mac_address, salt=None):
    """Stable, non-reversible per-device key. Same MAC -> same key."""
    salt = salt if salt is not None else _load_or_make_salt()
    norm = (mac_address or "").strip().upper()
    digest = hmac.new(salt, norm.encode(), hashlib.sha256).hexdigest()
    return "dev-" + digest[:10]


def build_observation(mac_address, cod_hex, vendor, chipset_info, hw_info,
                      c_data, sdp_flags, gatt_uuids, gatt_appearance, name):
    """
    The observation record for one scan. Deliberately contains no prediction,
    no confidence, and no advertised name - only whether a name resolved.
    """
    modalias = None
    if chipset_info:
        vendor_id = chipset_info.get("vendor_id")
        product_id = chipset_info.get("product_id")
        version = chipset_info.get("version")
        source = chipset_info.get("source")
        if vendor_id and product_id:
            modalias = f"{source}:v{vendor_id}p{product_id}d{version}"

    lmp_int = 0
    if c_data and c_data.get("success"):
        lmp_int = c_data.get("lmp_integer", 0)
    elif hw_info:
        lmp_int = hw_info.get("lmp_integer", 0)

    profiles = sorted(k for k, v in (sdp_flags or {}).items()
                      if v and k != "failed")

    return {
        "device_key": device_key(mac_address),
        "observed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modalias": modalias,
        "cod_hex": (cod_hex or "N/A").upper(),
        "vendor": (vendor or "Unknown").strip(),
        "lmp_integer": lmp_int,
        "sdp_profiles": profiles,
        "gatt_uuid_count": len(gatt_uuids or []),
        "appearance_category": (gatt_appearance or {}).get("gatt_appearance_category"),
        "name_resolved": bool(name and name.strip()
                              and name.strip().lower() != "unknown"),
    }


def load_prior_observations(device_key_value, path=STORE_PATH):
    """Every stored observation for this device, oldest first. Never raises."""
    if not os.path.exists(path):
        return []
    prior = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("device_key") == device_key_value:
                    prior.append(record)
    except OSError:
        return []
    return prior


def record_observation(observation, path=STORE_PATH):
    """Append one observation. Never raises - a failed write must not fail a scan."""
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(observation, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def compare_with_prior(observation, prior_observations):
    """
    Compare one observation against this device's earlier ones.

    Returns (mismatches, comparable_count). A mismatch is a field that should
    be invariant for a physical device but was read differently before; it is
    reported with both values so an auditor can see which scan to distrust.
    Fields absent from either side are skipped rather than counted as
    agreement: "not observed" is not "observed to be the same".

    Agreement is returned only as comparable_count, never as a score. The
    caller must not treat a high comparable_count as corroboration.
    """
    mismatches = []
    comparable = 0
    for prior in prior_observations:
        for field in INVARIANT_FIELDS:
            now = observation.get(field)
            before = prior.get(field)
            if now in (None, "", "N/A") or before in (None, "", "N/A"):
                continue
            comparable += 1
            if now != before:
                mismatches.append({
                    "field": field,
                    "current": now,
                    "previous": before,
                    "previously_observed_at": prior.get("observed_at"),
                })
    return mismatches, comparable


def prior_encounter_entry(observation, prior_observations):
    """
    The evidence_chain record for a re-encounter, or None when this device has
    not been seen before (nothing to compare, so no entry - an absent check is
    not a passed check).

    A mismatch is "conflicts". A match is "unused" at weight 0: agreement
    between two runs of the same reader is not independent corroboration, and
    recording it as support would inflate the agreement count with evidence
    that was never at risk of failing.
    """
    if not prior_observations:
        return None

    mismatches, comparable = compare_with_prior(observation, prior_observations)
    n = len(prior_observations)

    if mismatches:
        detail = "; ".join(
            f"{m['field']}: now {m['current']!r}, was {m['previous']!r} "
            f"on {m['previously_observed_at']}" for m in mismatches[:3]
        )
        return {
            "signal_name": "prior_encounter",
            "observed_value": f"{n} earlier observation(s) of this device",
            "inference": f"Invariant field(s) disagree with an earlier scan - {detail}",
            "contribution": ("A property that cannot legitimately change between "
                            "scans was read differently, so at least one of the two "
                            "reads is wrong - or this address is shared/randomized"),
            "weight": 0.15,
            "direction": "conflicts",
        }

    if comparable == 0:
        return {
            "signal_name": "prior_encounter",
            "observed_value": f"{n} earlier observation(s) of this device",
            "inference": "Device seen before, but no invariant field resolved on both scans",
            "contribution": ("Nothing could be compared - this entry is not evidence "
                            "for or against the prediction"),
            "weight": 0.0,
            "direction": "unused",
        }

    return {
        "signal_name": "prior_encounter",
        "observed_value": f"{n} earlier observation(s) of this device",
        "inference": f"{comparable} invariant field comparison(s) agree with earlier scans",
        "contribution": ("Agreement between two runs of the same reader is not "
                        "independent corroboration and does not raise confidence - "
                        "recorded for audit only"),
        "weight": 0.0,
        "direction": "unused",
    }
