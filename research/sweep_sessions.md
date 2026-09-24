# Sweep session log

Tracks location/time metadata for each `--discover`/`--measure` session, since
`candidates.json`/`availability_raw.jsonl` record exact timestamps but no
location (by design - no location is needed for the scan itself). This file
pairs the two for later write-up in the larger-sweep section of the paper.
Not part of the manuscript.

| Session | Date | Approx. time | Location | Candidates | Measured | Connectable |
|---|---|---|---|---|---|---|
| 1 | 2026-08-31 | ~18:58-19:0X (evening) | Public place | 27 | 27 | 1 |
| 2 | 2026-09-01 | ~14:38 (afternoon) | Dorm room (private) | 6 new (2 excluded, see note) | 4 | 1 |
| 3 | 2026-09-02 | ~14:40 (afternoon) | Cafe (public) | 23 new (2 excluded, see note) | 21 | 1 |

## Own-device exclusion policy

Already-paired/bonded devices (the researcher's own phone, laptop
peripherals, etc.) connect far more easily than a genuine unknown/unbonded
device, so including them would bias the connectability rate upward and
isn't representative of what the sweep is meant to measure (unknown public
devices). When one is spotted in `candidates.json`, it must be excluded
before its measurement counts toward the sweep.

**Exclusion method:** move the full record(s) - not just the MAC - out of
`candidates.json`/`availability_raw.jsonl` and into
`research/availability_raw_own_devices.jsonl` (and a matching
`candidates_own_devices.json`), the same "archive, don't delete" pattern
already used for superseded sweep rounds
(`availability_raw.jsonl.stale_*`). This keeps the sweep's own numbers
clean while preserving the excluded records for audit or for a possible
future paired-vs-unknown comparison.

## Notes

- **Session 2 own-device exclusion:** 2 of the 6 candidates seen in the dorm
  room were the researcher's own already-paired devices (`İrem İpad`,
  `DE:85:2F:CF:4A:01` "LOGI M240" mouse). **Process error:** these were
  deleted outright rather than archived per the policy above - only their
  MAC, name, and device_type survive (in this log), not their full
  measurement record (GATT/SDP results, timestamps). Not recoverable.
  Policy above adopted after this to prevent a repeat. "Measured" and
  "Connectable" counts above are post-exclusion (31 total candidates
  across sessions 1-2, 4 of session 2's remaining ones measured with 1
  connectable).
- **Same mouse found in the original n=20 pilot:** `DE:85:2F:CF:4A:01`
  ("LOGI M240") also appears in the archived pilot data
  (`availability_raw.jsonl.stale_pre_taxonomy`, gatt_appearance_category
  "HID: Mouse"). The same personal-device contamination issue was already
  present in the original n=20 pilot reported in
  Section~4.1/`sec:pilot-availability` of the paper - at least 1 of that
  pilot's 20 addresses is the researcher's own device, not an unknown
  public one. Not yet corrected in the paper text; worth deciding whether
  to note this as a limitation or to identify and exclude any other
  personal devices from that archived set before the larger-sweep write-up.
- **Session 3 own-device exclusion (fixed process):** 2 of the 23
  candidates seen were the researcher's own devices - `9C:A9:C5:69:8F:91`
  ("İrem (AirPods)") and a second sighting of `DE:85:2F:CF:4A:01`
  ("LOGI M240"). This time the exclusion policy above was followed
  correctly: both full records were moved to `candidates_own_devices.json`
  before `--measure` ran, so nothing was lost. A third device,
  `9C:58:84:1A:0E:5C` ("Mehmet MacBook Air"), was also seen - this is a
  named, identifiable device but belongs to someone else, not the
  researcher, so it is not own-device bias and was left in the sweep
  (covered by the paper's existing passive-listening ethics justification,
  not a new consideration).
