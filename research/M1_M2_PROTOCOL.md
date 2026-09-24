# M1 / M2 — measurement protocol

Run these before writing anything further about Modalias. Both are
instrument-calibration runs on **your own devices**; neither touches third
parties, so neither needs the DPO clearance that gates a new public sweep.

Tool: `research/modalias_experiment.py`. Output appends to
`research/modalias_experiment.jsonl`.

---

## What is actually in question

The paper says Modalias "comes from a prior pairing". Nothing in the code
supports that. `query_dbus_properties()` reads BlueZ's cached `Device1`
properties and has no visibility into how the cache was filled. At least four
mechanisms fit the sweep data equally well:

1. a prior **bond** (link key on this adapter),
2. a prior plain **connection** without bonding,
3. the device volunteering it during **discovery**,
4. BlueZ populating it from something else entirely.

The sweep cannot separate these because every variable moved at once. M1 holds
all of them fixed but one.

---

## M1 — one location, one adapter, four states

**Constant throughout:** same room, same adapter (`hci0`), same device set,
same day if possible. Use 3–5 devices you own, with a mix of BR/EDR and BLE.

**Do not skip the cold state.** It is the only state that can falsify the
paper's claim, and it is the only one that needs the cache clear below.

### State 1 — `cold`

**Do not skip this state.** It is the only one that can falsify the paper's
claim.

There are two ways to reach it. Use the first.

#### Preferred: per-device removal (non-destructive)

BlueZ stores bonds per adapter *and per device*, under
`/var/lib/bluetooth/<ADAPTER-MAC>/<DEVICE-MAC>/`. Removing one device removes
only that subtree, so the rest of your pairings are untouched:

```bash
bluetoothctl remove AA:BB:CC:DD:EE:FF     # one device, bond + cached object
bluetoothctl info AA:BB:CC:DD:EE:FF       # expect: Device not available
bluetoothctl scan on                      # ~10 s, then off. No connect, no pair.
python3 research/modalias_experiment.py --m1 --state cold \
    --devices AA:BB:CC:DD:EE:FF --location lab-a \
    --note "bluetoothctl remove; other pairings left intact"
```

Pick devices that currently *do* expose Modalias, so there is something to
watch disappear and come back, and that are cheap to re-pair. Mixing a
`bluetooth:`-prefixed Modalias with a `usb:`-prefixed one is worth doing: they
come from different numbering spaces and may behave differently.

**Caveat that must be reported.** `bluetoothctl remove` clears *our* side of
the bond. The device generally still holds its own side, so this is a
one-sided cold state, not a mutual one: the peer may still treat us as a known
host. For at least one device, also delete the pairing in the device's own
Bluetooth settings, and record in `--note` which devices got the mutual
treatment. If the one-sided and mutual cases differ, that difference is itself
a finding and the paper should say so rather than averaging over it.

#### Fallback: full adapter wipe (destructive — avoid if you can)

Only if you need a guaranteed-clean adapter state. This deletes **every**
pairing on the adapter. Back up first:

```bash
sudo tar czpf ~/bluetooth-pairings-backup.tgz /var/lib/bluetooth/
sudo systemctl stop bluetooth
sudo rm -rf /var/lib/bluetooth/<ADAPTER-MAC>/*
sudo systemctl start bluetooth
```

Restore with:

```bash
sudo systemctl stop bluetooth
sudo tar xzpf ~/bluetooth-pairings-backup.tgz -C /
sudo systemctl start bluetooth
```

### State 2 — `scanned`

Passive discovery only, no connection:

```bash
bluetoothctl scan on   # ~10 s, then off
python3 research/modalias_experiment.py --m1 --state scanned \
    --devices AA:.. BB:.. CC:.. --location lab-a
```

### State 3 — `connected` (connected, **not** bonded)

```bash
bluetoothctl connect AA:..      # do NOT pair
bluetoothctl info AA:..         # confirm: Connected: yes / Paired: no
python3 research/modalias_experiment.py --m1 --state connected \
    --devices AA:.. --location lab-a
```

This is the discriminating state. Modalias appearing here means a connection is
sufficient and bonding is not required — a materially weaker and much more
interesting claim than the one in the paper.

### State 4 — `bonded`

```bash
bluetoothctl pair AA:..
bluetoothctl info AA:..         # confirm: Paired: yes
python3 research/modalias_experiment.py --m1 --state bonded \
    --devices AA:.. --location lab-a
```

### Reading the result

| First state where Modalias appears | What the paper may then say |
|---|---|
| `cold` | Not pairing-derived at all. Delete the claim; the mechanism is unknown. |
| `scanned` | The device advertises it. "Prior pairing" is wrong. |
| `connected` | A connection suffices; bonding is not required. Weaken the claim. |
| `bonded` | The claim is supported — for these devices, on this adapter. Say exactly that. |
| never | Inconclusive until M2 passes. See below. |

`--state` is **declared, not verified**: the script cannot tell whether you
really cleared the cache. Paste the commands you actually ran into `--note`.

---

## M2 — positive control and a second adapter

M1's "never" row is the trap. A null result there has two explanations —
the devices do not expose Modalias, or this adapter/BlueZ build never records
it — and M1 cannot tell them apart. A study that reports the first without
excluding the second is reporting an artifact.

### M2a — positive control on the primary adapter

Deliberately bond one device you control, then:

```bash
bluetoothctl pair DD:..
python3 research/modalias_experiment.py --m2 --control DD:.. \
    --devices AA:.. BB:.. CC:.. --adapter hci0 --location lab-a
```

If the bonded control shows **no** Modalias, the script stops and tells you the
instrument is broken. That is the correct outcome: every null from that adapter
is uninterpretable, and nothing about Modalias availability may be reported
from it.

### M2b — repeat on a second adapter

Different hardware, ideally a different chipset vendor:

```bash
python3 research/modalias_experiment.py --m2 --control DD:.. \
    --devices AA:.. BB:.. CC:.. --adapter hci1 --location lab-a
```

Same devices, same room, same day. A per-device result that differs between
`hci0` and `hci1` is an **adapter** property, not a device property.

#### If only one adapter is available

M2b cannot be run, and no substitute closes it. Two consequences, both of
which belong in the paper rather than being quietly dropped:

1. Every Modalias availability figure is conditioned on one controller (here
   an Intel, LMP 5.3). State the controller and BlueZ version next to the
   figure, and say plainly that whether it generalizes across controllers is
   untested. One sentence; do not imply coverage you did not measure.
2. M2a still runs and still does its main job. A bonded positive control that
   produces Modalias proves *this* adapter records it, so a null on another
   device is attributable to that device rather than to a broken instrument.
   That is the confound that would otherwise invalidate M1; the second adapter
   addresses generalizability, which is a weaker claim.

A second adapter also offers a non-destructive route to the `cold` state,
since bonds are per adapter: a never-used controller sees every device as
never-paired. With one adapter, the per-device `bluetoothctl remove` method in
M1 State 1 gets you the same thing for a chosen subset.

---

## The two denominators

The paper currently reports one Modalias availability figure. There are two,
and they answer different questions:

- **D1 — all addresses encountered** (52 in the public sweep). Answers: how
  often is Modalias available *in the wild*? This is the operationally honest
  number, and it is small.
- **D2 — addresses that were actually reached** (2 of 52). Answers: given that
  we got a connection at all, how often is Modalias there? A percentage over
  n = 2 should be written as a raw count, never as a percentage.

Report both, labelled, with the raw counts. A single unlabelled percentage
silently picks one and reads as the other.

---

## What to bring back

For each of M1 and M2: the state table, the raw `modalias_experiment.jsonl`,
the exact commands run, and the adapter/BlueZ versions the script recorded. If
M2 fails, report that and stop — a failed instrument check invalidates the M1
series run on that adapter, and re-running M1 first would waste the effort.
