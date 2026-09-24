"""
Unit tests for build_evidence_chain (paper Section III-C).

B2 exists because the mechanism produced zero entries across 43 real scans and
the paper explained that away as "conflicts are rare". That explanation cannot
be right: the chain is specified to record *supporting* evidence too, so an
all-empty archive points at the code, not at the world. These five cases are
the ones the advisor asked for:

  1. a supporting pair          - CoD and Appearance agree     -> "supports"
  2. a conflicting pair         - CoD and Appearance disagree  -> "conflicts"
  3. a single signal            - one side missing             -> no pair entry
  4. a dependent pair to skip   - Appearance stood in for an absent CoD, so
                                  checking it against device_type is circular
                                  and must NOT be recorded as corroboration
  5. empty input                - nothing observed             -> empty chain
"""

import _runner_bootstrap  # noqa: F401  (sys.path setup)
import advanced_nmap_scanner as scanner


def chain_for(inference=None, cod_hex="N/A", vendor="", name="",
              lmp_features=None, chipset_info=None, gatt_appearance=None,
              gatt_conn_params=None, sdp_full_records=None,
              behavioral_summary=None):
    """build_evidence_chain with every argument defaulted to 'not observed'."""
    if inference is None:
        inference = {"device_type": "Smartphone", "os": "Android",
                     "major_minor_version": "Android 13 (Tiramisu)",
                     "confidence": "High"}
    return scanner.build_evidence_chain(
        inference, cod_hex, vendor, name, lmp_features, chipset_info,
        gatt_appearance, gatt_conn_params, sdp_full_records, behavioral_summary,
    )


def entries_named(chain, signal_name):
    return [e for e in chain if e["signal_name"] == signal_name]


# --- 1. supporting pair -----------------------------------------------------

def test_agreeing_cod_and_appearance_records_a_supporting_entry():
    """
    0x5a020c is CoD major class 2 (Phone); the "Generic Phone" Appearance maps
    to the same major class. Two independent category signals agreeing is
    exactly the "supports" record the paper says the chain emits - and the
    kind that was missing from all 43 archived scans.
    """
    chain = chain_for(cod_hex="0x5a020c",
                      gatt_appearance={"gatt_appearance_category": "Generic Phone"})
    pair = entries_named(chain, "cod_vs_gatt_appearance")
    assert len(pair) == 1, f"expected exactly one pair entry, got {chain}"
    assert pair[0]["direction"] == "supports", pair[0]
    assert pair[0]["weight"] > 0


# --- 2. conflicting pair ----------------------------------------------------

def test_disagreeing_cod_and_appearance_records_a_conflict():
    """CoD says Phone (2), Appearance says Watch (7) - an independent conflict,
    not a scoring artifact, since Appearance played no part in the prediction
    when a real CoD was present."""
    chain = chain_for(cod_hex="0x5a020c",
                      gatt_appearance={"gatt_appearance_category": "Generic Watch"})
    pair = entries_named(chain, "cod_vs_gatt_appearance")
    assert len(pair) == 1, f"expected exactly one pair entry, got {chain}"
    assert pair[0]["direction"] == "conflicts", pair[0]


# --- 3. single signal -------------------------------------------------------

def test_a_lone_signal_produces_no_pair_entry():
    """
    A pair check needs both halves. With CoD present but no Appearance at all,
    the CoD/Appearance and name/Appearance pairs must both stay silent - and
    silence here is correct, not the bug B2 is chasing.
    """
    chain = chain_for(cod_hex="0x5a020c", gatt_appearance=None)
    assert entries_named(chain, "cod_vs_gatt_appearance") == []
    assert entries_named(chain, "name_vs_gatt_appearance") == []


# --- 4. dependent pair that must be skipped ---------------------------------

def test_appearance_standing_in_for_absent_cod_is_not_counted_as_support():
    """
    With no CoD, predict_device_core falls back to Appearance to derive
    device_type. Recording that same Appearance as evidence "supporting"
    device_type would be the scorer agreeing with itself. The entry must be
    marked "primary" (a scoring input), never "supports", and it must not be
    counted as a conflict either.
    """
    inference = {"device_type": "Wearable (Smartwatch/Band)", "os": "Embedded Firmware (RTOS)",
                 "major_minor_version": "Wearable Device (LMP 11)", "confidence": "High"}
    chain = chain_for(inference=inference, cod_hex="N/A",
                      gatt_appearance={"gatt_appearance_category": "Generic Watch"})

    assert entries_named(chain, "cod_vs_gatt_appearance") == [], (
        "the CoD/Appearance pair must not fire when there is no CoD to compare against"
    )
    standin = entries_named(chain, "gatt_appearance")
    assert len(standin) == 1, f"expected the stand-in entry to be recorded, got {chain}"
    assert standin[0]["direction"] == "primary", standin[0]
    assert not any(e["direction"] == "supports" for e in chain), (
        f"a circular stand-in signal was recorded as independent support: {chain}"
    )


# --- 5. empty input ---------------------------------------------------------

def test_no_observed_signals_yields_an_empty_chain():
    """Nothing observed must yield an empty chain, not a crash and not a
    fabricated entry."""
    inference = {"device_type": "Unknown Peripheral", "os": "Unknown",
                 "major_minor_version": "Unknown", "confidence": "Low"}
    assert chain_for(inference=inference) == []


# --- 6. the Appearance-free pair -------------------------------------------

def test_cod_and_name_pair_fires_without_any_appearance():
    """
    Pairs 7 and 8 both need GATT Appearance, found on 2 of 115 archived
    records, which is why the chain almost never fired. This pair uses only
    Class-of-Device and the advertised name, so it must fire with no
    Appearance present at all - that is the whole point of adding it.
    """
    chain = chain_for(cod_hex="0x5a020c", name="Pixel 7", gatt_appearance=None)
    pair = entries_named(chain, "cod_vs_device_name")
    assert len(pair) == 1, f"expected the Appearance-free pair to fire, got {chain}"
    assert pair[0]["direction"] == "supports", pair[0]


def test_cod_and_name_pair_reports_contradictory_inputs_as_a_conflict():
    """
    A device whose CoD says Phone while its name resolves to Audio means the
    prediction rests on two inputs that contradict each other. Both halves fed
    the prediction, so this is not the same independence argument as pair 7;
    it is still not circular, because the check compares the two inputs with
    each other rather than with the output.

    Note on the example: "Galaxy Buds2" was the original conflict this pair
    surfaced on archived data, but that turned out to be a defect in our own
    name derivation (see test_name_category.py) rather than a device
    contradiction, and fixing it made that case agree. The case below is a
    genuine disagreement between what the device declares and what it calls
    itself, which is what the check is meant to catch.
    """
    chain = chain_for(cod_hex="0x5a020c", name="JBL Speaker", gatt_appearance=None)
    pair = entries_named(chain, "cod_vs_device_name")
    assert len(pair) == 1, f"expected exactly one pair entry, got {chain}"
    assert pair[0]["direction"] == "conflicts", pair[0]


# --- 8. an untested check must not be recorded as agreement ------------------

def test_undatable_chipset_is_not_recorded_as_support():
    """
    The Modalias chronology check compares a chipset's release year against the
    predicted OS. With no release year it never runs, and "it did not
    contradict the prediction" is then vacuously true. Recording that as
    "supports" would inflate the agreement count with corroboration that was
    never tested - the same failure the primary/circularity handling exists to
    prevent. Found on a live AirPods scan, where the chipset model resolved but
    carried no year.
    """
    chipset = {"chipset_model": "Apple AirPods (family)",
               "estimated_chipset_release_year": None,
               "estimated_min_os_hint": None}
    chain = chain_for(chipset_info=chipset)
    entry = entries_named(chain, "modalias_chipset")
    assert len(entry) == 1, f"expected the resolved model to be surfaced, got {chain}"
    assert entry[0]["direction"] == "unused", entry[0]
    assert entry[0]["weight"] == 0.0, entry[0]


def test_datable_chipset_still_reports_agreement():
    """The guard above must not silence the check when it can actually run."""
    chipset = {"chipset_model": "BCM4345C0",
               "estimated_chipset_release_year": 2016,
               "estimated_min_os_hint": "Android 7+"}
    chain = chain_for(chipset_info=chipset)
    entry = entries_named(chain, "modalias_chipset")
    assert len(entry) == 1, chain
    assert entry[0]["direction"] == "supports", entry[0]
    assert entry[0]["weight"] > 0


if __name__ == "__main__":
    from _runner import run

    raise SystemExit(run())
