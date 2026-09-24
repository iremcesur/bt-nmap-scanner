# Supervisor Review and Revision Guideline

**Paper:** Layered, Evidence-Aware Bluetooth Fingerprinting: Connection-Free Signals and Conflict-Aware Inference
**Author:** Irem Cesur, CYSECDIGITAL, THM Friedberg
**Draft reviewed:** version of 2026-09-09, about 5,400 words, 15 references, 4 tables, 1 figure
**Reviewer:** Adnan Kujovic (supervisor)
**Date:** 2026-09-09

---

## 0. How to use this document

This is a full review plus a revision plan. It is written so that it can be worked through item by item, including with an AI assistant.

Read this section before starting.

**Three categories of finding.** Each item is tagged.

- `[TEXT]` can be fixed by editing the manuscript. No new data, no code changes.
- `[CODE]` requires a change to the scanner or the inference code, and re-running the numbers. Editing the text alone produces a manuscript that is wrong in a new way.
- `[DATA]` requires new measurements. It cannot be written around.

**Four rules for anyone working on this paper, human or AI.**

1. Do not invent, estimate, extrapolate or round any measured value. Every number in the paper must come from a run that actually happened. If a number is needed and does not exist, mark it `[MISSING]` and leave it.
2. Do not fix a contradiction by deleting the honest half. Several findings below are contradictions between an overclaiming sentence and an accurate one. The accurate sentence stays and the overclaiming one changes. Never the reverse.
3. Do not remove the limitations sections. The self-criticism in this draft is a genuine strength and reviewers reward it. What has to go is not the honesty, it is the defects that the honesty currently describes.
4. Verify every claim in Section 2 below against the actual source code before acting on it. This review was written from the PDF. Two findings depend on the exact contents of Table I, which did not extract cleanly. They are marked accordingly.

**Verdict.** In its current state the paper would be rejected at any venue that takes it seriously. It is not far from acceptable. The distance is three blocking defects, about a day of text corrections, and one decision about framing. The rest of this document is the route.

---

## 1. What is already good

State this plainly because it decides what not to touch.

- The reframing from a system paper to a measurement paper is done and it is convincing. The abstract, Section V and the conclusion now agree that no accuracy is claimed.
- The separation of "never reached", "reached but quiet" and "reached with signal" is exactly the right instrument, and it was not there before.
- The confidence intervals are correct. All four were recomputed independently, including the one-sided interval for the zero count.
- Table IV is internally consistent. The counts add up in both rounds.
- Retracting the connection-free claim for Modalias in Section V is the single most credible passage in the paper. Reviewers notice this.
- Separating Layer 3 as consent-only is correct and should be moved forward, not left in Section VI.

None of this needs revision. Everything below does.

---

## 2. Blocking defects

These three must be resolved before submission anywhere. They cannot be fixed by rewriting.

### B1. The Android version ladder has an unreachable class `[CODE]`

Section III-D defines the scaling as `s = (raw / 105) * 10` and the ladder as `>= 7.2` maps to Android 13 and `>= 7.15` maps to Android 12.

Every base value and every bonus in Table I is an integer, so the raw score is always an integer. The Android 12 band therefore requires a raw score in the interval [75.075, 75.6), which contains no integer.

Verified by direct computation:

| raw | s | predicted |
|---|---|---|
| 74 | 7.0476 | Android 11 |
| 75 | 7.1429 | Android 11 |
| 76 | 7.2381 | Android 13 |

**Android 12 can never be predicted, and a one point difference in the raw score moves the prediction two releases.**

This has a second consequence. Section III-C states that provisional score adjustments "can nudge a score within a branch but never flip a prediction". Both provisional adjustments in Table I are worth one point. A single provisional point takes a device from 75 to 76, that is from Android 11 to Android 13. The guarantee as written is false.

Required:

1. Confirm against the source code that all bonuses are integers. If any is fractional this finding changes and must be recomputed.
2. Redesign the mapping so that every class in the label space is reachable. The cleanest fix is to define the ladder directly on the integer raw score rather than on a scaled float, and to derive the boundaries from the base table rather than hand-picking them.
3. Fix the two defects the paper already names: make the LMP base non-decreasing in LMP version, and clip or renormalise after the bonuses.
4. Re-run every prediction in the paper after the fix.
5. Remove the passage in Section III-D that announces these bugs as future work. Once fixed there is nothing to announce.

Do not publish a scorer that is known to be broken. The current draft treats disclosure as a substitute for correction. It is not. A reviewer who has to decide whether to trust any number in the paper will decide here, and will decide against.

### B2. The evidence chain is empty for a reason the paper has not identified `[CODE]`

Section V reports that over 43 scans the chain was empty and `has_conflicting_signals` was false in every case. The paper explains this by the rarity of conflicting signal pairs.

That explanation does not fit the paper's own algorithm. Algorithm 1 appends an entry for every independent pair, tagged SUPPORTS, CONFLICTS or PRIMARY. Absence of conflicts explains a false conflict flag. It does not explain an empty chain. If no SUPPORTS entry was ever produced either, then the loop appended nothing at all across 43 scans, and that points at an implementation fault rather than at a property of the data.

A second inconsistency in the same mechanism: PRIMARY is defined in Section III-C as the tag for the case where only one of two signals carries a value, that is, a signal that is the sole basis for a decision. But the loop iterates over unordered pairs. With exactly one signal present there are no pairs and the loop body never executes, so the single-signal case, which is the most common case in the measurement, produces no record at all. The definition and the algorithm describe different things.

A third: Section III-C says the chain is "a list of records, one per signal". Algorithm 1 produces one record per signal pair. These are different data structures.

Required:

1. Write five unit tests before touching the measurement: one supporting pair, one genuinely conflicting pair, one lone signal, one dependent pair that must be skipped, and one empty input. Show that each produces the intended chain entry.
2. Fix whatever those tests expose.
3. Reconcile the three descriptions. Decide whether the chain is per signal or per pair, and make Section III-C, Algorithm 1 and the implementation agree.
4. Re-run the archive after the fix and report the result, whatever it is.
5. Compute the expected firing rate from your own data instead of reporting the observed zero as if it were informative. You have the co-presence statistics: Section V already states that 29 of 43 scans carried at least two independence-relevant signals. From that plus the rate at which those pairs disagree you can state what firing rate the design predicts. If the prediction is near zero, say so. That is a real finding about the design and it is much stronger than an unexplained null.

Until this is done the central methodological contribution of the paper has no evidence at all behind it.

### B3. The data protection basis for the sweep that already happened `[DATA]`

Section VI-C states that 52 third-party addresses were actively queried, that the raw archive stores each MAC in cleartext, and that a formal ethics determination, a written data handling and retention policy and a responsible disclosure procedure "are not yet in place".

The problem is the ordering. Institutional review belongs before collection, not after it. Reporting the gap honestly is correct, but honesty does not repair a sequence. Several security venues now require an ethics statement at submission and will desk-reject on this.

Note what this finding does and does not say. It does not say that a legal violation occurred. It says the basis on which the collection proceeded is not documented in a way a reviewer or a data protection officer could check.

Required, in this order:

1. Obtain a written determination from the THM data protection officer covering the collection that has already taken place. Not the responsible investigator, the data protection officer. Many German universities have no ethics board competent for computer science, so the determination or a DSFA-style assessment is the artefact that exists and can be cited.
2. Pseudonymise the existing archive now. The salted HMAC belongs at collection time, not at release time. The relevant question under data protection law is what is held, not what is published.
3. State a retention period in the paper. Its absence is a defect on its own.
4. Re-anchor the legal claim. Reference [11] is a CNIL document on audience measurement in public spaces. For a German affiliation the load-bearing sources are Art. 4(1) GDPR together with EDPB guidance. Keep CNIL as a secondary citation at most.
5. Rewrite Section VI-C to report the determination rather than its absence. Do not present a later review as retroactive prior approval. If the determination cannot be obtained for the data already collected, the honest route is to repeat the measurement under a cleared protocol and drop the current numbers.
6. Separate the two acts. Section VI-B correctly says that passive observation and active connection attempts are ethically different. Section VI-C then applies one blanket justification to both. Justify them separately.

One observation that belongs in this section and is currently missing: 62 of 70 addresses were never reached. The study therefore consists mostly of failed connection attempts against strangers' devices. That is the worst possible ratio of ethical cost to data yield, and a reviewer will say so. Addressing it is a reason to fix the pipeline before collecting again, not a reason to hide the number.

---

## 3. Internal contradictions

Seven places where the paper contradicts itself. All are `[TEXT]`. Budget about one day for the whole section. A reviewer who finds two of these stops trusting the rest.

**T1. The title contradicts Section V.**
The title says "Connection-Free Signals". Section V says the stronger connection-free claim was retracted. The footnote to Table II says "Only the RF family is fully connection-free". The paper disproves its own title.
Fix: remove "Connection-Free" from the title. Something in the direction of "Cache-Read and Low-Cost Signals" is accurate. Whatever is chosen, the title must not claim a capability the body withdraws.

**T2. Two rounds or five.**
Section V, Method: "Two rounds were run". Section V, discussion: "what five rounds of availability data increasingly suggest".
Fix: state the true number. If earlier informal rounds exist, describe them in Method or do not count them. The sentence that draws the paper's main implication currently rests on a number that appears nowhere else.

**T3. Two addresses or six.**
Section V: "The two addresses reached in the sweep were both read over SDP". Table IV: sweep reached = 6, of which 2 exposed a signal and 4 were reached but quiet.
Fix: the sentence means the two signal-bearing addresses. Say that. This is the exact distinction the paper introduces one paragraph earlier, so getting it wrong here is conspicuous.

**T4. The abstract does not carry the hedge the body carries.**
Abstract: "none combines low interaction cost, multi-OS granularity, and an honest account of uncertainty". Section II: "Preliminary search; not yet a completed systematic review". Section IV correctly writes "among the approaches surveyed".
Fix: the abstract must carry the same restriction. A preliminary search cannot support a universal non-existence claim. The same applies to "none exists" about a shared corpus in the non-goals paragraph.

**T5. Replaces or annotates.**
Abstract: the approach "replaces the single fused score with an evidence chain". Section III-A: the chain "is never itself an input to the score that produced the prediction, so it cannot change which OS or device type is predicted, only how much confidence is reported". The Figure 1 caption says the same.
Fix: the abstract is wrong. The chain supplements the score, it does not replace it. This is the paper's central mechanism, so getting its description wrong in the first paragraph is expensive.

**T6. Weighted scorer or rule cascade.**
Sections III-A, III-E and the Figure 1 caption describe a single weighted scorer that consumes all signals. Section III-D describes a fixed-priority rule cascade in which only the Android branch computes a numeric score.
Fix: use one vocabulary throughout. The accurate description is the cascade. Correct the earlier sections to match, not the other way round.

**T7. Output granularity.**
Table II lists the output of this work as "OS + type + BT-era + market + permissions". The body and Table III claim an OS version, and Table III's footnote says "M3 refines it with the added signals".
Fix: Bluetooth generation, device age and installed OS version are three different quantities. State which of them the system actually outputs and make the two tables and the body agree. If the OS version output is not validated, do not list it as a produced output.

---

## 4. Claims that exceed the evidence

Each row is a sentence that a reviewer can challenge and the paper cannot defend. All `[TEXT]` unless noted.

| Claim | Where | Problem | Required change |
|---|---|---|---|
| "read from a connection the baseline already opens" | Abstract, contribution 1 | `hcitool info` and SDP run over a BR/EDR ACL connection. GATT runs over LE. These are different transports and therefore different connections. If so, the central cost advantage of the design is false. | `[CODE]` Verify against the implementation. Add a table giving, per signal, whether it is BR/EDR, LE or a cache read. If GATT needs its own LE connection, withdraw the claim and state the true connection count. |
| "the cache is populated by a prior pairing" | Section III-B, repeated | In BlueZ, Modalias is derived from the Device ID record over SDP for BR/EDR, or the PnP ID characteristic of the GATT Device Information Service for LE, and is held in the settings storage. BlueZ also maintains a cache directory for devices that were never paired. Whether pairing is required, or whether connection or service discovery suffices, is not established. | Verify against the BlueZ storage layout and the source. State the mechanism precisely and cite it. If the source is the DID record over SDP, then this is not a new signal, it is the Layer 2 SDP read, and the contribution collapses. |
| "absent for a never-paired target" | Section III-B | Does not follow from the preceding sentence, which allows "pairing or connection". A never-paired device may have been connected. | Make the two sentences consistent once the mechanism is established. |
| "the 64-bit LMP features mask" | Section III-B | `hcitool info` returns feature page 0. Extended features on pages 1 and 2 require Read Remote Extended Features. Also, LMP features are BR/EDR. LE-only devices expose LE features instead. | Say page 0. Add the BR/EDR versus LE distinction here and in the signal table from row 1. |
| "Only a chipset released after the latest plausible release year of the predicted OS version is a genuine cross-signal conflict" | Section III-C | A device released later can run older software, and an OS version can be ported to newer hardware. The one-sidedness is right but the retained direction is still not a logical exclusion. | Downgrade to a plausibility warning, or demonstrate a concrete technical incompatibility. Also state whether Modalias resolves an actual chipset or only a vendor and product identifier, because the reference signal is otherwise itself uncertain. |
| "the additions raise granularity at near-zero marginal connection cost" | Section III-E | Cost is never measured. Additional GATT and SDP queries cost packets, time and failure probability even when no new connection is opened. | `[DATA]` Measure it: connection attempts, queries issued, wall-clock time per address, with and without the added layers. This is cheap and it converts an assertion into a result. |
| "an out-of-date OS is a precondition for many attacks" | Section I | "Precondition" is stronger than "risk factor" and is not shown. | Weaken to what reference [10] actually supports. |
| "signal availability, not classifier quality, is the first-order constraint" | Conclusion | The measurement does not compare these two causes. It measures one of them, with a pipeline that has not passed a positive control. | Restate as what was measured: most addresses were not reached by this pipeline. Draw the comparison only after the positive control exists. |
| "such coincidence is rare in the wild" | Section V | Co-presence of independent signal pairs is not quantified. The proxy count of 29 of 43 is stated to be a loose proxy over a single-owner sample. | Quantify co-presence properly, or present this as the hypothesis the next round tests, which is how the same paragraph already ends. Do not do both. |
| "permissions summary" and market-segment label | Section III-E | Appear for the first time in the summary of what is new. No rules, no validation, no mention earlier. Also, the set of exposed services does not by itself establish what access rights exist. | Either introduce and validate them in Section III-B, or remove them from the contribution list and from Table II. |
| 42 of 43 records predate the current build | Section V | Inferred from a missing `confidence_score` field. Without version metadata that inference does not hold, and older inputs can still exercise new logic if they carry the needed fields. | Record a build identifier per scan going forward. For the existing archive, state the inference as an inference. |

---

## 5. Information a reviewer needs and cannot find

All `[TEXT]`, all cheap, all currently missing.

1. **Address type breakdown.** For each round, how many addresses were public, random static, resolvable private, non-resolvable private. This is present in every advertising packet and costs nothing to extract. It probably explains the headline result: if most of the 52 were resolvable private addresses of non-connectable advertisers, then "never reached" is not a finding, it is the expected outcome. This is the single highest-value addition in this entire document.
2. **Device count bounds, not just address counts.** Unique addresses are an upper bound on device count. Clustering by advertising payload and manufacturer data gives a lower bound. Report the range. As written, n=52 is 52 observed addresses and the number of devices is unknown, which makes every percentage over that denominator hard to interpret.
3. **Environment.** BlueZ version, kernel version, adapter model, controller Bluetooth version, scan parameters, connection timeout, retry policy. For a paper whose central result is that the pipeline could not reach devices, omitting the controller model is disqualifying.
4. **Units.** The paper counts addresses in some places, scans in others, devices in others. State the unit next to every number.
5. **Both denominators for Modalias.** "0 of 52" mixes two effects: the cache was empty, and 46 of those addresses were never reached anyway. Report availability both over all discovered addresses and over reached addresses.
6. **The complete rule set.** Section III-D gives the Android branch in full, which is good and above average. The other five branches are described in prose only, and the initial assignment of High, Medium and Low is never stated.
7. **The baseline.** Footnote 1 declares the baseline scanner unpublished and not a contribution, while every contribution in the paper is a delta against it. No reviewer can evaluate a delta against an object they cannot see. Either publish the baseline as part of the artefact, or drop the delta framing and describe the system as a whole with proper attribution to the group.

---

## 6. The framing decision

This is the most important item in the document and it is a decision, not a defect.

The paper currently contains three competing theses.

- (a) Here is a layered fingerprinting design.
- (b) Signal availability, not classifier quality, is the first-order constraint.
- (c) Signal co-presence is the binding constraint for conflict-aware inference.

(b) and (c) are the same idea, and they are the only one that any data supports. (a) is unsupported: there is no accuracy result, no ablation, and the evidence chain has never fired. A paper that leads with (a) invites exactly the question it cannot answer.

There is also a fourth framing available, and it is better than all three.

**Section VI-A states that every signal used is declared by the target device and cryptographically unbound, and calls this a fundamental limit. Take that seriously.** If the target can lie about every signal, then the fingerprint is only meaningful against a non-adversarial target, that is, in inventory and audit settings, not in a security setting against a motivated adversary. The first sentence of the abstract currently implies the opposite.

But a lying device is precisely a device whose independent signals disagree with each other. That is what the conflict flag detects. **The evidence chain is an inconsistency detector, and inconsistency detection is a spoofing detector.** Under that framing:

- The mechanism has a clear purpose that no cited prior work provides.
- The zero firing rate over 43 scans becomes a result rather than an embarrassment: on a set of presumably honest devices the detector produced no false positives. That is weak, but it is evidence, and it is reportable.
- The base rate problem becomes the paper's honest thesis: at the observed co-presence rate, conflict-aware inference is not yet deployable. That is a negative result about a proposed method, which is publishable at the right venue.
- The threat model stops being inverted.

**Recommendation.** Choose one of two structures and commit to it.

**Structure A, availability paper.** Title and abstract lead with the availability result. The design becomes one section of context. The claim is: here is what a low-interaction Bluetooth audit can actually observe in the wild, and the binding constraint is reachability and co-presence, not classifier quality. Requires no new large measurement. This is the fast route.

**Structure B, inconsistency detection paper.** Title and abstract lead with the conflict mechanism as a detector for devices that misreport their own metadata. The availability measurement becomes the evidence that the mechanism's base rate is low. Requires B2 fixed and at least one demonstrated firing on a deliberately inconsistent device, which can be produced in the lab by configuring one. This is the stronger paper.

Do not attempt both in one submission. The current draft attempts three and lands none.

---

## 7. What to measure next

`[DATA]` throughout. Ordered by value per hour.

**M1. The controlled pairing experiment. One afternoon.**
The current comparison between an n=18 office pilot and an n=52 three-location sweep varies at least four things at once: location, familiarity, pairing history and time. Attributing the Modalias difference to familiarity alone is not supported by that design.

Do this instead: one location, one host, one adapter, one session, two device sets that you own or are authorised to use, one paired and one not. Record the cache state before and after. Separate the connect step from the pair step so you can tell which one populates Modalias.

This converts the paper's headline claim from something close to a definitional truth about caches into a controlled result, and it also settles the mechanism question in Section 4 above.

**M2. Positive control and a second adapter. Half a day.**
The paper already names the missing positive control. Add to it a second adapter with a different chipset, run against the same address set. This separates pipeline and controller effects from device behaviour far more convincingly than a positive control alone, because the current reachability result is fully confounded with the firmware of one dongle.

**M3. Cost measurement. Half a day.**
Connection attempts, queries issued, wall-clock time per address, with and without Layers 1 and 2. Turns "near-zero marginal cost" from an assertion into a measured claim.

**M4. A deliberately inconsistent device. Half a day.**
Only needed for Structure B. Configure a device whose declared metadata contradicts itself, and show the chain firing on it. One demonstrated firing changes the paper's status completely.

**M5. The real campaign. About a week.**
Four environment types, for example transit hub, campus, residential and retail, with the address type breakdown recorded from the start and pseudonymisation applied at collection time. Expect a few thousand addresses. This is what turns a feasibility note into a measurement paper, and it is the highest-value use of a month of work, well ahead of any rewriting.

M5 must not start before B3 is resolved.

---

## 8. Route to acceptance

Two tracks. Pick one now, because they lead to different papers and the same content cannot be submitted twice.

### Track 1: fast, ICISSP 2027 position paper, deadline 22 October 2026

The position paper track is explicitly for work in progress. The paper is that. SciTePress, indexed in Scopus and DBLP. Realistic acceptance.

Scope: Structure A. No new large measurement. M1 and M2 only.

| Week | Work |
|---|---|
| 1 | B3 started, that is the request to the data protection officer, plus pseudonymisation of the existing archive. In parallel: all of Section 3 and Section 5 of this document. |
| 2 | B1 and B2. Unit tests, scorer fix, re-run. Section 4 claim corrections. |
| 3 | M1 and M2. Restructure to Structure A. |
| 4 | Full pass, style pass, internal review, submit. |

The critical path is B3. Everything else is under Irem's control, that one is not, so the request goes out on day one.

One consequence to accept deliberately: if this is accepted at ICISSP, the same content cannot go to WiSec later. Only a substantially extended version can. That is why Structure A is the right choice for this track: it fixes the contribution as the availability result and leaves the conflict mechanism free for a later, separate paper.

### Track 2: stronger, ACM WiSec 2027 short paper or ARES 2027, roughly March 2027

WiSec runs a six page short paper track for mature work of a succinct nature, in two cycles, with the second around March. It is the thematic home of this work. ARES has a comparable window and a short paper track, and is European.

Scope: Structure B. Everything in Track 1 plus M4 and M5.

This is the better paper and it is achievable. It requires the evidence chain to work and to have fired at least once, and it requires a measurement with real statistical weight.

### Definition of done

Do not submit anywhere until every line is checked.

- [ ] B1 fixed, every class reachable, numbers re-run
- [ ] B2 fixed, five unit tests pass, chain re-run over the archive, expected firing rate computed
- [ ] B3 resolved, written determination obtained, archive pseudonymised, retention period stated, GDPR anchor replacing CNIL as primary
- [ ] T1 to T7 corrected
- [ ] Every row of Section 4 either substantiated or weakened
- [ ] Address type breakdown present
- [ ] Device count bounds present
- [ ] Environment fully specified
- [ ] Units stated next to every number
- [ ] Baseline published, or delta framing dropped
- [ ] One thesis, not three
- [ ] Abstract and body say the same thing about the mechanism
- [ ] Every table agrees with every other table and with the body
- [ ] Reference [15] replaced by the underlying publication rather than the press release
- [ ] Style pass done, see Section 9

---

## 9. Style

The writing is above average for a first-author student paper and unusually self-critical, which reviewers reward. Two mechanical problems.

**Dashes.** The draft contains 41 em dashes in about 5,400 words. That is roughly one every 130 words, and it is the most recognisable marker of AI-assisted text. Most of them are doing the work of a comma, a colon or a full stop. Replace them. Where a dash is genuinely marking an aside, prefer a comma pair or brackets.

**Nested sentences.** Several sentences carry three subordinate clauses and an aside. Target about 19 words per sentence on average. Split rather than compress.

**Revision notes in the manuscript.** Phrases such as "a claim we retracted", "we correct in the next round" and "the subject of the next submission" read as notes to a supervisor rather than as a scientific contribution. A paper states its current, consistent position. Keep the substance of the retraction, which is honest and correct, and drop the narrative of having changed your mind.

**Repetition.** The Modalias limitation and the disclaimer that no accuracy is claimed each appear four or more times. State each once, clearly, in the right place. That frees roughly half a column for the measurement detail that is currently missing.

---

## 10. Two questions to settle before starting

1. **Authorship.** Will the paper remain single author. At ICISSP and comparable venues a known name in the author list makes a practical difference. At WiSec, which is double blind, it does not. This changes the venue calculation and should be decided before, not after, the revision.
2. **Which structure.** Section 6, Structure A or Structure B. Everything downstream depends on it, and the two tracks in Section 8 diverge immediately.
