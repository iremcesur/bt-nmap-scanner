# Layered BT Scanner

Active Bluetooth security & OS fingerprinting scanner — an `nmap`-style tool for Bluetooth Classic/BLE devices. It forces a baseband connection to a target MAC address, pulls hardware telemetry (RSSI, LMP version, link quality), enumerates SDP/GATT services, and runs a layered inference engine to infer device type, OS, OS version, and exposed permissions.

What separates it from a rule engine that just prints a guess: every prediction carries an **evidence chain** — a per-signal audit trail saying what was observed and whether it supports or conflicts with the answer — and conflicting evidence *lowers* the reported confidence instead of being discarded.

See [bluetooth_project_documentation.md](bluetooth_project_documentation.md) for the full theory guide (protocols, inference engine, scoring model, evidence chain).

## The three layers

| Layer | What it does | Where |
| :--- | :--- | :--- |
| **Layer 1 — Telemetry** | Baseband/hardware reads: RSSI, link quality, TX power, L2CAP RTT, LMP version (via a custom C binary over HCI), SDP profile list, GATT UUIDs, D-Bus cache | `GET /api/advanced_nmap/:mac` |
| **Layer 2 — Fingerprinting** | GATT Appearance, preferred connection parameters, the full SDP attribute tree, Modalias → chipset/vendor resolution, chipset-vs-OS chronology check | same scan, same endpoint |
| **Layer 3 — Behavioral** | Observes one device over a time window (default 45 s): repeated telemetry samples and passive BLE advertising-interval capture, streamed live | `GET /api/behavioral_scan/:mac` (SSE) |

On top of those sits the post-hoc audit: the evidence chain, the chipset/OS consistency flags, and a cross-encounter check against earlier observations of the same device.

## Requirements

- Linux with BlueZ installed (`hcitool`, `l2ping`, `sdptool`, `gatttool`, `bluetoothctl`)
- Node.js (developed on v20)
- Python 3 (developed on 3.12) with the system D-Bus/GLib bindings:
  ```bash
  sudo apt install python3-dbus python3-gi
  ```
  These are system packages, not pip installs — the scanner talks to BlueZ over D-Bus.
- `libbluetooth-dev` (only if you need to rebuild `version_finder`, see below)

## Project structure

```
backend/    Express API (port 4001) that spawns the Python scanner
  routes/           advanced_nmap, discover, behavioral_scan, feedback
  routes/pythonfiles/
    advanced_nmap_scanner.py   the scanner + inference engine + evidence chain
    observation_store.py       pseudonymized cross-encounter observation store
    discover_devices.py        passive device discovery over BlueZ D-Bus
    chipset_database.py, bluetooth_company_ids.py, lmp_features.py,
    appearance_values.py       lookup tables
    version_finder_integrated.c / version_finder   HCI-level LMP extractor
frontend/   React 19 dashboard
tests/      stdlib-runnable test suite
```

## Setup

```bash
# backend
cd backend
npm install
node index.js        # listens on http://localhost:4001

# frontend (separate terminal)
cd frontend
npm install
npm start            # opens http://localhost:3000
```

The frontend calls the backend at `http://localhost:4001` (see `frontend/src/AdvancedNmap.jsx`).

### Rebuilding `version_finder`

`backend/routes/pythonfiles/version_finder` is a prebuilt binary that extracts the LMP version over HCI. It's architecture-specific — if it doesn't run on your machine, rebuild it from source:

```bash
cd backend/routes/pythonfiles
gcc -o version_finder version_finder_integrated.c -lbluetooth
```

## Usage

Most Bluetooth commands (`hcitool`, `l2ping`, etc.) require elevated privileges. Either run the backend with `sudo`, or grant the Node binary the needed capabilities:

```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(which node)
```

### API

| Endpoint | Purpose |
| :--- | :--- |
| `GET /api/discover` | Passive ~6 s discovery sweep; returns nearby devices with RSSI |
| `GET /api/advanced_nmap/:mac?logGroundTruth=true\|false` | Full Layer 1 + 2 scan; returns the JSON report |
| `GET /api/behavioral_scan/:mac?duration=45&interval=2&ble=true` | Layer 3 behavioral scan, streamed as Server-Sent Events (one JSON object per event) |
| `POST /api/feedback` | Records ground truth for an earlier scan — body: `{ mac, timestamp, is_correct, actual_value, notes }` |

The scanner can also be run directly:

```bash
cd backend/routes/pythonfiles
python3 advanced_nmap_scanner.py AA:BB:CC:DD:EE:FF false
python3 advanced_nmap_scanner.py --behavioral AA:BB:CC:DD:EE:FF 45 2 --ble
```

### Output files

Written to the **current working directory** of whatever launched the scanner, not to a fixed path:

- `historical_scans.jsonl` — one full JSON report per scan, always appended.
- `research_evaluation.csv` — the flattened ground-truth evaluation set. Only written when the caller passes `logGroundTruth=true` (the dashboard's "I can verify this device" checkbox, unchecked by default). Every row implicitly claims someone can eventually say whether the prediction was right, so scans of devices nobody can verify are deliberately kept out.
- `observation_store.jsonl` + `observation_store_salt.DO_NOT_RELEASE.bin` — the cross-encounter store, next to `observation_store.py`.

All of these are gitignored. They contain third-party device data and stay local.

## Privacy

This tool scans other people's devices. A MAC address is personal data on its own, and advertised device names in practice often contain personal names.

- Scan archives (`historical_scans.jsonl`, `research_evaluation.csv`) are never committed.
- The cross-encounter store keys records by a **salted HMAC pseudonym**, never by MAC, and stores no advertised names. The salt makes the pseudonyms irreversible in practice — publishing it would undo that, so `*.DO_NOT_RELEASE.bin` is gitignored and must stay that way.
- Only scan devices you own or have permission to scan.

## Tests

The suite is plain assert-style functions. It runs under `pytest` if you have it, but the system Python here is externally managed (PEP 668) with no pytest, so each module is also directly runnable with nothing but the standard library:

```bash
cd tests
python3 test_evidence_chain.py
python3 test_prediction_pipeline.py
python3 test_observation_store.py
python3 test_android_score_ladder.py
python3 test_name_category.py
```

Coverage is on the parts that can be tested without a radio: the Android score ladder, name→category inference, the prediction pipeline wrapper, the evidence chain, and the observation store.

## Status & limitations

- **Confidence is not calibrated.** `confidence_score` is a convenience number derived from the qualitative label for sorting and filtering — it is not a probability. The evidence-chain weights are provisional placeholders, not fitted to ground truth.
- The Layer 3 behavioral scan is exposed over the API but has no dashboard UI yet.
- OS-version inference (e.g. LMP 13 → Android 15 / Windows 11) is a heuristic ladder over hardware age, not a measurement.
