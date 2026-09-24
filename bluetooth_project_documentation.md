# Advanced Bluetooth Security & OS Fingerprinting Engine
**Comprehensive Project Documentation & Theory Guide**

---

## 1. Introduction to Bluetooth Technology
Bluetooth is a short-range wireless communication technology operating in the 2.4 GHz ISM band. Modern Bluetooth is split into two entirely different protocols that share a name:
- **Classic Bluetooth (BR/EDR)**: Used for continuous, high-bandwidth data streaming (e.g., Audio headsets, file transfers). It uses standard pairing and profiles.
- **Bluetooth Low Energy (BLE)**: Designed for short bursts of data with minimal power consumption (e.g., Smartwatches, IoT sensors). It uses GATT (Generic Attribute Profile) to expose data states.

### Core Concepts
- **MAC Address**: A 48-bit unique identifier. Modern devices use **Randomized MACs** to prevent tracking, changing their broadcast address every few minutes.
- **LMP (Link Manager Protocol)**: The hardware-level protocol that manages the physical radio connection.
- **L2CAP**: The multiplexing layer. It takes data from higher-level apps and chops it into radio packets.
- **SDP (Service Discovery Protocol)**: The "phonebook" of Classic Bluetooth. It tells other devices what features (Audio, Contacts, etc.) this device supports.

---

## 2. Project Overview: "Bluetooth Nmap"
Standard Bluetooth scanners only show you the Name, MAC address, and Signal Strength. They are easily fooled by randomized MAC addresses and fake names.

**What we built:**
We built a highly advanced, active scanner that acts like `nmap` for Bluetooth. Instead of trusting the surface-level broadcast, our scanner forcefully establishes a baseband connection, extracts the raw hardware data, interrogates the protocol software stacks, and runs a mathematical heuristic engine to definitively identify the exact device type, operating system, hardware age, and permissions—regardless of what the device claims to be.

---

## 3. Data Extraction: What We Pull & How
We bypass the standard OS APIs and use low-level Linux sockets (`hcitool`, `l2ping`, `sdptool`, `gatttool`, and a custom C binary) to extract data.

1. **Hardware Telemetry (Baseband)**:
   - **Absolute RSSI**: The raw radio signal strength in dBm.
   - **Link Quality (LQ)**: A 0-255 scale representing the packet drop rate (interference).
   - **TX Power**: The transmission power level of the target device.
2. **Latency (L2CAP Ping)**: We send ICMP-like pings over the Bluetooth L2CAP layer to measure response times (RTT).
3. **Software Protocols (SDP & GATT)**: We dump the entire Service Discovery Protocol tree and attempt to read BLE GATT characteristics.
4. **Hardware Versioning (LMP Extraction)**: Our custom C-binary drops down to the HCI (Host Controller Interface) level to forcibly extract the exact LMP version number (which correlates to the Bluetooth specification year).

---

## 4. The Inference Engine: How We Guess Everything

### A. Distance Estimation
Bluetooth RSSI is *relative*. A weak signal might mean the device is far away, OR it might mean the device is right next to you but in "low power mode".
- **How we fix it**: We normalize the RSSI against a baseline (-60 dBm at 1 meter).
- **The Math**: We use a log-distance path loss model: `Distance = 10 ^ ((-55 - Absolute RSSI) / 20)`. 
- **The Output**: Because radio waves bounce off walls, we floor/ceil the result to provide a realistic interval (e.g., `Approx. 1 - 2 meters`).

### B. OS & Version Fingerprinting (The Pipeline)
This is the heart of the engine. Hardware alone isn't enough (an Android phone and a Windows PC might use the exact same Intel Bluetooth chip). We must look at the *Software Fingerprint*. The engine evaluates devices in a strict priority order:

> [!IMPORTANT]
> **Priority 1: The Exact Android Engine**
> Android phones expose very specific services to interact with cars/smartwatches. If we see `PBAP` (Phonebook Access) or `MAP` (Message Access), we know it is a mobile phone. 
> We then calculate a **Weighted Score** (out of 10.0) based on their LMP hardware age and the presence of advanced codecs (like `DID` and `A2DP`). 
> *Example: LMP 13 + High Audio profile = Score 9.2 = Android 15.*

> [!NOTE]
> **Priority 2 & 3: IoT and Apple**
> If the hardware vendor is an embedded manufacturer (Espressif, Tuya), we classify it as an IoT Peripheral. If the vendor is Apple or it exposes `Wireless iAP` (Apple's proprietary protocol), we classify it as iOS/macOS.

> [!WARNING]
> **Priority 4: The PC/Laptop Fallback**
> If it failed the Android/Apple checks, we look at the vendor. If the Bluetooth chip is made by Intel, Qualcomm, Realtek, or Cloud Network, it is almost certainly a computer. 
> - If the device exposes `BlueZ` or `Ubuntu` markers, we classify it as Linux.
> - Otherwise, we default to **Windows**. We use the LMP version to guess the OS age (e.g., `LMP 13` = `Windows 11`, `LMP 10` = `Windows 10`).

> [!TIP]
> **Priority 5: Audio Peripherals (Earbuds/Speakers)**
> Earbuds often block SDP requests once paired to a phone. If everything else fails, but the device name contains "Airdopes", "Airpods", "Sony", or it has a base-level `A2DP` flag, we classify it as an Embedded Audio RTOS device.

### C. Permissions Inference
We translate complex hex protocols into human-readable privacy risks:
- `HFP` / `A2DP` -> **Audio & Microphone Access**
- `PBAP` -> **Contacts & Call History**
- `MAP` -> **SMS/Text Messages**
- `PAN` -> **Internet Tethering**

---

## 5. Layer 2: Deeper Fingerprinting Signals

Layer 1 (section 3) is what the radio hands us. Layer 2 is what we get by asking the device *more specific questions* — signals the quick scan doesn't need, collected in the same pass:

- **GATT Appearance (0x2A01)**: a BLE device self-declares a category (Phone, Watch, Heart Rate Sensor…). Useful, but self-reported — so it is treated as a claim to be checked, not as truth.
- **Preferred Connection Parameters (0x2A04)**: connection interval, slave latency, supervision timeout. Power-saving peripherals and phones pick characteristically different values.
- **Full SDP attribute tree**: not just *which* profiles exist, but the raw service-name and description strings inside each record, which frequently leak vendor/OS wording the profile list alone doesn't.
- **Modalias → chipset resolution**: BlueZ's `modalias` (`bluetooth:v001Dp1200d1436`) decodes to vendor/product/version IDs, which we map to a concrete chipset model and its approximate release year.

### The Chipset/OS Chronology Check
The chipset's release year is a hard lower bound on plausibility: a chip that shipped in 2023 cannot be sitting inside a device running an OS version from 2016. When the predicted OS version and the chipset's era disagree, an **inconsistency flag** is raised and the confidence label drops one level. The prediction itself is left alone — the engine reports the contradiction rather than quietly resolving it.

---

## 6. Layer 3: Deep Behavioral Scan

A single-shot scan is a photograph. Some properties only appear over *time*, so Layer 3 (`--behavioral`, or `GET /api/behavioral_scan/:mac`) watches one device for a window (default 45 s, sampling every 2 s) and streams each measurement out as it happens over Server-Sent Events.

What the window reveals that one sample cannot:
- **RSSI variance over time** — a device whose signal drifts is being carried; a rock-steady one is sitting on a shelf. A handheld/worn pattern contradicts a "stationary peripheral" classification, and that contradiction is recorded.
- **BLE advertising interval** (captured passively, without connecting) — advertising cadence and shifts in it separate power-managed peripherals from phones.
- **Link stability** — whether the device drops and re-accepts connections across the window.

The scan is interruptible: if the HTTP client disconnects, the backend sends `SIGTERM` rather than killing the process, so the Python side exits its sampling loop cleanly and still emits a summary of what it collected.

---

## 7. The Evidence Chain: Why the Answer, Not Just the Answer

The scoring engine produces a prediction. A separate, **post-hoc** pass then re-examines every Layer 1/2/3 signal and records, per signal, one entry:

| Field | Meaning |
| :--- | :--- |
| `signal_name` | which signal (e.g. `gatt_appearance`, `cod_major_class`) |
| `observed_value` | what was actually read |
| `inference` | what that reading means on its own |
| `direction` | `supports`, `conflicts`, `primary`, or `unused` |
| `weight` | provisional, **not** ground-truth calibrated |

Three design rules matter more than the list:

1. **No circularity.** A signal that was already fed *into* the score cannot then be recorded as evidence *for* it — that entry would only be confirming a total it was itself added into. Such signals are marked `primary` (a scoring input) and excluded from the conflict count.
2. **Absence is recorded too.** A signal that was unavailable (an undatable chipset, a device that refused SDP) is logged as `unused` at weight zero rather than silently omitted, so a short chain is legible instead of ambiguous.
3. **The audit can only subtract.** Conflicting evidence lowers the confidence label one level. Nothing in the audit ever *raises* confidence or changes the predicted OS/device type.

`confidence_score` is a numeric convenience derived from that final label, for sorting and filtering the evaluation CSV. **It is not a calibrated probability** and should not be read as one.

---

## 8. Cross-Encounter Comparison

When a device is scanned again, the earlier scans can be checked against the current one — but only in a deliberately narrow way.

- **Observations are stored, never predictions.** Comparing a new prediction against archived predictions from the same scorer measures only that the scorer agrees with itself; a systematically biased scorer agrees with itself perfectly. Raw readings carry no such circularity: two scans reporting different Class-of-Device bytes for one address disagree about a fact, and at most one can be right.
- **Only invariants are compared**: `modalias`, Class of Device, OUI vendor. These do not legitimately change between two scans minutes apart. RSSI, RTT, battery and connection parameters are stored for availability analysis but never compared for equality — varying is what they do.
- **The result is asymmetric.** A mismatch is evidence that something is wrong and is recorded as `conflicts`. A match is *not* evidence: a signal that reads the same way twice may be stably right or stably wrong, so it is recorded at weight zero as `unused`.
- **It never enters the score.** Like every other post-hoc check it can only annotate and lower confidence. A prediction must not become more confident merely because the device was seen before.

**Privacy**: a MAC address is personal data, so this store would otherwise become another archive of raw addresses. Records are keyed by a **salted HMAC pseudonym** instead, and no advertised device name is stored (names in this project frequently contain personal names). The salt file is never published — with it, the pseudonyms would be reversible by brute force over the address space.

---

## 9. Protocols Dictionary

| Protocol / Profile | What it stands for | What it actually does |
| :--- | :--- | :--- |
| **A2DP** | Advanced Audio Distribution Profile | High-quality stereo audio streaming (Music, YouTube). |
| **HFP** | Hands-Free Profile | Low-quality mono audio + Microphone (Phone calls). |
| **PBAP** | Phonebook Access Profile | Allows a car or smartwatch to download your contacts. |
| **MAP** | Message Access Profile | Allows a car or smartwatch to read/send your SMS text messages. |
| **AVCTP** | Audio/Video Control Transport | Allows you to press "Pause" or "Skip Track" on your earbuds and have it control your phone. |
| **RFCOMM** | Radio Frequency Communication | A serial port emulator. Very old, but heavily used for basic data transfer. |
| **L2CAP** | Logical Link Control | The core multiplexer. Everything runs on top of this. |
| **GATT** | Generic Attribute Profile | The entire basis of BLE. It organizes data into "Services" (e.g., Heart Rate) and "Characteristics" (e.g., 85 BPM). |
| **HID** | Human Interface Device | Tells the OS that the device is a Keyboard, Mouse, or Gamepad. |

---

## Summary of the Engine Flow

1. **User inputs MAC address** (or picks one from the passive `/api/discover` sweep).
2. **Layer 1 — Scanner opens sockets** -> RSSI, link quality, TX power, multi-ping RTT, LMP version via the C binary, SDP handles/profiles, GATT UUIDs, D-Bus cache.
3. **Layer 2 — Deeper interrogation** -> GATT Appearance & connection parameters, the full SDP attribute tree, Modalias -> chipset & release year.
4. **Cross-encounter check** -> The observation is built and compared against prior observations of the same device *before* it is stored, so a scan is never compared against itself.
5. **Inference Engine evaluates** -> Distance, power state, market target, OS type, OS version, permissions.
6. **Post-hoc audit** -> Chipset/OS chronology check + evidence chain; conflicts lower the confidence label, never the prediction.
7. **Outputs** -> Full JSON report appended to `historical_scans.jsonl`; a flattened row written to `research_evaluation.csv` *only* when the caller declared the device verifiable.
8. **React dashboard renders** -> The report, including the evidence chain, laid out for review.

**Layer 3** runs separately and on demand (`/api/behavioral_scan/:mac`), streaming its samples live rather than returning one buffered report.
