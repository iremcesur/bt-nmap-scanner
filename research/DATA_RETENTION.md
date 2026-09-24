# Data protection, retention and deletion — Bluetooth signal-availability study

Status: **draft, pending written confirmation from the THM Data Protection
Officer.** Nothing here has been approved by the DPO yet; the request was
prepared on 2026-09-10 (see `DPO_REQUEST.md`). Until that confirmation
arrives, treat every retention period below as proposed, not settled.

Every `[PLACEHOLDER]` is a fact I do not have and must not invent.

---

## 1. What was collected

| Archive | Records | Third-party? | Identifiers held |
|---|---|---|---|
| `historical_scans.jsonl` | 43 scans, 9 distinct devices | mixed | MAC, advertised name, vendor, service list |
| `research_evaluation.csv` | 43 rows | mixed | same, flattened |
| `research/candidates.json` | 52 addresses | yes | MAC, advertised name, first-seen timestamp |
| `research/availability_raw.jsonl` | 52 records | yes | MAC, per-signal availability, failure reasons |
| `research/availability_raw_pilot_cleaned.jsonl` | 18 records | yes | as above |
| `research/availability_raw_pilot_own_devices.jsonl` | 2 records | no (researcher's own) | as above |
| `research/*.stale_*` | 59 records total | yes | superseded rounds, kept for auditability |
| `backend/historical_scans.jsonl` | 31 scans, 13 devices | **yes, 12 of 13** | full scans: MAC, advertised name (several contain given names), permissions profile, RTT, uptime, AFH map |
| `backend/routes/pythonfiles/historical_scans.jsonl` | 2 scans | no | own devices |

**Why three copies.** The scanner opens `historical_scans.jsonl` by relative
path, so the archive is written wherever it happens to be run from. Three
copies accumulated in three directories and only the repo-root one was under
review until 2026-09-13. All are now enumerated in `check_release_clean.py`,
which additionally walks the tree for archives in locations nothing knows
about, and `.gitignore` matches these filenames at any depth.

No payload, no content, no pairing attempt, no authentication material was
recorded. What *was* recorded, and what the paper must stop describing as "no
device identity": **the MAC address, and in the two full-scan archives the
advertised device name**, which is frequently personal (one archived name
contains a person's first name).

## 2. Legal basis

Primary: **GDPR Art. 4(1)** — a Bluetooth MAC address is an online identifier
and therefore personal data where it can be linked, directly or indirectly, to
a natural person. Processing basis claimed: **[PLACEHOLDER — Art. 6(1)(f)
legitimate interest or Art. 6(1)(e) public interest / Art. 89 research
safeguards; the DPO must state which applies at THM].**

The CNIL guidance previously cited in the paper is French supervisory-authority
material and is retained only as secondary, illustrative support. It is not the
governing basis for a study run in Germany and must not be presented as such.

## 3. The ordering problem — stated plainly

Institutional ethics review was **not** obtained before collection. The active
Layer 2 sweep against 52 third-party addresses ran on 2026-08-31, and the
request to the DPO was raised on 2026-09-10, ten days after. This is the wrong
order and cannot be presented otherwise. The paper's ethics section must say so
in those terms; a retrospective approval, if granted, does not convert this
into a pre-approved study.

## 4. Retention periods (proposed)

| Data | Retention | Rationale |
|---|---|---|
| Raw archives with MACs in the clear | **delete by 2027-03-31**, or 30 days after camera-ready, whichever is earlier | Only needed until the pseudonymized release is verified reproducible |
| Pseudonymization salt | **destroy together with the raw archives** | While it exists the release is reversible; destroying it makes pseudonymization irreversible in fact, not just in policy |
| Pseudonymized release (`research/release/`) | retain **5 years** from publication | Standard reproducibility window; [PLACEHOLDER — confirm against THM's own research-data policy] |
| Derived aggregate counts in the paper | indefinite | Not personal data |

Deletion is not "stop using": it means removing the files **and** the salt, and
confirming no copy survives in git history (see §6).

## 5. Pseudonymization

Applied to every archive with one shared salt:

    python3 research/pseudonymize_archive.py --salt-file \
        research/pseudonymize_salt.DO_NOT_RELEASE.bin IN OUT

MACs become `dev-<10 hex>` = HMAC-SHA256(salt, uppercased MAC); advertised
names become `name-<10 hex>` over the same salt. Verify before any release:

    python3 research/check_release_clean.py     # exit 0 = clean

This gate re-reads the files on disk and fails on any surviving MAC, any device
name present in the raw archives, or salt material inside `research/release/`.

Caveat that must stay in the paper: at n of a few dozen, in a single location,
pseudonymization is **not** anonymization. A vendor OUI plus a coarse timestamp
can still narrow to a small set. The release is pseudonymized personal data
under GDPR, not anonymous data, and remains in scope of the Regulation.

## 6. Outstanding — git history

`.gitignore` previously listed `backend/historical_scans.jsonl` and
`backend/research_evaluation.csv`, but the scanner writes both to the
repository **root**, so the rules never matched. The paths are fixed now, but
`.gitignore` does not apply to already-tracked files, and these are committed:

    historical_scans.jsonl                      research_evaluation.csv
    research/candidates.json                    research/candidates.json.stale_pre_taxonomy
    research/availability_raw.jsonl             research/availability_raw.jsonl.stale_pre_fix
    research/availability_raw.jsonl.stale_gatttool_broken
    research/availability_raw.jsonl.stale_pre_taxonomy

Raw MACs and device names are therefore in git history. Removing them requires
`git rm --cached` plus a history rewrite (`git filter-repo`) and a force-push,
which rewrites every commit hash — **not done here, because it is destructive
and it is the repository owner's call.** If the repository is or will be
public, this is the highest-priority item on this page. If it has only ever
been local and private, it is a cleanup task, not an incident.

## 7. Data subject rights

Contactless observation of a broadcast identifier gives no channel to reach the
device owner, so Art. 13 notification is not achievable in the field. This is a
real limitation, not a solved problem, and the paper should present it as one.
Route for anyone who does come forward: **[PLACEHOLDER — contact address the
DPO designates].**
