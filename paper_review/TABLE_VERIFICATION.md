# Table II / III cell verification checklist

`latest.tex` now carries two comparison tables:

- **`tab:signals`** — signals read and outputs emitted, 18 rows × 9 methods,
  marks `✓` / `×` / `–`.
- **`tab:cap`** — the axes a binary mark would misrepresent (interaction cost,
  ground-truth corpus, uncertainty handling).

Every cell has a provenance. This file records it, because a binary mark that
turns out to be wrong is less defensible than the free-text cell it replaced —
a reader can argue with prose, but a `×` is a flat assertion about someone
else's work.

Three symbols are in use. `–` is not a hedge: it means *the source was not read
closely enough to settle this cell*, and it exists so the table never asserts
an absence we did not check. There are **17 such cells out of 162** (37 `✓`, 108 `×`). Resolving
them is what turns the preliminary survey (§II) into a completed one.

---

## Tier 1 — filled from primary evidence, safe to defend

| Column | Source of truth | Notes |
|---|---|---|
| **KV** (Kavisankar et al.) | The IEEE PDF, read in full | See per-cell evidence below |
| **TW** (this work) | Our own source, function by function | See per-cell evidence below |

### KV cells and the text that supports them

| Row | Mark | Evidence in the paper |
|---|---|---|
| 2 SDP service list | ✓ | §III-A: OS type from the access-point profile — Android NAP, Linux GAP/BlueZ, iOS iAP, Windows PANU |
| 12 RSSI | ✓ | Eq. 4 (mean RSSI), Figs. 2 and 4, Table IV `RSSI` column |
| 13 Echo / RTT timing | ✓ | §III-B reverse L2ping; Table IV `Beh value`, `Res` columns |
| 15 Device type | ✓ | Table IV `Device type` column |
| 16 OS family | ✓ | Table IV `SDP value` column (Android) |
| 17 OS version | ✓ | Table IV `Identified version` column |
| 18 CVE mapping | ✓ | Table IV `CVE` column; stated contribution 2 |
| 1, 4–11, 14 | × | No mention anywhere in the paper. Confident. |
| **3 SDP attribute tree** | × | **Weakest KV cell.** They say "SDP profile information" throughout and never describe attribute-level parsing, but they never explicitly exclude it either. If challenged, soften to `–`. |

### TW cells and the code that supports them

| Row | Function |
|---|---|
| 1 Class-of-Device | `decode_cod_major_class` |
| 2 SDP service list | `get_sdp_services` |
| 3 SDP attribute tree | `get_sdp_full_service_details`, `extract_sdp_hints` |
| 4 LMP version | `get_hcitool_info` |
| 5 LMP feature bitmap | `parse_lmp_features` |
| 6 Modalias | `decode_modalias`, `enrich_modalias_with_chipset` |
| 7 GATT UUIDs | `get_gatt_uuids` |
| 8 GATT Appearance | `query_gatt_appearance` |
| 9 GATT conn. parameters | `query_gatt_preferred_conn_params` |
| 10 GATT Device Info | `query_deep_gatt` (software/firmware revision) |
| 11 Vendor OUI | `lookup_oui` |
| 12 RSSI | `×` — see below |
| 13 Echo / RTT | `×` — see below |
| 14 Radio / clock skew | × — we have no RF front end |
| 18 CVE mapping | × — we do not map to CVEs |

### Rows 12 and 13 were `✓` and are now `×`

Both were corrected after tracing the call graph, and the reason is worth
recording because it changed the paper, not just the table.

**RSSI.** `_infer_mobility_conflict` turns a high RSSI variance into an
evidence-chain conflict, and `build_evidence_chain` accepts a
`behavioral_summary` argument to carry it. Nothing passes one. The single
call site of `predict_device` in `main()` passes the literal `None`, and
`behavioral_main` — the `--behavioral` Layer 3 entry point, driven by
`backend/routes/behavioral_scan.js` — streams NDJSON events to the operator
and never calls the scorer at all. The code is implemented and unreachable.

**Echo / RTT.** `measure_rtt` feeds `infer_deep_metadata`, which produces a
`power_state` string. That is reported metadata, not an input to device type,
OS family or OS version. Under this table's row definition it is `×`.

Consequences applied elsewhere in the paper:

- Fig. 1's Layer 3 arrow into the scorer is now dashed and labelled
  "not wired in current pipeline".
- The §III-A overview no longer says Layer 3 feeds the prediction.
- §III-B now states plainly that Layer 3 is measurement infrastructure, not a
  signal layer on the same footing as Layers 1–2.
- §Comparison no longer claims rows 12–13 are shared with Kavisankar et al.;
  it now says the opposite, that they use those signals for the version
  decision and we do not.

This is the fourth paper-vs-code discrepancy found in this review pass, after
the C helper short-circuit, the chronology check direction, and the confidence
ladder.

---

## Tier 2 — filled from our own §II summaries, NOT from the sources

These are the cells to check before submission. Each was inferred from what
`sec:related` already says about the work, which is not the same as having
verified it against the source.

### BL (the baseline we extend) — whole column

Filled from the specification we wrote in §II: Class-of-Device, summarized SDP
service list, GATT UUIDs, vendor OUI, LMP version, single weighted score, no
Modalias. Internally consistent by construction, but **a reviewer cannot check
any of it** — this is referee item M7-7, still open. The fix is not to the
table; it is to publish the baseline's signal/output set as an appendix.

### CC (Celosia & Cunche) — highest risk in the table

| Row | Current | What to check |
|---|---|---|
| **8 GATT Appearance** | `–` | **Check this first.** Their method fingerprints BLE devices from the GATT profile, and Appearance (0x2A01) is a standard characteristic. If it is in their feature set, this becomes `✓` and our claim that Appearance is used by this work alone must be withdrawn from §Comparison. |
| 9 GATT conn. parameters | `–` | Same feature-set question |
| 10 GATT Device Info | `–` | DIS is a common fingerprint source; likely `✓` |
| 11 Vendor OUI | `–` | Do they use the address at all, or only GATT contents? |
| 7 GATT UUIDs | ✓ | Safe — this is the paper's subject |
| 15 Device model | ✓ | Safe — stated in title/abstract |

### PA (Pferscher & Aichernig)

| Row | Current | What to check |
|---|---|---|
| 13 Echo / RTT timing | `–` | Was `✓` on the inference that active automata learning sends inputs and observes outputs. Withdrawn: that argument establishes they send packets, not that *timing* is a feature. Verify against the source. |
| 4, 5 LMP | `–` | Automata learning over the link layer may well cover LMP exchanges |
| 15 Device type | `–` | Their output is a state machine; whether they derive a device label from it is unclear from our summary |

### BP (Blueprinting)

| Row | Current | What to check |
|---|---|---|
| 3 SDP attribute tree | `–` | Was `✓` on the inference that "hashes Classic SDP records" implies attribute-level parsing. Withdrawn — the phrase is equally consistent with hashing the service list. Confirm against the source. |
| 1 Class-of-Device | `–` | Does the blueprint include the device class? |
| 11 Vendor OUI | `–` | Does it use the address prefix? |

### IB (InsideBlue / GhostBLE)

| Row | Current | What to check |
|---|---|---|
| 8, 9, 10 GATT metadata | `–` | Genuinely ambiguous, and the row definition is why: the row asks whether a signal is *an input to the method's own output*. These tools dump GATT without interpreting it, so they read the bytes but derive nothing from them. Decide once whether "dumped but not interpreted" counts as `✓`, then apply it to all three. |

### BT (BlueToolkit)

| Row | Current | What to check |
|---|---|---|
| 2 SDP service list | `–` | Does it enumerate services to select CVE probes? |
| 7 GATT UUIDs | `–` | Same |
| 11 Vendor OUI | `–` | Same |

### RF and clock-skew

Row 14 `✓`, row 15 `✓`, everything else `×`. Low risk: these methods operate
below the protocol layer by definition. No action.

---

## `tab:cap` cells needing work

| Cell | Status |
|---|---|
| KV interaction cost | **Solid.** Up to ~3000 packets, reset at 259 packets on Android 14 and 1152 on Android 10 (their Fig. 3b), reset rates 12% / 20% (their §IV). |
| KV ground-truth corpus | **Solid, and worth stating exactly as it is:** their Table II lists 23 devices, but Table IV reports findings for only 8 — one per Android version. The two iPhones and six embedded devices in Table II never appear in the results, so the OS-*type* claim (Android/Linux/iOS/Windows via NAP/GAP/iAP/PANU) is never demonstrated. |
| **TW interaction cost** | **Closed.** `research/measure_scan_cost.py` instruments the scanner and counts radio-facing operations: **27** against a fully responsive target, **35** against an unresponsive one. Reproduce with `python3 research/measure_scan_cost.py`. Two cautions the paper already carries: these are *operations*, not packets, so they are not comparable to the ~3000-packet figure in the same row; and the unresponsive case is the *expensive* one, because failed probes trigger connection-setup retries (`hcitool cc`/`dc` ×4 each). A cold sweep of unfamiliar devices is therefore the upper bound, not the lower one. |
| TW ground-truth corpus | 8 devices / 43 scans, 7 labelled. Verified against `research_evaluation.csv`. |
| All other ground-truth cells | `–` — not assessed. Acceptable only while §II is declared preliminary. |

---

## One claim that must change if CC row 8 comes back `✓`

§Comparison currently says rows 3, 5, 6 and 8–10 carry a `✓` only in the last
column. If Celosia & Cunche turn out to use Appearance, conn. parameters or the
DIS string, that sentence is false and the table must show it. The sentence is
written to be checkable against the table precisely so this stays a one-line
fix rather than a buried error.
