import sys
import subprocess
import json
import re
import unicodedata
import socket
import time
import urllib.request
import os
import signal
import threading
import queue
import statistics
import dbus

from lmp_features import decode_features_bitmap
from chipset_database import lookup_chipset, resolve_usb_vendor_name
import observation_store
from appearance_values import resolve_appearance, appearance_category_to_cod_major
from bluetooth_company_ids import lookup_bluetooth_company_id

VERSION_FINDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version_finder")

def log(msg):
    print(f"[>] {msg}", flush=True)

def decode_baseband_features(hex_str):
    if not hex_str or hex_str == "Unknown": return "Unknown"
    
    byte_map = {
        0: {0: "3-Slot Packets", 1: "5-Slot Packets", 2: "Encryption", 3: "Slot Offset", 4: "Timing Accuracy", 5: "Role Switch", 6: "Hold Mode", 7: "Sniff Mode"},
        1: {0: "Park State", 1: "RSSI", 2: "CQDDR", 3: "SCO Link", 4: "HV2 Packets", 5: "HV3 Packets", 6: "u-law Voice", 7: "A-law Voice"}
    }
    
    parts = hex_str.split()
    decoded = []
    
    if len(parts) >= 2:
        try:
            b0 = int(parts[0], 16)
            b1 = int(parts[1], 16)
            for bit, name in byte_map[0].items():
                if (b0 >> bit) & 1: decoded.append(name)
            for bit, name in byte_map[1].items():
                if (b1 >> bit) & 1: decoded.append(name)
        except: pass
        
    if not decoded: return hex_str
    return ", ".join(decoded)

def hex_to_ascii(hex_str):
    try:
        return bytes.fromhex(hex_str.replace(" ", "")).decode('utf-8', 'ignore').strip()
    except:
        return None

def query_deep_gatt(mac_address):
    log("Running deep GATT extraction (Model/Firmware/Battery)...")
    gatt_meta = {}

    chars = {
        "model_number": "2a24",
        "serial_number": "2a25",
        "firmware_revision": "2a26",
        "hardware_revision": "2a27",
        "software_revision": "2a28",
        "manufacturer_name": "2a29"
    }

    for key, uuid in chars.items():
        try:
            res = subprocess.run(["gatttool", "-b", mac_address, "--char-read", "-u", uuid], capture_output=True, text=True, timeout=4)
            match = re.search(r"Characteristic value/descriptor:\s*(.*)", res.stdout)
            if match:
                ascii_val = hex_to_ascii(match.group(1))
                if ascii_val: gatt_meta[key] = ascii_val
        except: pass

    try:
        res = subprocess.run(["gatttool", "-b", mac_address, "--char-read", "-u", "2a19"], capture_output=True, text=True, timeout=4)
        match = re.search(r"Characteristic value/descriptor:\s*([0-9a-fA-F]{2})", res.stdout)
        if match:
            gatt_meta["battery_level"] = f"{int(match.group(1), 16)}%"
    except: pass

    return gatt_meta

def parse_lmp_features(mac_address):
    """
    Extracts the full 8-byte LMP Features (Page 0) bitmap via `hcitool -i hci0 info <mac>`
    and decodes every named bit per Bluetooth Core Spec Vol 2, Part C, 3.3 (see lmp_features.py).
    Returns None (never raises) when the device doesn't expose this data - e.g. BLE-only
    peripherals that never negotiate a BR/EDR Features page.
    """
    log("Extracting full LMP Features bitmap (Vol 2, Part C, 3.3)...")
    try:
        result = subprocess.run(["hcitool", "-i", "hci0", "info", mac_address], capture_output=True, text=True, timeout=10)
        output = result.stdout
        match = re.search(r"Features(?: page 0)?:\s*((?:0x[0-9a-fA-F]{1,2}\s*){8})", output)
        if not match:
            return None
        hex_bytes = match.group(1).split()
        byte_values = [int(b, 16) for b in hex_bytes]
        raw_str = ":".join(f"{b:02x}" for b in byte_values)
        return {"lmp_features_raw": raw_str, "lmp_features": decode_features_bitmap(byte_values)}
    except Exception as e:
        log(f"  -> LMP Features extraction failed: {e}")
        return None

def _device_dbus_path(mac_address):
    return "/org/bluez/hci0/dev_" + mac_address.replace(":", "_")

def _find_gatt_characteristic_path(bus, mac_address, uuid_prefix):
    """Walks BlueZ's D-Bus ObjectManager tree for this device looking for a
    GattCharacteristic1 object whose UUID starts with uuid_prefix (e.g.
    "00002a04"). Returns None if the device has no such characteristic exposed
    - which requires the device to already be Connected with GATT services
    resolved; this function does not itself attempt to connect."""
    mac_dbus = mac_address.replace(":", "_")
    obj_manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
    objects = obj_manager.GetManagedObjects()
    for path, interfaces in objects.items():
        if mac_dbus not in path:
            continue
        char_props = interfaces.get("org.bluez.GattCharacteristic1")
        if char_props and str(char_props.get("UUID", "")).startswith(uuid_prefix):
            return path
    return None

def query_gatt_appearance(mac_address):
    """
    BLE-side signal: Generic Access Service (0x1800) -> Appearance characteristic
    (0x2A01), resolved against appearance_values.py (Bluetooth SIG Assigned
    Numbers). Read via BlueZ's own `org.bluez.Device1.Appearance` D-Bus property
    rather than a live GATT characteristic fetch - two reasons, found empirically
    during this study:

    1. `gatttool` (the original implementation) returns "Connection refused" for
       EVERY device on a modern BlueZ system, not just ones lacking the
       characteristic - gatttool opens its own raw L2CAP connection outside
       bluetoothd's management, and current bluetoothd versions refuse to share
       the ACL link with a second process. This reproduced on both a Classic-
       connected device (AirPods) and a pure-BLE device (a Logitech mouse), and
       persisted under sudo, ruling out both "Classic blocks BLE" and
       permissions as the cause - gatttool itself is simply not viable on this
       stack, consistent with it being deprecated upstream.
    2. Separately, BlueZ does not always expose Generic Access as a discoverable
       GattService1 object even when a device supports it (confirmed on that
       same mouse: 0x1800 appears in its advertised UUIDs list but was absent
       from its live GATT object tree). BlueZ instead resolves Appearance itself
       (from GAP advertising data and/or its own internal GATT read at pairing
       time) and republishes it directly as a Device1 property - reading that
       cached property is both simpler and more reliable than re-deriving it.

    Returns (value, failure_reason): value is None if the property isn't
    present (e.g. a device BlueZ never resolved an Appearance for), in which
    case failure_reason carries the raw D-Bus exception message (None on
    success) - callers that don't care why (the served app) can discard it;
    research/availability_audit.py's failure taxonomy is why it exists.
    """
    log("Reading GATT Appearance (0x2A01) via BlueZ Device1.Appearance...")
    try:
        bus = dbus.SystemBus()
        props = dbus.Interface(bus.get_object("org.bluez", _device_dbus_path(mac_address)), "org.freedesktop.DBus.Properties")
        raw_value = int(props.Get("org.bluez.Device1", "Appearance"))
        return {"gatt_appearance_raw": f"0x{raw_value:04x}", "gatt_appearance_category": resolve_appearance(raw_value)}, None
    except Exception as e:
        log(f"  -> GATT Appearance read failed: {e}")
        return None, str(e)

def query_gatt_preferred_conn_params(mac_address):
    """
    BLE-side signal: Generic Access Service (0x1800) -> Preferred Connection
    Parameters characteristic (0x2A04). 8-byte little-endian struct of 4 uint16
    fields: min/max connection interval (units of 1.25ms per the spec), peripheral
    latency (unitless - count of connection events the peripheral may skip), and
    supervision timeout multiplier (units of 10ms).

    Unlike Appearance, BlueZ does not republish this one as a Device1 property, so
    this does a real characteristic read via D-Bus GattCharacteristic1.ReadValue()
    - replacing the original gatttool-based implementation for the same
    "gatttool is refused by bluetoothd on this stack" reason documented in
    query_gatt_appearance(). This requires the device to already be Connected
    with GATT services resolved (so its GATT tree is enumerable); it does not
    attempt to connect itself, so it returns a None value for a device that
    isn't already connected rather than forcing a new connection as a side
    effect here.

    Returns (value, failure_reason) - see query_gatt_appearance() above for
    what failure_reason is for.
    """
    log("Reading GATT Preferred Connection Parameters (0x2A04) via D-Bus GattCharacteristic1...")
    try:
        bus = dbus.SystemBus()
        char_path = _find_gatt_characteristic_path(bus, mac_address, "00002a04")
        if not char_path:
            return None, "characteristic 00002a04 not found in GATT tree (not resolved / not present)"
        char_iface = dbus.Interface(bus.get_object("org.bluez", char_path), "org.bluez.GattCharacteristic1")
        b = [int(x) for x in char_iface.ReadValue({})]
        if len(b) < 8:
            return None, f"ReadValue returned {len(b)} bytes, expected 8"
        min_interval_raw = b[0] | (b[1] << 8)
        max_interval_raw = b[2] | (b[3] << 8)
        peripheral_latency = b[4] | (b[5] << 8)
        timeout_mult_raw = b[6] | (b[7] << 8)
        return {
            "preferred_conn_interval_min_ms": round(min_interval_raw * 1.25, 2),
            "preferred_conn_interval_max_ms": round(max_interval_raw * 1.25, 2),
            "preferred_slave_latency": peripheral_latency,
            "preferred_supervision_timeout_ms": timeout_mult_raw * 10,
        }, None
    except Exception as e:
        log(f"  -> GATT Preferred Connection Parameters read failed: {e}")
        return None, str(e)

def extract_sdp_hints(text):
    """
    Best-effort keyword/regex scan over a raw SDP Service Name/Description string for
    embedded vendor names or version-looking substrings (e.g. "v1.2.3"). Shallow
    pattern matching meant to flag text worth a human's attention, not a vendor
    database lookup.
    """
    if not text:
        return []
    hints = []
    known_brand_keywords = ["apple", "samsung", "sony", "bose", "jbl", "microsoft", "google",
                             "intel", "realtek", "broadcom", "qualcomm", "xiaomi", "huawei",
                             "logitech", "garmin", "fitbit", "amazon"]
    text_lower = text.lower()
    for brand in known_brand_keywords:
        if brand in text_lower:
            hints.append(f"vendor_keyword:{brand}")

    for v in re.findall(r"\bv?\d+\.\d+(?:\.\d+)?\b", text):
        hints.append(f"version_pattern:{v}")

    return hints

def _hex_bytes_to_ascii(hex_str):
    """Decodes a space-separated hex byte string (as printed by `sdptool --tree`'s
    `Data : xx xx xx ...` lines) to ASCII text, truncated at the first NUL byte
    (SDP text attributes are conventionally NUL-terminated)."""
    try:
        raw = bytes.fromhex(hex_str.replace(" ", ""))
        text = raw.split(b"\x00")[0].decode("ascii", errors="ignore").strip()
        return text or None
    except (ValueError, UnicodeDecodeError):
        return None

def get_sdp_full_service_details(mac_address):
    """
    Classic BR/EDR-side signal. Runs `sdptool browse --tree <mac>` (the full attribute
    tree, unlike the summarized `sdptool browse` that get_sdp_services already uses)
    and parses, per service record: the LanguageBaseAttributeIDList (SDP attribute
    0x0006, printed as `Base Offset (Integer) : 0xNNN`) plus the Service Name /
    Service Description attributes that live at base_offset+0x0 / base_offset+0x1.
    Unlike the plain `sdptool browse` output get_sdp_services() parses, `--tree` mode
    does NOT resolve these to human-readable "Service Name: ..." text - it prints the
    raw attribute ID and a space-separated hex byte dump (`Attribute Identifier :
    0x100` / `Data : 47 41 54 54 00`), which this function hex-decodes itself (see
    _hex_bytes_to_ascii). Each record is parsed independently and defensively
    (try/except per record) so one malformed record can't drop the rest of the scan.

    Returns (records, failure_reason): records is a list of dicts
    {"service_name_raw", "service_description_raw", "language_base_offset",
    "sdp_extracted_hints"}, always present (possibly empty - a device can
    legitimately expose zero SDP services, which is not a failure).
    failure_reason is None unless sdptool couldn't reach the device at all
    (nonzero exit / stderr text with no output), in which case it carries the
    raw stderr - sdptool maps distinct HCI/connection outcomes (page timeout,
    ACL refusal, no route) to distinct, recognizable text here, which is what
    research/availability_audit.py's failure taxonomy classifies. A
    per-record parse failure below does not set it.
    """
    log("Running full SDP attribute tree parse (sdptool browse --tree)...")
    records = []
    try:
        result = subprocess.run(["sdptool", "browse", "--tree", mac_address], capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        log("  -> Full SDP tree extraction timed out (15s)")
        return records, "subprocess timeout after 15s (no response from sdptool)"
    except Exception as e:
        log(f"  -> Full SDP tree extraction failed: {e}")
        return records, str(e)

    output = result.stdout
    if not output.strip():
        failure_reason = None
        if result.returncode != 0 or result.stderr.strip():
            failure_reason = result.stderr.strip() or f"sdptool exited {result.returncode} with no output"
            log(f"  -> Full SDP tree extraction failed: {failure_reason}")
        return records, failure_reason

    # Every record starts with its mandatory ServiceRecordHandle attribute
    # (0x0) - this is the only reliable boundary. Blank lines are NOT reliable:
    # sdptool sometimes prints stray lines (e.g. "Failed to connect to SDP
    # server...", when one of several per-service SDP queries times out mid-scan
    # while others succeed) directly between two records with no blank line, and
    # such a stray line must not cause a record to be dropped or merged with its
    # neighbor - it simply won't match any of the patterns below and is ignored.
    blocks = re.split(r"(?=Attribute Identifier\s*:\s*0x0\s*-\s*ServiceRecordHandle)", output)
    for block in blocks:
        if not block.strip():
            continue
        try:
            record = {"service_name_raw": None, "service_description_raw": None, "language_base_offset": None, "sdp_extracted_hints": []}

            base_match = re.search(r"Base Offset \(Integer\)\s*:\s*0x([0-9a-fA-F]+)", block)
            if not base_match:
                continue
            base_offset = int(base_match.group(1), 16)
            record["language_base_offset"] = f"0x{base_offset:x}"

            # Service Name lives at base_offset+0x0, Service Description at
            # base_offset+0x1 (SDP spec) - neither is guaranteed to be present;
            # a record may carry only one, or neither.
            name_attr = f"0x{base_offset:x}"
            desc_attr = f"0x{base_offset + 1:x}"

            name_match = re.search(
                rf"Attribute Identifier\s*:\s*{re.escape(name_attr)}(?!\w)\s*\n\s*Data\s*:\s*([0-9a-fA-F ]+)", block)
            if name_match:
                record["service_name_raw"] = _hex_bytes_to_ascii(name_match.group(1))

            desc_match = re.search(
                rf"Attribute Identifier\s*:\s*{re.escape(desc_attr)}(?!\w)\s*\n\s*Data\s*:\s*([0-9a-fA-F ]+)", block)
            if desc_match:
                record["service_description_raw"] = _hex_bytes_to_ascii(desc_match.group(1))

            combined_text = " ".join(filter(None, [record["service_name_raw"], record["service_description_raw"]]))
            record["sdp_extracted_hints"] = extract_sdp_hints(combined_text)

            if record["service_name_raw"] or record["service_description_raw"]:
                records.append(record)
        except Exception as e:
            log(f"  -> Skipping malformed SDP record: {e}")
            continue
    return records, None

class _GracefulStop(BaseException):
    """Raised by the SIGTERM handler so a running behavioral_scan() loop can exit
    its while-loop and still fall through to summarize/emit whatever samples it
    already has, instead of being killed mid-scan with no output at all.

    Subclasses BaseException (not Exception) - same reasoning as KeyboardInterrupt -
    specifically so it is NOT swallowed by the narrow `except Exception: pass` blocks
    used throughout this file's individual hcitool/l2ping/gatttool calls. If this were
    a plain Exception, a SIGTERM arriving mid-subprocess-call would be silently
    caught by whichever call happened to be in flight and the scan would just
    continue as if nothing happened, defeating graceful cancellation entirely.
    """
    pass

def _install_sigterm_handler():
    def _handler(signum, frame):
        raise _GracefulStop()
    signal.signal(signal.SIGTERM, _handler)

class _BleAdvertisingListener:
    """
    Passive BLE advertising interval capture, for the Layer 3 behavioral scan.
    Backed by `hcitool lescan --duplicates`, which reports every advertising packet
    seen (not just first-discovery) but does NOT print a per-packet timestamp column
    itself - so we timestamp each stdout line the instant Python's read loop receives
    it. That's a proxy for true RX time (a few ms of pipe/scheduling jitter), which is
    negligible against real advertising intervals (typically tens to thousands of ms).
    Runs its own background thread so the main behavioral_scan loop (RSSI/RTT polling)
    isn't blocked waiting on hcitool's line-buffered output.
    """
    def __init__(self, mac_address):
        self.mac_address = mac_address.upper()
        self._proc = None
        self._thread = None
        self._events = queue.Queue()
        self._last_seen = None
        self._stop = threading.Event()

    def start(self):
        try:
            self._proc = subprocess.Popen(
                ["hcitool", "lescan", "--duplicates"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
        except Exception:
            self._proc = None
            return
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        if not self._proc or not self._proc.stdout:
            return
        try:
            for line in self._proc.stdout:
                if self._stop.is_set():
                    break
                if self.mac_address in line.upper():
                    now = time.time()
                    if self._last_seen is not None:
                        interval_ms = round((now - self._last_seen) * 1000, 1)
                        self._events.put((now, interval_ms))
                    self._last_seen = now
        except Exception:
            pass

    def poll(self):
        """Drains and returns every (timestamp, interval_ms) pair queued since the
        last poll() call - non-blocking, safe to call from the main scan loop."""
        gaps = []
        while True:
            try:
                gaps.append(self._events.get_nowait())
            except queue.Empty:
                break
        return gaps

    def stop(self):
        self._stop.set()
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                try: self._proc.kill()
                except Exception: pass

def summarize_behavioral_data(samples, advertising_gaps_ms=None):
    """
    Statistical summary of a behavioral_scan() time series.
    samples: list of {"t", "rssi", "rtt_ms"} dicts (either value may be None for a
    missed sample - a single dropped hcitool/l2ping call doesn't invalidate the rest).
    advertising_gaps_ms: list of consecutive-BLE-advertising-packet interval_ms values
    (only populated for BLE devices - see _BleAdvertisingListener). None for Classic.

    "interval_shift_detected" splits the advertising gap list at its midpoint and
    compares the first-half vs second-half mean interval; a >=30% relative change is
    flagged. This threshold is a placeholder heuristic (not ground-truth calibrated)
    meant to catch a device switching advertising modes mid-scan (e.g. fast/active ->
    slow/power-saving) - treat the flag as "worth a human look", not a confirmed fact.
    """
    def _stats(values):
        vals = [v for v in values if v is not None]
        if not vals:
            return {"mean": None, "stdev": None, "min": None, "max": None, "sample_count": 0}
        return {
            "mean": round(statistics.mean(vals), 2),
            "stdev": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "sample_count": len(vals),
        }

    rssi_stats = _stats([s.get("rssi") for s in samples])
    rtt_stats = _stats([s.get("rtt_ms") for s in samples])

    advertising_gaps_ms = advertising_gaps_ms or []
    adv_stats = _stats(advertising_gaps_ms)
    adv_stats["interval_shift_detected"] = False
    adv_stats["shift_detail"] = None
    if len(advertising_gaps_ms) >= 6:
        mid = len(advertising_gaps_ms) // 2
        mean1 = statistics.mean(advertising_gaps_ms[:mid])
        mean2 = statistics.mean(advertising_gaps_ms[mid:])
        if mean1 > 0:
            relative_change = abs(mean2 - mean1) / mean1
            if relative_change >= 0.3:
                adv_stats["interval_shift_detected"] = True
                adv_stats["shift_detail"] = f"First-half mean {round(mean1, 1)}ms -> second-half mean {round(mean2, 1)}ms ({round(relative_change * 100)}% change)"

    return {
        "duration_covered_seconds": samples[-1]["t"] if samples else 0,
        "sample_count": len(samples),
        "rssi": rssi_stats,
        "rtt_ms": rtt_stats,
        "advertising_interval_ms": adv_stats,
    }

def behavioral_scan(mac_address, duration_seconds=45, sample_interval_seconds=2, is_ble=False, emit=None):
    """
    Katman 3 "Derin Davranışsal Tarama": observes a device over a time window instead
    of a single instant. Two independent measurement sources run for the whole window:
      - Every sample_interval_seconds: one `hcitool rssi` + one single-packet `l2ping`
        RTT sample (same underlying commands measure_baseband_metrics()/measure_rtt()
        use for a single point-in-time read in the fast-scan flow).
      - If is_ble: a background _BleAdvertisingListener passively captures BLE
        advertising packet arrival gaps for the whole window.

    emit(event_dict) is called for every measurement/interval event as it happens
    (defaults to printing one JSON line per event to stdout - see behavioral_main()),
    and once more at the end with a "complete" event carrying summarize_behavioral_data()'s
    output. That per-event streaming is what lets the Express SSE endpoint relay each
    event to the browser live instead of buffering the whole 45s scan.

    Exits its sampling loop early (without losing already-collected data) on a
    _GracefulStop (SIGTERM, e.g. the HTTP client disconnected - see
    _install_sigterm_handler) as well as on a plain KeyboardInterrupt - either way the
    summary/"complete" event still gets computed and emitted from whatever was
    gathered before the interruption, per the "don't silently discard a cancelled
    scan" requirement.

    Returns (samples, summary) so non-streaming callers (e.g. tests) can use this
    synchronously without needing an emit callback.
    """
    if emit is None:
        emit = lambda event: print(json.dumps(event), flush=True)

    samples = []
    advertising_gaps_ms = []
    start_time = time.time()

    ble_listener = None
    if is_ble:
        ble_listener = _BleAdvertisingListener(mac_address)
        ble_listener.start()

    # `hcitool rssi` only returns a value while an ACL link to the device is open -
    # confirmed on real hardware, where without this the entire sampling loop below
    # returned "Not connected." on every single poll. Nothing else in this loop opens
    # or holds that link, so mirror the pattern measure_baseband_metrics() already uses
    # for its single-shot RSSI read: spawn a background `sdptool browse` as a keep-alive
    # "anchor" (BlueZ won't tear down the ACL link while it's mid-browse) for the whole
    # scan window, and issue one `hcitool cc` up front if nothing already has the device
    # connected.
    already_connected = False
    try:
        con_out = subprocess.run(["hcitool", "con"], capture_output=True, text=True, timeout=2).stdout
        already_connected = mac_address.upper() in con_out.upper()
    except Exception:
        pass
    anchor_proc = subprocess.Popen(["sdptool", "browse", mac_address], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not already_connected:
        try:
            subprocess.run(["hcitool", "cc", mac_address], capture_output=True, timeout=3)
        except Exception:
            pass
    time.sleep(1.5)  # let the connection/anchor settle before the first poll

    try:
        while (time.time() - start_time) < duration_seconds:
            elapsed = time.time() - start_time
            sample = {"t": round(elapsed, 2), "rssi": None, "rtt_ms": None}

            try:
                r_rssi = subprocess.run(["hcitool", "rssi", mac_address], capture_output=True, text=True, timeout=2)
                m = re.search(r"RSSI return value:\s*(-?\d+)", r_rssi.stdout)
                if m: sample["rssi"] = -60 + int(m.group(1))
            except Exception: pass

            try:
                r_ping = subprocess.run(["l2ping", "-c", "1", mac_address], capture_output=True, text=True, timeout=2)
                m = re.search(r"(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*) ms", r_ping.stdout)
                if m: sample["rtt_ms"] = float(m.group(2))
            except Exception: pass

            samples.append(sample)
            emit({"type": "measurement", **sample})

            if ble_listener:
                for gap_ts, interval_ms in ble_listener.poll():
                    advertising_gaps_ms.append(interval_ms)
                    emit({"type": "advertising_interval", "t": round(gap_ts - start_time, 2), "interval_ms": interval_ms})

            time.sleep(sample_interval_seconds)
    except (_GracefulStop, KeyboardInterrupt):
        pass
    finally:
        if ble_listener:
            for gap_ts, interval_ms in ble_listener.poll():
                advertising_gaps_ms.append(interval_ms)
            ble_listener.stop()
        try:
            anchor_proc.terminate()
            anchor_proc.wait(timeout=2)
        except Exception:
            try: anchor_proc.kill()
            except Exception: pass
        if not already_connected:
            try: subprocess.run(["hcitool", "dc", mac_address], capture_output=True, timeout=1)
            except Exception: pass

    summary = summarize_behavioral_data(samples, advertising_gaps_ms)
    emit({"type": "complete", "summary": summary})
    return samples, summary

def measure_afh_state(mac_address):
    log("Querying Adaptive Frequency Hopping map...")
    afh_data = {"map": "Unknown (Blocked)", "mode": "Unknown"}
    try:
        res = subprocess.run(["hcitool", "afh", mac_address], capture_output=True, text=True, timeout=4)
        map_match = re.search(r"AFH map:\s*(.*)", res.stdout)
        mode_match = re.search(r"AFH mode:\s*(.*)", res.stdout)
        if map_match: afh_data["map"] = map_match.group(1).strip()
        if mode_match: afh_data["mode"] = mode_match.group(1).strip()
    except: pass
    return afh_data

def test_mtu_reliability(mac_address):
    log("Testing large MTU payload fragmentation (600 bytes)...")
    try:
        res = subprocess.run(["l2ping", "-s", "600", "-c", "2", mac_address], capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and "0% loss" in res.stdout:
            return "Pass (Handles Large Fragmentation)"
        elif "loss" in res.stdout:
            return "Fail (Drops/Fragments Payloads)"
        else:
            return "Unknown"
    except:
        return "Fail (Timeout / Connection Dropped)"

def measure_rtt(mac_address):
    log(f"Starting Multi-Ping RTT analysis on {mac_address}...")
    try:
        result = subprocess.run(["l2ping", "-c", "3", mac_address], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            rtt_match = re.search(r"(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*) ms", result.stdout)
            if rtt_match:
                return {"min": float(rtt_match.group(1)), "avg": float(rtt_match.group(2)), "max": float(rtt_match.group(3))}
    except Exception:
        pass
        
    rtt_list = []
    already_connected = False
    try:
        if mac_address.upper() in subprocess.run(["hcitool", "con"], capture_output=True, text=True).stdout.upper():
            already_connected = True
    except: pass
    
    for i in range(3):
        try:
            start = time.time()
            if not already_connected: 
                res = subprocess.run(["hcitool", "cc", mac_address], capture_output=True, timeout=3)
            else:
                res = subprocess.run(["hcitool", "clock", mac_address], capture_output=True, timeout=3)
                
            rtt = (time.time() - start) * 1000
            
            if not already_connected: 
                subprocess.run(["hcitool", "dc", mac_address], capture_output=True, timeout=1)
                
            if res.returncode == 0: 
                rtt_list.append(rtt)
        except Exception: pass
        time.sleep(0.5)
        
    if not rtt_list: return None
    return {"min": round(min(rtt_list), 2), "max": round(max(rtt_list), 2), "avg": round(sum(rtt_list) / len(rtt_list), 2)}

def measure_baseband_metrics(mac_address):
    log(f"Actively querying baseband packet metrics with SDP Anchor...")
    metrics = {"rssi": "N/A", "distance_m": "N/A", "link_quality": "N/A", "tx_power_level": "N/A", "uptime": "Unknown", "security": "Unknown", "link_policy": "Unknown", "supervision_timeout": "Unknown", "clock_offset": "Unknown"}
    
    already_connected = False
    try:
        if mac_address.upper() in subprocess.run(["hcitool", "con"], capture_output=True, text=True).stdout.upper():
            already_connected = True
    except: pass
    
    # 1. Spawn SDP Anchor in background to perfectly prevent ACL link drops (unblockable)
    anchor_proc = subprocess.Popen(["sdptool", "browse", mac_address], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5) # wait for anchor to establish
    
    try:
        if not already_connected: subprocess.run(["hcitool", "cc", mac_address], capture_output=True, timeout=2)
        
        r_rssi = subprocess.run(["hcitool", "rssi", mac_address], capture_output=True, text=True, timeout=3)
        rssi_match = re.search(r"RSSI return value:\s*(-?\d+)", r_rssi.stdout)
        if rssi_match:
            relative_rssi = int(rssi_match.group(1))
            absolute_rssi = -60 + relative_rssi
            metrics["rssi"] = absolute_rssi
            if absolute_rssi > -35: metrics["distance_m"] = "< 1.0 meters (Extremely Close)"
            else:
                import math
                distance = 10 ** ((-55 - absolute_rssi) / 20)
                d_min = max(1, math.floor(distance) - 1)
                d_max = math.ceil(distance) + 1
                if d_min == d_max: d_max += 1
                metrics["distance_m"] = f"Approx. {d_min} - {d_max} meters"

        r_lq = subprocess.run(["hcitool", "lq", mac_address], capture_output=True, text=True, timeout=3)
        lq_match = re.search(r"Link quality:\s*(\d+)", r_lq.stdout)
        if lq_match: metrics["link_quality"] = int(lq_match.group(1))
        
        r_tpl = subprocess.run(["hcitool", "tpl", mac_address], capture_output=True, text=True, timeout=3)
        tpl_match = re.search(r"Current transmit power level:\s*(-?\d+)", r_tpl.stdout)
        if tpl_match: metrics["tx_power_level"] = int(tpl_match.group(1))
            
        r_clk = subprocess.run(["hcitool", "clock", mac_address], capture_output=True, text=True, timeout=3)
        clk_match = re.search(r"Clock:\s*0x([0-9a-fA-F]+)", r_clk.stdout)
        if clk_match:
            ticks = int(clk_match.group(1), 16)
            uptime_hrs = ((ticks * 0.3125) / 1000) / 3600
            metrics["uptime"] = f"{uptime_hrs:.2f} Hours"
            
        r_auth = subprocess.run(["hcitool", "auth", mac_address], capture_output=True, text=True, timeout=3)
        if "Authentication requested" in r_auth.stdout:
            metrics["security"] = "Mandates PIN/Link Key (Secure)"
        else:
            metrics["security"] = "Legacy / Just-Works (Unsecured)"
            
        r_lp = subprocess.run(["hcitool", "lp", mac_address], capture_output=True, text=True, timeout=3)
        lp_match = re.search(r"Link policy:\s*(.*)", r_lp.stdout)
        if lp_match: metrics["link_policy"] = lp_match.group(1).strip()
        
        r_lst = subprocess.run(["hcitool", "lst", mac_address], capture_output=True, text=True, timeout=3)
        lst_match = re.search(r"Link supervision timeout:\s*(.*)", r_lst.stdout)
        if lst_match: metrics["supervision_timeout"] = lst_match.group(1).strip()
        
        r_clkoff = subprocess.run(["hcitool", "clkoff", mac_address], capture_output=True, text=True, timeout=3)
        clkoff_match = re.search(r"Clock offset:\s*(.*)", r_clkoff.stdout)
        if clkoff_match: metrics["clock_offset"] = clkoff_match.group(1).strip()
            
        if not already_connected: subprocess.run(["hcitool", "dc", mac_address], capture_output=True, timeout=2)
    except Exception as e: log(f"  -> Baseband extraction failed: {e}")
    finally:
        try: anchor_proc.terminate()
        except: pass
        
    return metrics

def query_dbus_properties(mac_address):
    log("Querying BlueZ DBus & Bluetoothctl for cached attributes...")
    dbus_props = {"battery": "N/A", "class_of_device": "N/A", "modalias": "N/A", "manufacturer_data": "N/A"}
    mac_dbus = mac_address.replace(":", "_")
    obj_path = f"/org/bluez/hci0/dev_{mac_dbus}"
    cmd = ["dbus-send", "--system", "--print-reply", f"--dest=org.bluez", obj_path, "org.freedesktop.DBus.Properties.GetAll", "string:org.bluez.Device1"]
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        out = res.stdout
        if "BatteryPercentage" in out:
            bat_match = re.search(r'string "BatteryPercentage"\s*variant\s*byte\s*(\d+)', out)
            if bat_match: dbus_props["battery"] = f"{bat_match.group(1)}%"
        if "Class" in out:
            class_match = re.search(r'string "Class"\s*variant\s*uint32\s*(\d+)', out)
            if class_match: dbus_props["class_of_device"] = hex(int(class_match.group(1)))
        if "Modalias" in out:
            mod_match = re.search(r'string "Modalias"\s*variant\s*string\s*"([^"]+)"', out)
            if mod_match: dbus_props["modalias"] = mod_match.group(1)
            
        # Parse ManufacturerData from bluetoothctl
        bctl = subprocess.run(["bluetoothctl", "info", mac_address], capture_output=True, text=True, timeout=4)
        mfg_match = re.search(r"ManufacturerData Key:\s*(0x[0-9a-fA-F]+).*?ManufacturerData Value:\n\s*([0-9a-fA-F\s]+)", bctl.stdout, re.DOTALL)
        if mfg_match:
            dbus_props["manufacturer_data"] = f"VendorID: {mfg_match.group(1)} | Payload: {mfg_match.group(2).strip()}"
    except Exception: pass
    return dbus_props

def get_gatt_uuids(mac_address):
    log("Running gatttool to enumerate BLE/GATT UUIDs...")
    uuids = []
    try:
        # Use timeout to prevent hanging on devices that reject GATT
        result = subprocess.run(["gatttool", "-b", mac_address, "--primary"], capture_output=True, text=True, timeout=8)
        output = result.stdout
        for match in re.finditer(r"uuid:\s*([a-fA-F0-9\-]+)", output):
            uuids.append(match.group(1).lower())
    except Exception as e:
        log(f"  -> GATT extraction failed: {e}")
    return list(set(uuids))

def get_device_name(mac_address):
    try:
        result = subprocess.run(["hcitool", "name", mac_address], capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or "Unknown"
    except: return "Unknown"

def run_c_version_finder(mac_address):
    c_data = {"lmp_integer": 0, "flags": {"a2dp": 0, "map": 0, "pbap": 0, "hfp": 0, "opp": 0, "did": 0}, "estimated_android": None, "success": False}
    if not os.path.exists(VERSION_FINDER_PATH): return c_data
    try:
        result = subprocess.run([VERSION_FINDER_PATH, mac_address], capture_output=True, text=True, timeout=15)
        out = result.stdout
        if "LMP Version:" in out:
            c_data["success"] = True
            lmp_match = re.search(r"LMP Version:\s*(\d+)", out)
            if lmp_match: c_data["lmp_integer"] = int(lmp_match.group(1))
            if "Device ID Profile: Present" in out: c_data["flags"]["did"] = 1
            if "A2DP: Y" in out: c_data["flags"]["a2dp"] = 1
            if "MAP: Y" in out: c_data["flags"]["map"] = 1
            if "PBAP: Y" in out: c_data["flags"]["pbap"] = 1
            if "HFP: Y" in out: c_data["flags"]["hfp"] = 1
            if "OPP: Y" in out: c_data["flags"]["opp"] = 1
            est_match = re.search(r"Estimated Android Version:\s*(.*)", out)
            if est_match: c_data["estimated_android"] = est_match.group(1).strip()
    except Exception: pass
    return c_data

def get_hcitool_info(mac_address):
    features = {"lmp_version": "Unknown", "lmp_integer": 0, "lmp_subversion": "Unknown", "manufacturer": "Unknown", "supported_features": "Unknown", "failed": False}
    try:
        result = subprocess.run(["hcitool", "info", mac_address], capture_output=True, text=True, timeout=10)
        output = result.stdout
        if not output.strip() or "Device is not available" in output: features["failed"] = True
        lmp_match = re.search(r"LMP Version:\s*(.*?)\s*\(0x([0-9a-fA-F]+)\)\s*Subversion:\s*0x([0-9a-fA-F]+)", output)
        if lmp_match:
            features["lmp_version"] = f"{lmp_match.group(1)} (0x{lmp_match.group(2)})"
            try: features["lmp_integer"] = int(lmp_match.group(2), 16)
            except: features["lmp_integer"] = 0
            features["lmp_subversion"] = f"0x{lmp_match.group(3)}"
        mfg_match = re.search(r"Manufacturer:\s*(.*)", output)
        if mfg_match: features["manufacturer"] = mfg_match.group(1).strip()
        feat_match = re.search(r"Features page 0:\s*(.*)", output)
        if feat_match: 
            raw_hex = feat_match.group(1).strip()
            features["baseband_features"] = f"{raw_hex} | {decode_baseband_features(raw_hex)}"
    except Exception: features["failed"] = True
    return features

def sdp_flags_from_service_names(service_names, flags=None):
    """
    Maps SDP "Service Name:" strings onto the profile flags the scoring engine
    consumes. Split out of get_sdp_services() so the offline replay tool
    (research/replay_predictions.py) can rebuild flags from an archived scan
    using this exact rule set instead of a hand-copied duplicate that would
    drift out of sync with the live scanner.
    """
    if flags is None:
        flags = {"a2dp": 0, "map": 0, "pbap": 0, "hfp": 0, "opp": 0, "did": 0,
                 "pan": 0, "hid": 0, "failed": False}
    for name in service_names:
        s_lower = (name or "").lower()
        if "audio" in s_lower or "a2dp" in s_lower: flags["a2dp"] = 1
        if "message" in s_lower or "map" in s_lower: flags["map"] = 1
        if "phonebook" in s_lower or "pbap" in s_lower: flags["pbap"] = 1
        if "hands-free" in s_lower or "hfp" in s_lower: flags["hfp"] = 1
        if "object push" in s_lower or "opp" in s_lower: flags["opp"] = 1
        if "device id" in s_lower or "pnp" in s_lower: flags["did"] = 1
        if "network" in s_lower or "pan" in s_lower or "nap" in s_lower: flags["pan"] = 1
        if "human interface" in s_lower or "hid" in s_lower: flags["hid"] = 1
    return flags


def get_sdp_services(mac_address):
    services = []; protocols = []; handles = []
    flags = {"a2dp": 0, "map": 0, "pbap": 0, "hfp": 0, "opp": 0, "did": 0, "pan": 0, "hid": 0, "failed": False}
    try:
        result = subprocess.run(["sdptool", "browse", mac_address], capture_output=True, text=True, timeout=15)
        output = result.stdout
        if not output.strip() or "Failed to connect" in output: flags["failed"] = True
        current_service = None
        for line in output.split('\n'):
            line_str = line.strip()
            if line_str.startswith("Service Name:"):
                current_service = line.split(":", 1)[1].strip()
                if current_service:
                    services.append(current_service)
                    sdp_flags_from_service_names([current_service], flags)
            elif line_str.startswith("Service RecHandle:"):
                h_match = re.search(r"0x[0-9a-fA-F]+", line_str)
                if h_match: handles.append(h_match.group(0).lower())
            elif line_str.startswith('"L2CAP"') or line_str.startswith('"RFCOMM"') or line_str.startswith('"AVCTP"'):
                protocols.append(line_str.strip('"'))
            elif "Profile Version:" in line_str and current_service:
                ver = line_str.split("0x")[1].strip()
                protocols.append(f"{current_service} (v{ver[0]}.{ver[1:]})")
    except Exception: flags["failed"] = True
    return services, list(set(protocols)), flags, handles

def lookup_oui(mac_address):
    oui = mac_address[:8].upper()
    known_ouis = {
        "D4:F5:47": "Apple, Inc.", "00:1A:7D": "Apple, Inc.", "FC:6E:A3": "Apple, Inc.",
        "34:8A:7B": "Samsung Electronics", "00:1B:DC": "Microsoft Corporation", "A0:59:50": "Intel Corporate", 
        "B8:27:EB": "Raspberry Pi", "24:0A:C4": "Espressif Inc.", "30:AE:A4": "Espressif Inc.",
        "00:12:4B": "Texas Instruments", "E0:E5:CF": "Xiaomi Communications", "A4:C1:38": "Tuya Smart", 
        "00:1A:11": "Google, Inc."
    }
    if oui in known_ouis: return known_ouis[oui]
    try:
        req = urllib.request.Request(f"https://api.macvendors.com/{mac_address}", headers={'User-Agent': 'Mozilla/5.0'})
        return urllib.request.urlopen(req, timeout=3).read().decode('utf-8')
    except: return "Unknown"

def decode_modalias(modalias_str): # bunu sonradan ekledin. aniketin kodunda yoktu.
    if not modalias_str or modalias_str == "N/A": return None
    match = re.match(r"(bluetooth|usb):v([0-9A-Fa-f]{4})p([0-9A-Fa-f]{4})d([0-9A-Fa-f]{4})", modalias_str)
    if not match: return None
    return {
        "source": match.group(1),
        "vendor_id": match.group(2).upper(),
        "product_id": match.group(3).upper(),
        "version": match.group(4).upper()
    }

def enrich_modalias_with_chipset(device_id_info):
    """
    Looks up the (source, vendor_id, product_id) triplet from decode_modalias() against
    CHIPSET_DATABASE (chipset_database.py). Always preserves the raw vendor_id/product_id
    even on a miss, so no data is lost for future database expansion - only the resolved
    fields (chipset_model, release year, OS hint) are left null when unmatched.
    """
    if not device_id_info:
        return device_id_info
    match = lookup_chipset(device_id_info["source"], device_id_info["vendor_id"], device_id_info["product_id"])
    if device_id_info["source"] == "usb":
        # USB-IF vendor IDs and Bluetooth SIG Company IDs are different numbering spaces -
        # vendor_name (lookup_company_id) is SIG-only, so resolve USB vendor names separately.
        resolved = resolve_usb_vendor_name(device_id_info["vendor_id"])
        device_id_info["chipset_vendor"] = resolved or f"Unknown USB Vendor (0x{device_id_info['vendor_id']})"
    else:
        device_id_info["chipset_vendor"] = device_id_info.get("vendor_name")
    device_id_info["chipset_product_id"] = device_id_info["product_id"]
    device_id_info["chipset_model"] = match["chipset"] if match else None
    device_id_info["estimated_chipset_release_year"] = match["release_year"] if match else None
    device_id_info["estimated_min_os_hint"] = match["min_os_hint"] if match else None
    return device_id_info

# Plausible calendar span for each OS bucket predict_device_core can output, as
# (earliest, latest) release years. "earliest" is when that OS version shipped;
# "latest" is the last year a device could plausibly have shipped still running
# it - the following version's release year plus one year of grace, since
# vendors keep shipping the previous release for a while. None means unbounded:
# an open-ended bucket ("iOS 17+", "Windows 11", the newest Android band) has no
# upper edge, so it can never be contradicted by a chipset date.
#
# Only the "latest" edge is used by the chronology check below; "earliest" is
# retained because it documents where each bucket starts and is what makes the
# asymmetry legible. Years are approximate and the table is deliberately
# generous - see check_chipset_os_consistency for why.
OS_VERSION_PLAUSIBLE_YEARS = {
    "Windows 11": (2021, None), "Windows 10": (2015, 2022),
    "Windows 8.1 / 10": (2013, 2022), "Windows 7 or older": (2009, 2010),
    "iOS 17+": (2023, None), "iOS 16+": (2022, None), "iOS 15+": (2021, None),
    "iOS 14 or older": (2018, 2021),
    "macOS 14+": (2023, None), "macOS 13+": (2022, None), "macOS 12+": (2021, None),
    "macOS 11 or older": (2018, 2021),
    "iPadOS 17+": (2023, None), "iPadOS 16+": (2022, None), "iPadOS 15+": (2021, None),
    "iPadOS 14 or older": (2018, 2021),
    "Android 16 (Baklava)": (2025, None),
    "Android 15 (Vanilla Ice Cream)": (2024, 2026),
    "Android 14 (Upside Down Cake)": (2023, 2025),
    "Android 13 (Tiramisu)": (2022, 2024),
    "Android 12 (Snow Cone)": (2021, 2023),
    "Android 11 (Red Velvet Cake)": (2020, 2022),
    "Android 10 (Q)": (2019, 2021),
    "Android 9.0 (Pie)": (2018, 2020),
    "Android 8.0/8.1 (Oreo)": (2017, 2019),
    "Android 7.0 or older": (2016, 2018),
}


def check_chipset_os_consistency(predicted_version_str, chipset_release_year):
    """
    Soft, one-sided chronology check. It does NOT change the prediction itself -
    it only returns a flag for predict_device() to lower the reported confidence.

    The comparison has to be against the bucket's LATEST plausible year, not its
    earliest. Both other directions are uninformative:

      - a chipset OLDER than the predicted OS is no contradiction at all, since
        old silicon happily runs new software (a 2016 chipset in a phone running
        Android 14 is an ordinary, long-supported device);
      - a chipset merely newer than the bucket's EARLIEST year holds for nearly
        every device ever scanned, because hardware almost always postdates the
        first release of the OS it runs. Flagging that would fire constantly and
        mean nothing.

    What IS a genuine contradiction is a chipset released after the last year the
    predicted OS version could plausibly still have been shipping: the device
    then contains a component newer than the software one signal claims it runs.
    Open-ended buckets ("iOS 17+", the newest Android band) have no upper edge
    and so are never flagged.

    This remains sensitive to false positives wherever our chipset release dates
    are uncertain, which is why the upper edge carries a year of grace and why
    the result only softens confidence.
    """
    if not predicted_version_str or not chipset_release_year:
        return []
    for label, (_earliest, latest) in OS_VERSION_PLAUSIBLE_YEARS.items():
        if label in predicted_version_str:
            if latest is not None and chipset_release_year > latest:
                return ["chipset_newer_than_predicted_os"]
            return []
    return []

def lookup_company_id(vendor_id_hex):
    """
    Resolves a "bluetooth:vXXXX..." Modalias vendor ID against the full Bluetooth
    SIG assigned Company Identifiers table (bluetooth_company_ids.py) rather than
    a small hand-picked subset - the earlier ~7-entry version left common vendors
    (e.g. Qualcomm, 0x001D) unresolved not because they lacked an assigned ID, but
    because the table was never populated with it.
    """
    if not vendor_id_hex: return "Unknown"
    name = lookup_bluetooth_company_id(vendor_id_hex)
    return name if name else f"Unknown (Company ID: 0x{vendor_id_hex})"

def extract_permissions(sdp_flags, dev_name=""):
    perms = []
    name_lower = dev_name.lower()
    audio_keywords = ["airdopes", "airpods", "earbuds", "buds", "headphones", "headset", "speaker", "audio", "jbl", "bose", "sony", "boat", "sennheiser"]
    is_audio_device = any(x in name_lower for x in audio_keywords)
    
    has_audio = sdp_flags["a2dp"] or sdp_flags["hfp"] or is_audio_device
    
    perms.append(f"Audio & Microphone Access: {'GRANTED' if has_audio else 'DENIED'}")
    perms.append(f"Contacts & Call History Access: {'GRANTED' if sdp_flags['pbap'] else 'DENIED'}")
    perms.append(f"SMS/Text Messages Access: {'GRANTED' if sdp_flags['map'] else 'DENIED'}")
    perms.append(f"File Transfer & Media Access: {'GRANTED' if sdp_flags['opp'] else 'DENIED'}")
    perms.append(f"Keyboard/Mouse Input Control: {'GRANTED' if sdp_flags['hid'] else 'DENIED'}")
    perms.append(f"Internet Tethering/Network Access: {'GRANTED' if sdp_flags['pan'] else 'DENIED'}")
    
    if sdp_flags["failed"] and not is_audio_device:
        perms.append("WARNING: SDP Connection Blocked - Permissions Inferred")
        
    return perms

def infer_deep_metadata(lmp_int, vendor, rtt, sdp_handles, gatt_uuids, protocols):
    meta = {}
    if rtt and rtt.get('avg'):
        avg_ping = rtt['avg']
        if avg_ping > 80: meta["power_state"] = f"Sniff/Sleep Mode Active (Battery Saving) - Latency: {avg_ping}ms"
        elif avg_ping < 20: meta["power_state"] = f"Active Polling Mode (High Performance) - Latency: {avg_ping}ms"
        else: meta["power_state"] = f"Standard Mode - Latency: {avg_ping}ms"
    else: meta["power_state"] = "Unknown (Ping Failed)"

    lmp_map = {
        13: "Bluetooth 5.4 (Released 2023)", 12: "Bluetooth 5.3 (Released 2021)",
        11: "Bluetooth 5.2 (Released 2020)", 10: "Bluetooth 5.1 (Released 2019)",
        9: "Bluetooth 5.0 (Released 2016)", 8: "Bluetooth 4.2 (Released 2014)"
    }
    meta["hardware_age"] = lmp_map.get(lmp_int, f"Legacy / Unknown (LMP {lmp_int})") if lmp_int > 0 else "Unknown"
    
    v = vendor.lower()
    if any(x in v for x in ["espressif", "texas", "nordic", "tuya"]): meta["market"] = "Industrial / Embedded IoT"
    elif "apple" in v: meta["market"] = "Premium Consumer Tech (Apple Ecosystem)"
    elif any(x in v for x in ["samsung", "xiaomi", "google"]): meta["market"] = "Consumer Electronics / Mobile"
    elif any(x in v for x in ["intel", "microsoft", "cloud network"]): meta["market"] = "PC / Compute Hardware"
    else: meta["market"] = "Generic / Unknown"
    
    insights = []
    if not gatt_uuids:
        # An empty gatt_uuids list means get_gatt_uuids() got nothing back -
        # timeout, connection refused, or a real absence of GATT services are
        # all indistinguishable here (see its own log()'d exception, which
        # this function never receives). "Classic Mode Enforced" used to be
        # asserted here regardless of which of those happened - a specific
        # claim about the device's own policy that this data cannot support,
        # and one that could directly contradict Nearby Devices' own
        # device_type="ble" classification for the same device.
        insights.append("No GATT UUIDs enumerated (enumeration failed, timed out, or "
                         "device exposes none - not evidence the device itself blocks BLE)")
    else:
        insights.append(f"BLE Active ({len(gatt_uuids)} Proprietary UUIDs Exposed)")

    h_str = " ".join(sdp_handles).lower()
    if "0x1002d" in h_str or "0x1002e" in h_str:
        insights.append("Windows SDP Offset (0x1002X Block Detected)")
    elif "0x10001" in h_str and "0x10002" in h_str:
        insights.append("Unix/BlueZ SDP Offset (0x10001 Block Detected)")
    elif sdp_handles:
        insights.append("Randomized/Generic SDP Sequencing")

    p_str = " ".join(protocols).upper()
    if "AVCTP" in p_str and "RFCOMM" in p_str and "L2CAP" in p_str:
        insights.append("Standard Media & Serial Transport Profile")

    meta["protocol_insights"] = insights
    
    return meta

def decode_cod_major_class(cod_hex):
    if not cod_hex or cod_hex == "N/A": return None
    try:
        cod_int = int(cod_hex, 16)
        return (cod_int >> 8) & 0x1F
    except: return None

# Surface-level device-category keyword scan over the advertised device name, mapped
# onto the same CoD major-class integers as decode_cod_major_class()/
# appearance_category_to_cod_major() (2=Phone, 1=Computer, 7=Wearable, 4=Audio,
# 5=Peripheral). Deliberately separate from predict_device_core's own name-keyword
# checks (e.g. the Apple-audio branch) - those feed device_type directly, so reusing
# them here for a signal meant to cross-check device_type would be circular. This one
# exists only for build_evidence_chain's name-vs-Appearance independence check
# (Section 4.8) and is never consulted by predict_device_core itself.
# Name keywords are split into two tiers, and the split is load-bearing rather
# than cosmetic.
#
# The single-table version of this was first-match-wins over dict order, which
# silently mis-categorized any accessory carrying a brand-family name: "Galaxy
# Buds2" matched "galaxy" (Phone) before "buds" (Audio) and resolved to Phone.
# The evidence chain surfaced this by disagreeing with Class-of-Device on four
# archived scans of one such device - which is what the mechanism is for, but
# the underlying derivation was still wrong and is fixed here.
#
# Longest-match does not fix it ("galaxy" is longer than "buds"). The real
# distinction is that brand-family names appear on a vendor's phones AND on its
# earbuds, watches and tablets, whereas a product-type word names the thing
# itself. Product type is therefore strictly more specific and is resolved
# first; brand family is consulted only when nothing more specific matched.
NAME_CATEGORY_KEYWORDS_SPECIFIC = {
    2: ["iphone", "phone"],
    # "ipad"/"tablet" resolve to Computer (major class 1) on empirical grounds,
    # not by assumption: a paired iPad in our own device set reports
    # CoD 0x006a0110, whose major class is 1. Guessing here would have been
    # worse than omitting the keyword, since a wrong mapping manufactures
    # conflicts in the CoD-vs-name pair rather than revealing them.
    1: ["macbook", "imac", "mac mini", "mac studio", "mac pro", "laptop",
        "notebook", "pc", "ipad", "tablet"],
    7: ["watch", "band", "fit"],
    4: ["airpods", "airdopes", "buds", "headphone", "headset", "earphone",
        "earbud", "speaker", "soundbar"],
    5: ["mouse", "keyboard", "trackpad", "gamepad", "joystick", "stylus", "pen"],
}

# Ambiguous on their own: these name a vendor's product family, not a device
# category, and the same word ships on phones and accessories alike.
NAME_CATEGORY_KEYWORDS_BRAND_FAMILY = {
    2: ["galaxy", "pixel", "redmi", "oneplus"],
}

# Retained for callers and tests that want the full keyword set in one place.
NAME_CATEGORY_KEYWORDS = NAME_CATEGORY_KEYWORDS_SPECIFIC


def _fold_for_keyword_match(text):
    """
    Case-folds a device name for ASCII keyword matching, decomposing accents
    and dropping combining marks first.

    A plain .lower() is not sufficient and silently lost real signal. Turkish
    dotted capital I (U+0130) lower-cases to "i" PLUS a combining dot above
    (U+0307), so a device advertising as "Irem Ipad" with a Turkish capital
    folded to "i\u0307pad" and never matched the keyword "ipad". The device
    then contributed no name signal at all, which quietly reduced coverage of
    the evidence chain's name-based pairs instead of failing visibly. Device
    names are user-chosen free text and routinely carry non-ASCII characters,
    so folding has to be explicit.
    """
    decomposed = unicodedata.normalize("NFKD", text).casefold()
    return "".join(ch for ch in unicodedata.normalize("NFKD", decomposed)
                   if not unicodedata.combining(ch))


def infer_device_category_from_name(name):
    """
    Maps an advertised device name onto a Class-of-Device major class, or None
    when nothing matches. Deliberately kept separate from predict_device_core's
    own name-based branches so the evidence chain's name signal is derived from
    raw name text only, never from a decision that already used device_type.
    """
    if not name:
        return None
    name_lower = _fold_for_keyword_match(name)
    for table in (NAME_CATEGORY_KEYWORDS_SPECIFIC, NAME_CATEGORY_KEYWORDS_BRAND_FAMILY):
        for major_class, keywords in table.items():
            if any(kw in name_lower for kw in keywords):
                return major_class
    return None

# ---------------------------------------------------------------------------
# Android version scoring tables (Section III, "Scoring model").
#
# Lifted out of predict_device_core so the paper, the unit tests and the code
# read from ONE definition instead of three hand-copied ladders.
#
# Three invariants are asserted by test_android_score_ladder.py:
#   (I1) ANDROID_LMP_BASE is non-decreasing in LMP version. A newer Bluetooth
#        controller must never score *lower* than an older one. (The previous
#        table violated this: LMP 9 scored 85 while LMP 10 scored 68.)
#   (I2) Every band in ANDROID_VERSION_BANDS is reachable by some integer raw
#        score that an actual (base + bonus) combination can produce. The
#        previous ladder compared a rescaled float against thresholds 7.15 and
#        7.2, i.e. raw scores in [75.075, 75.6) - an interval containing no
#        integer, so "Android 12 (Snow Cone)" was unreachable by construction.
#   (I3) The PROVISIONAL evidence layers cannot move the estimate by more
#        than one version band, which is what the paper claims about them.
#        The previous ladder skipped two versions on a single point
#        (75 -> 76 moved Android 11 -> Android 13). The structural DID
#        bonus (+6) is deliberately large and is NOT covered by this.
#
# Thresholds are compared against the INTEGER raw score directly. There is no
# intermediate float rescale: rescaling was what made the bands unreachable,
# and it bought nothing, since every input to the sum is an integer.
ANDROID_SCORE_MAX = 105

# LMP version -> base score. Keys are exact LMP versions; anything above the
# highest key uses the highest key's score (see android_lmp_base).
ANDROID_LMP_BASE = {
    4: 5,    # BT 2.0 + EDR
    5: 10,   # BT 2.1 + EDR
    6: 15,   # BT 3.0 + HS
    7: 25,   # BT 4.0
    8: 48,   # BT 4.1
    9: 68,   # BT 5.0
    10: 78,  # BT 5.1
    11: 85,  # BT 5.2
    12: 88,  # BT 5.3
    13: 98,  # BT 5.4
    14: 105, # BT 5.5 and later
}

# Profile / evidence bonuses added on top of the LMP base. Kept as a table so
# MAX_SINGLE_BONUS and the total bonus ceiling are derived, not hand-counted -
# the previous code's comment claimed a "105 ceiling" while the bonuses could
# actually push the sum to 128.
ANDROID_BONUSES = {
    "a2dp": 2, "hfp": 2, "map": 2, "pbap": 2, "opp": 1,
    "did": 6, "did_modern_lmp": 6,
    "lmp_simultaneous_le_bredr": 1,   # PROVISIONAL, uncalibrated
    "gatt_conn_interval_sub_15ms": 1, # PROVISIONAL, uncalibrated
}
ANDROID_BONUS_TOTAL = sum(ANDROID_BONUSES.values())

# The two uncalibrated evidence layers, kept separate from the structural
# profile bonuses. The paper's claim is specifically about THESE: that a
# provisional, not-yet-ground-truthed signal only nudges the estimate and
# cannot move it by a whole version. Invariant I3 tests exactly that claim, so
# it has to know which bonuses are provisional - the structural DID bonus (+6)
# is deliberately large and IS allowed to cross a band.
PROVISIONAL_BONUSES = ("lmp_simultaneous_le_bredr", "gatt_conn_interval_sub_15ms")
MAX_PROVISIONAL_BONUS = max(ANDROID_BONUSES[k] for k in PROVISIONAL_BONUSES)
PROVISIONAL_BONUS_TOTAL = sum(ANDROID_BONUSES[k] for k in PROVISIONAL_BONUSES)
MAX_SINGLE_BONUS = max(ANDROID_BONUSES.values())

# (inclusive lower bound on the integer raw score, label), highest band first.
ANDROID_VERSION_BANDS = [
    (103, "Android 16 (Baklava)"),
    (97,  "Android 15 (Vanilla Ice Cream)"),
    (87,  "Android 14 (Upside Down Cake)"),
    (79,  "Android 13 (Tiramisu)"),
    (74,  "Android 12 (Snow Cone)"),
    (70,  "Android 11 (Red Velvet Cake)"),
    (42,  "Android 10 (Q)"),
    (37,  "Android 9.0 (Pie)"),
    (32,  "Android 8.0/8.1 (Oreo)"),
]


def android_lmp_base(lmp_int):
    """Base score for an LMP version, saturating at the highest tabulated key."""
    if lmp_int in ANDROID_LMP_BASE:
        return ANDROID_LMP_BASE[lmp_int]
    highest = max(ANDROID_LMP_BASE)
    if lmp_int > highest:
        return ANDROID_LMP_BASE[highest]
    return 0


def android_version_from_score(score):
    """
    Map an integer raw score onto an Android version label. Returns None below
    the lowest band so the caller can pick the right "unknown vs. old" wording.
    """
    for threshold, label in ANDROID_VERSION_BANDS:
        if score >= threshold:
            return label
    return None


def predict_device_core(hw_info, services, sdp_flags, sdp_handles, gatt_uuids, vendor, name, c_data, cod_hex="N/A", deep_gatt=None, lmp_features=None, gatt_appearance=None, gatt_conn_params=None):
    inference = {"device_type": "Unknown", "os": "Unknown", "major_minor_version": "Unknown", "confidence": "Low"}
    services_str = " ".join(services).lower()
    name_lower = name.lower()
    lmp_int = c_data["lmp_integer"] if c_data["success"] else hw_info["lmp_integer"]

    f_pbap = c_data["flags"]["pbap"] or sdp_flags["pbap"]
    f_map  = c_data["flags"]["map"] or sdp_flags["map"]
    is_missing_data = (lmp_int == 0) and not c_data["success"]
    cod_major = decode_cod_major_class(cod_hex)

    # BLE-only devices are frequently missing Class of Device entirely - CoD is a
    # BR/EDR-era inquiry field with no BLE equivalent requirement. GATT Appearance
    # (0x2A01) is the closest BLE-native "device category" signal, so when CoD is
    # absent but Appearance is present, treat Appearance as an equal-priority primary
    # signal by mapping it onto the same major-class taxonomy used throughout this
    # function (see appearance_category_to_cod_major in appearance_values.py).
    if cod_major is None and gatt_appearance and gatt_appearance.get("gatt_appearance_category"):
        cod_major = appearance_category_to_cod_major(gatt_appearance["gatt_appearance_category"])

    # LMP is only the Bluetooth chip/stack version, not the device's own OS/firmware version.
    # When the device exposes the standard GATT Device Information Service, prefer that real
    # firmware/software string over the "(LMP X)" placeholder for categories we can't otherwise
    # version (wearables, audio accessories, unclassified peripherals).
    deep_gatt = deep_gatt or {}
    device_firmware = deep_gatt.get("software_revision") or deep_gatt.get("firmware_revision")

    # 1. Exact Apple Engine (Highest Priority to prevent PBAP false positives)
    is_apple = "apple" in vendor.lower() or "apple" in hw_info["manufacturer"].lower() or "wireless iap" in services_str
    if is_apple:
        apple_audio_keywords = ["airpods", "airdopes", "earbuds", "buds", "headphones", "headset", "beats"]
        # A2DP alone isn't proof of an audio accessory - iPhones/Macs also expose it (as an
        # A2DP *source*, to send audio to speakers). Only trust it when the device doesn't
        # already look like a phone: COD isn't "Phone" and it has no PBAP/MAP (phones only).
        has_a2dp = c_data["flags"]["a2dp"] or sdp_flags["a2dp"]
        looks_like_phone = cod_major == 2 or f_pbap or f_map
        is_apple_audio = (
            cod_major == 4
            or any(x in name_lower for x in apple_audio_keywords)
            or (has_a2dp and not looks_like_phone)
        )

        if is_apple_audio:
            inference["device_type"] = "Audio Peripheral (Apple)"
            inference["os"] = "Embedded Firmware (RTOS)"
            if device_firmware:
                inference["major_minor_version"] = f"Firmware {device_firmware}"
                inference["confidence"] = "High (GATT Device Info)"
            else:
                inference["major_minor_version"] = f"Audio Sink Device (LMP {lmp_int})"
                inference["confidence"] = "High (Name/CoD Heuristic)"
            return inference

        inference["os"] = "iOS / macOS"

        if cod_major == 2 or any(x in name_lower for x in ["iphone", "ipod"]):
            inference["device_type"] = "Smartphone (iPhone)"
            inference["os"] = "iOS"
        elif cod_major == 1 or any(x in name_lower for x in ["macbook", "imac", "mac mini", "mac studio", "mac pro"]):
            inference["device_type"] = "Computer (Mac)"
            inference["os"] = "macOS"
        elif "ipad" in name_lower:
            inference["device_type"] = "Tablet (iPad)"
            inference["os"] = "iPadOS"
        else:
            inference["device_type"] = "Smartphone/Computer (Apple)"

        # Bluetooth never exposes the phone's actual OS version - LMP is only the chip/
        # stack version, so below we can only report a floor ("iOS 15+"), not an exact
        # release. The one exception: if the device happens to expose the standard GATT
        # Device Information Service (bonded pairing, or a permissive stack), that string
        # IS the real firmware/software version - prefer it over the LMP floor when present,
        # same as the Wearable/Audio branches already do below.
        if device_firmware:
            inference["major_minor_version"] = f"{inference['os']} {device_firmware}"
            inference["confidence"] = "High (GATT Device Info)"
            return inference

        version_floors = {
            "iOS": {13: "iOS 17+", 12: "iOS 16+", 11: "iOS 15+", 0: "iOS 14 or older"},
            "macOS": {13: "macOS 14+", 12: "macOS 13+", 11: "macOS 12+", 0: "macOS 11 or older"},
            "iPadOS": {13: "iPadOS 17+", 12: "iPadOS 16+", 11: "iPadOS 15+", 0: "iPadOS 14 or older"},
            "iOS / macOS": {13: "iOS 17+ / macOS 14+", 12: "iOS 16+ / macOS 13+", 11: "iOS 15+ / macOS 12+", 0: "iOS 14 or older / macOS 11 or older"},
        }
        floors = version_floors.get(inference["os"], version_floors["iOS / macOS"])
        if lmp_int >= 13: inference["major_minor_version"] = floors[13]
        elif lmp_int == 12: inference["major_minor_version"] = floors[12]
        elif lmp_int == 11: inference["major_minor_version"] = floors[11]
        else: inference["major_minor_version"] = floors[0]
        inference["confidence"] = "High" if not is_missing_data else "Medium"
        return inference
    
    # 2. Exact Android Scoring Engine
    # The C binary generates an 'estimated_android' score for ALL devices.
    # We must only trust it if we have strong proof the device is actually a phone (PBAP, MAP, or Vendor).
    # Vendor name alone is weak evidence - Samsung/Xiaomi/Huawei etc. also make earbuds, watches,
    # and other accessories. CoD is the ground truth for device category (2 = Phone), so a
    # vendor-only match is discarded whenever CoD is present and says otherwise (e.g. 4 = Audio/Video,
    # 7 = Wearable). PBAP/MAP and an explicit "android" in the name remain trusted regardless,
    # since real phones expose those profiles and accessories don't.
    cod_says_not_phone = cod_major is not None and cod_major != 2
    is_android_phone = (f_pbap or f_map or "android" in name_lower or
                        (not cod_says_not_phone and any(x in vendor.lower() for x in ["samsung", "pixel", "motorola", "xiaomi", "oneplus", "huawei", "oppo", "vivo"])))
    
    if is_android_phone:
        inference["os"] = "Android"
        inference["device_type"] = "Smartphone"
        # The C helper (version_finder_integrated.c) prints its own "Estimated
        # Android Version" line, and this branch used to return it verbatim,
        # short-circuiting the ladder below. That was wrong: the helper carries
        # its own, older copy of the scoring table, which still has BOTH defects
        # the Python ladder was corrected for - a non-monotonic LMP base (LMP 9
        # scores 85 against LMP 10's 68, so BT 5.1 mapped to an OLDER Android
        # than BT 5.0) and the (score/105)*10 float rescale that made whole
        # bands unreachable. Whenever the helper binary happened to be present
        # its defective label won, so the invariants asserted by
        # tests/test_android_score_ladder.py held only on the path nothing took.
        # We now use the helper for what it reliably provides - the LMP integer
        # and the profile flags read below - and score here, on one ladder.
        # c_data["estimated_android"] is still parsed by run_c_version_finder()
        # and kept for the archive, but is deliberately not an input.

        # Raw integer score: LMP base (non-decreasing, see ANDROID_LMP_BASE)
        # plus profile/evidence bonuses, clipped to ANDROID_SCORE_MAX. Bands are
        # compared against this integer directly - see the invariant notes above
        # ANDROID_VERSION_BANDS for why the old float rescale was removed.
        score = android_lmp_base(lmp_int)

        f_a2dp = c_data["flags"]["a2dp"] or sdp_flags["a2dp"]
        f_hfp  = c_data["flags"]["hfp"] or sdp_flags["hfp"]
        f_opp  = c_data["flags"]["opp"] or sdp_flags["opp"]
        f_did  = c_data["flags"]["did"] or sdp_flags["did"]

        if f_a2dp: score += ANDROID_BONUSES["a2dp"]
        if f_hfp: score += ANDROID_BONUSES["hfp"]
        if f_map: score += ANDROID_BONUSES["map"]
        if f_pbap: score += ANDROID_BONUSES["pbap"]
        if f_opp: score += ANDROID_BONUSES["opp"]
        if f_did: score += ANDROID_BONUSES["did"]
        if lmp_int >= 11 and f_did: score += ANDROID_BONUSES["did_modern_lmp"]

        # PROVISIONAL - small additional evidence layer from the LMP Features bitmap,
        # not a hard rule. "Simultaneous LE and BR/EDR" is a controller-level capability
        # that only became common on newer dual-mode chipsets, so its presence weakly
        # skews toward a more recent Android release. Magnitude intentionally kept small
        # (+1) pending confirmation before tuning further; invariant I3 guarantees this
        # +1 can never move the estimate by more than one version band.
        if lmp_features and lmp_features.get("lmp_features", {}).get("simultaneous_le_bredr"):
            score += ANDROID_BONUSES["lmp_simultaneous_le_bredr"]

        # PROVISIONAL - second small evidence layer, from GATT Preferred Connection
        # Parameters, awaiting ground-truth calibration (see research_evaluation.csv
        # feedback) before tuning further. Apple's public Accessory Design Guidelines
        # require MFi BLE accessories to request a minimum connection interval >=
        # 15ms; a minimum interval below that is weak evidence AGAINST Apple-ecosystem
        # ADG compliance. It only nudges the score here, in the branch we've already
        # otherwise concluded is non-Apple - this is NOT a standalone Apple/Android
        # classifier and connection parameters are ultimately app/firmware-chosen, not
        # OS-mandated, so treat this as a soft tiebreaker only.
        if gatt_conn_params and gatt_conn_params.get("preferred_conn_interval_min_ms") is not None:
            if gatt_conn_params["preferred_conn_interval_min_ms"] < 15:
                score += ANDROID_BONUSES["gatt_conn_interval_sub_15ms"]

        # Clip after bonuses. Without this the bonuses could carry the sum to 128
        # while every comment and the paper claimed a ceiling of 105.
        score = max(0, min(score, ANDROID_SCORE_MAX))
        inference["android_score_raw"] = score
        inference["android_score_max"] = ANDROID_SCORE_MAX

        version = android_version_from_score(score)
        if version is None:
            version = "Android (Unknown Version - Hardware Profile Missing)" if is_missing_data else "Android 7.0 or older"
            
        inference["major_minor_version"] = version
        inference["confidence"] = "Medium" if is_missing_data else "High"
        return inference

    # 2. IoT
    if any(iot in vendor.lower() for iot in ["espressif", "texas", "nordic", "tuya", "xiaomi", "raspberry"]):
        inference["device_type"] = "IoT Peripheral / Embedded"
        inference["os"] = "RTOS / Baremetal"
        inference["major_minor_version"] = "N/A"
        inference["confidence"] = "High" if not is_missing_data else "Medium"
        return inference
        

    # 4. PC / Laptop Engine (Windows & Linux)
    pc_vendors = ["intel", "cloud network", "realtek", "mediatek", "qualcomm", "broadcom", "atheros", "azurewave", "rivet", "killer", "lenovo", "dell", "hp", "asus", "acer", "microsoft"]
    is_pc = (any(x in vendor.lower() for x in pc_vendors) or 
             "windows" in name_lower or "pc" in name_lower.split() or 
             "desktop" in name_lower or "laptop" in name_lower or
             ("audio source" in services_str and "audio sink" in services_str))
             
    if is_pc:
        inference["device_type"] = "PC / Laptop"
        
        # Check explicit Linux markers
        if "bluez" in services_str or "ubuntu" in name_lower or "debian" in name_lower or "linux" in name_lower:
            inference["os"] = "Linux (BlueZ)"
            inference["major_minor_version"] = f"BlueZ Stack (LMP {lmp_int})"
            inference["confidence"] = "High (Explicit Linux Marker)"
        else:
            # Fallback to Windows for standard PC network cards
            inference["os"] = "Windows"
            if lmp_int >= 12: inference["major_minor_version"] = "Windows 11"
            elif lmp_int == 10 or lmp_int == 11: inference["major_minor_version"] = "Windows 10"
            elif lmp_int == 8 or lmp_int == 9: inference["major_minor_version"] = "Windows 8.1 / 10"
            else: inference["major_minor_version"] = "Windows 7 or older"
            
            inference["confidence"] = "High" if not is_missing_data else "Medium"
            
        return inference
            
    # 5. Wearables (Smartwatches / Fitness Bands)
    # CoD major class 7 is the Bluetooth spec's own "Wearable" category - authoritative when present.
    if cod_major == 7 or "watch" in name_lower:
        inference["device_type"] = "Wearable (Smartwatch/Band)"
        inference["os"] = "Embedded Firmware (RTOS)"
        if device_firmware:
            inference["major_minor_version"] = f"Firmware {device_firmware}"
            inference["confidence"] = "High (GATT Device Info)"
        else:
            inference["major_minor_version"] = f"Wearable Device (LMP {lmp_int})"
            inference["confidence"] = "High (CoD Heuristic)" if cod_major == 7 else "Medium (Name Heuristic)"
        return inference

    # 6. Audio Peripherals
    # CoD major class 4 (Audio/Video) is authoritative and doesn't depend on the device name
    # resolving successfully, unlike the keyword match below.
    audio_keywords = ["airdopes", "airpods", "earbuds", "buds", "headphones", "headset", "speaker", "audio", "jbl", "bose", "sony", "boat", "sennheiser"]
    if cod_major == 4 or any(x in name_lower for x in audio_keywords) or "audio sink" in services_str or c_data["flags"]["a2dp"] or sdp_flags["a2dp"]:
        inference["device_type"] = "Audio Peripheral / Headset"
        inference["os"] = "Embedded Firmware (RTOS)"
        if device_firmware:
            inference["major_minor_version"] = f"Firmware {device_firmware}"
            inference["confidence"] = "High (GATT Device Info)"
        else:
            inference["major_minor_version"] = f"Audio Sink Device (LMP {lmp_int})"
            inference["confidence"] = "High (Name/Service Heuristic)" if any(x in name_lower for x in audio_keywords) or "audio sink" in services_str or c_data["flags"]["a2dp"] or sdp_flags["a2dp"] else "High (CoD Heuristic)"
        return inference

    inference["device_type"] = "Unknown Peripheral"
    if device_firmware:
        inference["os"] = "Embedded Firmware (RTOS)"
        inference["major_minor_version"] = f"Firmware {device_firmware}"
        inference["confidence"] = "Medium (GATT Device Info)"
    return inference

def _confidence_string_to_score(confidence_str):
    """
    Maps the existing free-text confidence label (e.g. "High", "Medium (Chipset/OS
    Inconsistency Detected)") onto a numeric 0-1 confidence_score. Provisional/
    uncalibrated buckets - only the ordering (High > Medium > Low) is meaningful
    right now, not the exact numbers.
    """
    if confidence_str.startswith("High"): return 0.9
    if confidence_str.startswith("Medium"): return 0.6
    if confidence_str.startswith("Low"): return 0.3
    return 0.3

def _lower_confidence_one_level(confidence_str, reason):
    """
    Drops a free-text confidence label exactly one qualitative level,
    High -> Medium -> Low, and annotates it with the reason. Low is the floor.

    This used to be open-coded as `if confidence == "High": confidence =
    "Medium (...)"`, which silently did nothing to a prediction that was already
    Medium - so a Medium prediction with a conflicting signal was reported with
    the same label as a Medium prediction with none, and the conflict was
    visible only in has_conflicting_signals. The ladder is qualitative on
    purpose: the weights are not calibrated, so only the ordering is meaningful.
    """
    if confidence_str.startswith("High"):
        return f"Medium ({reason})"
    if confidence_str.startswith("Medium"):
        return f"Low ({reason})"
    return confidence_str if confidence_str.startswith("Low") else f"Low ({reason})"


def _infer_mobility_conflict(inference, behavioral_summary):
    """
    PROVISIONAL, not ground-truth calibrated: a high RSSI standard deviation over the
    Layer 3 observation window suggests physical movement (a handheld/worn device),
    while a very low stdev suggests a stationary device (PC, IoT sensor, desk
    peripheral). Used only to add a "worth a second look" evidence_chain entry -
    never changes the device_type/os prediction itself.
    """
    if not behavioral_summary:
        return None
    rssi_stats = behavioral_summary.get("rssi", {})
    stdev = rssi_stats.get("stdev")
    sample_count = rssi_stats.get("sample_count", 0)
    if stdev is None:
        return None

    stationary_types = {"PC / Laptop", "IoT Peripheral / Embedded"}
    mobile_types = {"Smartphone", "Smartphone (iPhone)", "Tablet (iPad)", "Wearable (Smartwatch/Band)"}
    device_type = inference.get("device_type")

    if device_type in stationary_types and sample_count >= 5 and stdev >= 6:
        return {
            "signal_name": "behavioral_rssi_variance",
            "observed_value": f"RSSI stdev {stdev} dBm over {sample_count} samples",
            "inference": "High signal variance over the observation window suggests physical movement",
            "contribution": f"Weakly conflicts with stationary classification '{device_type}'",
            "weight": 0.1,
            "direction": "conflicts",
        }
    if device_type in mobile_types and sample_count >= 10 and stdev < 1.5:
        return {
            "signal_name": "behavioral_rssi_variance",
            "observed_value": f"RSSI stdev {stdev} dBm over {sample_count} samples",
            "inference": "Very low signal variance suggests the device didn't move during the scan",
            "contribution": f"Weakly conflicts with mobile classification '{device_type}' (a stationary phone/watch is still possible)",
            "weight": 0.05,
            "direction": "conflicts",
        }
    return None

def build_evidence_chain(inference, cod_hex, vendor, name, lmp_features, chipset_info, gatt_appearance, gatt_conn_params, sdp_full_records, behavioral_summary, prior_encounter=None):
    """
    Post-hoc evidence audit trail: re-examines the Layer 1/2/3 signals
    predict_device_core already used (plus ones it doesn't touch directly, like raw
    SDP service-name text and behavioral data) and records, per signal, what was
    observed and whether it's consistent ("supports") or inconsistent ("conflicts")
    with the final prediction. Built here in the wrapper - post-hoc - rather than
    threaded through predict_device_core's branches, so none of the existing Layer
    1/2 scoring logic has to be touched/risked to add this.

    Weights are provisional placeholders (not ground-truth calibrated) - see the
    per-signal comments below for the reasoning behind each one. An entry is only
    added when the signal was actually relevant to how the final prediction was
    reached (e.g. the LMP Features bonus only applied in the Android scoring
    branch), so an empty/short chain for a given scan is expected, not a bug.
    """
    chain = []
    os_str = inference.get("os", "")
    device_type = inference.get("device_type", "")

    # 1. LMP Features - only meaningful in the Android scoring branch that actually
    # used it (see the "simultaneous_le_bredr" bonus in predict_device_core).
    # NOTE: predict_device_core already added this bit's +1 into the version score
    # before we get here, so recording "supports" against that same score would be
    # circular (the entry would just be confirming it agrees with a total it was
    # added into) - same anti-circularity reasoning as gatt_appearance below. It's
    # recorded as "primary" - a scoring input, not independent corroborating
    # evidence - and excluded from the conflict count/confidence penalty.
    if lmp_features and lmp_features.get("lmp_features", {}).get("simultaneous_le_bredr") and os_str == "Android":
        chain.append({
            "signal_name": "lmp_features_simultaneous_le_bredr",
            "observed_value": True,
            "inference": "Controller supports Simultaneous LE and BR/EDR - common on newer dual-mode chipsets",
            "contribution": "Scoring input - weakly skewed the Android version estimate newer (not independent evidence for it)",
            "weight": round(1 / 105, 3),
            "direction": "primary",
        })

    # 2. Modalias-resolved chipset - direction mirrors the chronology check already
    # computed as inconsistency_flags (check_chipset_os_consistency).
    if chipset_info and chipset_info.get("chipset_model"):
        release_year = chipset_info.get("estimated_chipset_release_year")
        # The chronology check needs a release year. Without one it never ran,
        # and "the check did not contradict the prediction" is then vacuously
        # true - there was no check. Recording that as "supports" inflates the
        # agreement count with corroboration that was never tested, which is
        # the same failure mode the primary/circularity handling exists to
        # avoid. A chipset model we cannot date is recorded as "unused",
        # weight 0: worth surfacing that the model resolved, but it is not
        # evidence either way.
        if release_year is None:
            direction, weight = "unused", 0.0
            contribution = ("Chipset model resolved but has no release year in our "
                            "table, so the chronology check could not run - this "
                            "entry is not evidence for or against the prediction")
        else:
            conflicts = bool(inference.get("inconsistency_flags"))
            direction = "conflicts" if conflicts else "supports"
            weight = 0.15
            contribution = chipset_info.get("estimated_min_os_hint") or "No OS floor hint available"
        chain.append({
            "signal_name": "modalias_chipset",
            "observed_value": chipset_info["chipset_model"],
            "inference": (f"Chipset released ~{release_year}" if release_year is not None
                          else "Chipset release year unknown"),
            "contribution": contribution,
            "weight": weight,
            "direction": direction,
        })

    # 3. GATT Appearance - only scored when it actually stood in for a missing CoD
    # (see predict_device_core's cod_major fallback via appearance_category_to_cod_major).
    # NOTE: when appearance_major resolves, it's the exact value predict_device_core
    # used to derive device_type in this branch - so it cannot be judged "supports"/
    # "conflicts" against device_type without being circular (the scorer would just be
    # agreeing with itself). It's recorded as "primary" - the driving signal, not
    # corroborating evidence - and excluded from the conflict count/confidence penalty
    # below. When it fails to resolve, it had zero effect on device_type (some other
    # branch decided it), so it isn't in conflict with anything either - it's simply
    # unused, which is worth surfacing but isn't a contradiction.
    if gatt_appearance and gatt_appearance.get("gatt_appearance_category") and decode_cod_major_class(cod_hex) is None:
        appearance_major = appearance_category_to_cod_major(gatt_appearance["gatt_appearance_category"])
        chain.append({
            "signal_name": "gatt_appearance",
            "observed_value": gatt_appearance["gatt_appearance_category"],
            "inference": "BLE Generic Access category, used as a Class-of-Device substitute (CoD absent on this device)",
            "contribution": (
                f"Primary signal behind device_type '{device_type}' - not independent evidence for it"
                if appearance_major is not None
                else "Category didn't map to a known device class - unused, did not influence device_type"
            ),
            "weight": 0.3 if appearance_major is not None else 0.0,
            "direction": "primary" if appearance_major is not None else "unused",
        })

    # 4. GATT Preferred Connection Parameters - only meaningful in the Android
    # scoring branch that actually used it (Apple MFi ADG minimum-interval check).
    # NOTE: same circularity concern as signal 1 above - this value's +1 was already
    # folded into the version score before we get here, so it's recorded as
    # "primary" (a scoring input), not "supports", and excluded from the conflict
    # count/confidence penalty.
    if gatt_conn_params and gatt_conn_params.get("preferred_conn_interval_min_ms") is not None and os_str == "Android":
        if gatt_conn_params["preferred_conn_interval_min_ms"] < 15:
            chain.append({
                "signal_name": "gatt_preferred_conn_params",
                "observed_value": f"{gatt_conn_params['preferred_conn_interval_min_ms']}ms min connection interval",
                "inference": "Below Apple's MFi Accessory Design Guidelines minimum (15ms)",
                "contribution": "Scoring input - weakly skewed the Android version estimate (non-Apple-ADG-compliant), not independent evidence for it",
                "weight": round(1 / 105, 3),
                "direction": "primary",
            })

    # 5. SDP Service Name/Description text - vendor keyword hints, cross-checked
    # against the OUI-resolved vendor and the device's advertised name.
    haystack = f"{vendor} {name}".lower()
    for record in (sdp_full_records or []):
        for hint in record.get("sdp_extracted_hints", []):
            if not hint.startswith("vendor_keyword:"):
                continue
            brand = hint.split(":", 1)[1]
            matches_vendor = brand in haystack
            chain.append({
                "signal_name": "sdp_service_name",
                "observed_value": record.get("service_name_raw") or record.get("service_description_raw"),
                "inference": f"Raw SDP text contains vendor keyword '{brand}'",
                "contribution": "Corroborates OUI-resolved vendor" if matches_vendor else "Vendor keyword doesn't match OUI-resolved vendor/name - worth a manual look",
                "weight": 0.05,
                "direction": "supports" if matches_vendor else "conflicts",
            })

    # 6. Behavioral summary (Layer 3) - advertising interval shift is informational
    # only for now (not yet weighted into any score); RSSI-variance-vs-mobility is
    # the one behavioral signal that can actually conflict with a prediction.
    if behavioral_summary:
        adv = behavioral_summary.get("advertising_interval_ms", {})
        if adv.get("interval_shift_detected"):
            chain.append({
                "signal_name": "behavioral_advertising_interval_shift",
                "observed_value": adv.get("shift_detail"),
                "inference": "Advertising interval changed mid-scan - device likely switched power/activity mode",
                "contribution": "Informational only - not yet weighted into device/OS scoring pending ground-truth calibration",
                "weight": 0.0,
                "direction": "supports",
            })
        mobility_conflict = _infer_mobility_conflict(inference, behavioral_summary)
        if mobility_conflict:
            chain.append(mobility_conflict)

    # 7. Class of Device vs. GATT Appearance - two device-category signals from two
    # different stacks (BR/EDR inquiry vs. BLE GAP), independent of each other by
    # construction: predict_device_core only ever consults Appearance as a CoD
    # *fallback* when cod_major is None (see its own comment above signal 3), so
    # whenever we reach here with a real CoD major class already resolved, Appearance
    # played no part in deriving device_type - checking the two against each other is
    # not circular. This is the pair Section 4.8 exists to test: unlike
    # modalias_chipset (signal 2), which needs a resolved chipset model - present for
    # only 1 of 20 addresses in the pilot (Section 4.1) - both CoD and Appearance are
    # comparatively cheap/common signals, so this pair should fire far more often.
    cod_major_real = decode_cod_major_class(cod_hex)
    if cod_major_real is not None and gatt_appearance and gatt_appearance.get("gatt_appearance_category"):
        appearance_major = appearance_category_to_cod_major(gatt_appearance["gatt_appearance_category"])
        if appearance_major is not None:
            matches = appearance_major == cod_major_real
            chain.append({
                "signal_name": "cod_vs_gatt_appearance",
                "observed_value": f"CoD major=0x{cod_major_real:02x}, Appearance='{gatt_appearance['gatt_appearance_category']}'",
                "inference": f"Appearance maps to CoD major-class 0x{appearance_major:02x}",
                "contribution": "Two independent device-category signals agree" if matches else "CoD and Appearance disagree on device category - independent evidence of a conflict, not a scoring artifact",
                "weight": 0.2,
                "direction": "supports" if matches else "conflicts",
            })

    # 8. Device name text vs. GATT Appearance - a second independent category pair,
    # deliberately using a keyword scan (infer_device_category_from_name) separate
    # from predict_device_core's own name-based branches, so this signal is derived
    # from raw name text only, never from a decision that already used device_type.
    name_major = infer_device_category_from_name(name)
    if name_major is not None and gatt_appearance and gatt_appearance.get("gatt_appearance_category"):
        appearance_major = appearance_category_to_cod_major(gatt_appearance["gatt_appearance_category"])
        if appearance_major is not None:
            matches = appearance_major == name_major
            chain.append({
                "signal_name": "name_vs_gatt_appearance",
                "observed_value": f"name='{name}', Appearance='{gatt_appearance['gatt_appearance_category']}'",
                "inference": f"Name keyword maps to major-class 0x{name_major:02x}, Appearance maps to 0x{appearance_major:02x}",
                "contribution": "Advertised name and Appearance agree on device category" if matches else "Advertised name and Appearance disagree on device category",
                "weight": 0.1,
                "direction": "supports" if matches else "conflicts",
            })

    # 9. Class-of-Device vs. device name text - the third category pair, and the
    # only one that does NOT depend on GATT Appearance.
    #
    # Why it was added: pairs 7 and 8 are both anchored on Appearance, which the
    # availability measurement found on 2 of 115 archived records. Selecting
    # pairs for independence alone turned out to be the wrong criterion - a pair
    # is only useful if both halves are also commonly present, and the signals
    # most clearly independent of the primary decision path are precisely the
    # ones that path did not need, hence the ones a device is least likely to
    # expose. CoD and the advertised name are both comparatively common.
    #
    # The independence argument here is DIFFERENT from pairs 7 and 8, and weaker
    # in one respect, so it is worth stating rather than assuming. For pair 7 the
    # argument is that Appearance played no part in deriving device_type when a
    # real CoD was present. That does not hold here: predict_device_core consults
    # both CoD and name keywords in its branches (e.g. the wearable branch fires
    # on cod_major == 7 OR "watch" in the name), so both halves of this pair fed
    # the prediction.
    #
    # It is still not circular, because a pair check does not ask whether a
    # signal agrees with the *output*. It asks whether two separately derived
    # inputs agree with *each other*. decode_cod_major_class() is a pure decode
    # of a device-declared field and infer_device_category_from_name() is a
    # keyword scan kept deliberately separate from predict_device_core's own
    # name branches; neither is computed from device_type. A disagreement
    # therefore means the prediction rests on two inputs that contradict one
    # another, which is exactly the condition worth surfacing to an auditor and
    # exactly what a single fused score destroys.
    name_major_vs_cod = infer_device_category_from_name(name)
    if cod_major_real is not None and name_major_vs_cod is not None:
        matches = cod_major_real == name_major_vs_cod
        chain.append({
            "signal_name": "cod_vs_device_name",
            "observed_value": f"CoD major=0x{cod_major_real:02x}, name='{name}'",
            "inference": f"Name keyword maps to major-class 0x{name_major_vs_cod:02x}",
            "contribution": (
                "Class-of-Device and advertised name agree on device category"
                if matches else
                "Class-of-Device and advertised name disagree on device category - "
                "the prediction rests on two contradictory inputs"
            ),
            "weight": 0.15,
            "direction": "supports" if matches else "conflicts",
        })

    # 8. Prior encounters with this same device (observation_store). This is the
    # only cross-scan entry, and it compares OBSERVATIONS, never predictions:
    # checking a new prediction against archived predictions from the same
    # scorer measures self-consistency, not correctness. It is also asymmetric
    # by construction - a mismatch in a field that cannot legitimately change
    # is recorded as "conflicts", while agreement is "unused" at weight 0,
    # since a reader agreeing with itself is not independent corroboration.
    # Built by the caller (observation_store.prior_encounter_entry) so this
    # function stays free of file I/O and remains unit-testable.
    if prior_encounter:
        chain.append(prior_encounter)

    return chain

def predict_device(hw_info, services, sdp_flags, sdp_handles, gatt_uuids, vendor, name, c_data, cod_hex="N/A", deep_gatt=None, lmp_features=None, chipset_info=None, gatt_appearance=None, gatt_conn_params=None, sdp_full_records=None, behavioral_summary=None, prior_encounter=None):
    """
    Thin wrapper around predict_device_core(): runs the existing rule/scoring engine
    unchanged, then layers on (a) a post-hoc chipset/OS chronology sanity check using
    the Modalias-derived chipset_info (see enrich_modalias_with_chipset), and (b) a
    full evidence_chain audit trail (see build_evidence_chain) covering every Layer
    1/2/3 signal, including the optional Layer 3 behavioral_summary (absent in the
    fast single-shot scan - this function works identically with or without it).
    None of this changes the predicted device_type/os/version - it only flags
    contradictions for review and softens the confidence label/score when found.
    """
    inference = predict_device_core(hw_info, services, sdp_flags, sdp_handles, gatt_uuids, vendor, name, c_data, cod_hex, deep_gatt, lmp_features, gatt_appearance, gatt_conn_params)
    inference["inconsistency_flags"] = []
    if chipset_info and chipset_info.get("estimated_chipset_release_year"):
        flags = check_chipset_os_consistency(inference.get("major_minor_version", ""), chipset_info["estimated_chipset_release_year"])
        inference["inconsistency_flags"] = flags
        if flags:
            inference["confidence"] = _lower_confidence_one_level(
                inference["confidence"], "Chipset/OS Inconsistency Detected")

    evidence_chain = build_evidence_chain(inference, cod_hex, vendor, name, lmp_features, chipset_info, gatt_appearance, gatt_conn_params, sdp_full_records, behavioral_summary, prior_encounter)
    inference["evidence_chain"] = evidence_chain

    has_conflicts = any(e["direction"] == "conflicts" for e in evidence_chain)
    inference["has_conflicting_signals"] = has_conflicts

    if has_conflicts:
        inference["confidence"] = _lower_confidence_one_level(
            inference["confidence"], "Conflicting Evidence Signals")

    # The reported confidence is the qualitative label above; confidence_score is
    # a derived convenience for sorting/filtering the CSV and is NOT a calibrated
    # probability. It is now taken straight from the (already lowered) label
    # rather than additionally decremented by 0.15 per conflict: that decrement
    # made the numeric value sensitive to the conflict COUNT while the label was
    # not, so the two disagreed about how bad a prediction was, and it amounted
    # to scaling a probability we have no grounds to scale.
    inference["confidence_score"] = _confidence_string_to_score(inference["confidence"])

    return inference

CSV_FIELDNAMES = [
    "Timestamp", "MAC Address", "Device Name", "Vendor",
    "Predicted OS", "OS Confidence", "Predicted Device Type",
    "Uptime", "Security", "Distance", "RTT (ms)",
    "RSSI (dBm)", "TX Power (dBm)", "Link Quality",
    "LMP Version", "LMP Subversion", "Hardware Manufacturer", "Baseband Features",
    "Link Policy", "Supervision Timeout", "Clock Offset",
    "AFH Map", "AFH Mode", "MTU Reliability",
    "Permissions", "Protocols", "Services",
    "DBus Battery", "Class of Device", "Modalias",
    "SDP Handles", "GATT UUIDs", "Deep GATT Strings",
    "LMP Features Raw", "LMP Features (Notable)",
    "Chipset Vendor", "Chipset Product ID", "Chipset Model",
    "Chipset Release Year", "Estimated Min OS Hint", "Inconsistency Flags",
    "GATT Appearance Raw", "GATT Appearance Category",
    "Preferred Conn Interval Min (ms)", "Preferred Conn Interval Max (ms)",
    "Preferred Slave Latency", "Preferred Supervision Timeout (ms)",
    "SDP Service Names (Raw)", "SDP Service Descriptions (Raw)", "SDP Extracted Hints",
    "Confidence Score", "Has Conflicting Signals", "Evidence Chain Summary",
    "Discrepancy Notes"
]

def ensure_csv_columns(csv_file, required_columns):
    """
    Migrates research_evaluation.csv in place so its header contains every column in
    required_columns, without touching existing rows/columns (e.g. a "Correct" column
    record_feedback.py may have already appended). Old rows simply get a blank value
    for any newly-added column - same pattern record_feedback.py already uses for
    "Correct", so both scripts stay compatible with each other's migrations.
    """
    import csv
    if not os.path.isfile(csv_file):
        return
    with open(csv_file, newline="", encoding="utf-8") as f:
        # restkey="_overflow": a row with more fields than the header (e.g. an
        # unescaped comma from an older, buggier write) would otherwise land
        # under the DictReader default restkey of None, which then crashes
        # DictWriter.writerows() below with "dict contains fields not in
        # fieldnames: None" - a real crash this migration hit once already.
        reader = csv.DictReader(f, restkey="_overflow")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing = [c for c in required_columns if c not in fieldnames]
    if not missing:
        return

    fieldnames.extend(missing)
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        # extrasaction="ignore": drop any "_overflow" overflow field rather than
        # raising - a malformed old row shouldn't be able to crash every future
        # scan's CSV migration step.
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def behavioral_main(mac, duration_seconds, sample_interval_seconds, is_ble):
    """
    CLI/subprocess entry point for:
      python3 advanced_nmap_scanner.py --behavioral <mac> [duration] [interval] [--ble]

    Unlike main()'s single end-of-scan JSON blob (mixed with "[>] ..." log() lines,
    which the Express /api/advanced_nmap route separates out by string search), this
    prints ONE JSON object per line to stdout as each event happens (NDJSON). The
    Express SSE route (backend/routes/behavioral_scan.js) reads stdout line by line
    and forwards each line to the browser as an SSE event as it arrives, instead of
    buffering the whole ~45s scan - so every stdout line here MUST be valid JSON,
    including status/progress messages (as {"type": "status", ...} events rather
    than log()'s "[>] ..." prefix).
    """
    _install_sigterm_handler()

    def emit(event):
        print(json.dumps(event), flush=True)

    emit({"type": "status", "message": f"Starting behavioral scan on {mac} for {duration_seconds}s (interval={sample_interval_seconds}s, ble={is_ble})"})
    try:
        behavioral_scan(mac, duration_seconds, sample_interval_seconds, is_ble=is_ble, emit=emit)
    except _GracefulStop:
        pass

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--behavioral":
        if len(sys.argv) < 3:
            sys.exit(1)
        mac = sys.argv[2]
        duration_seconds = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 45
        sample_interval_seconds = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else 2
        is_ble = "--ble" in sys.argv[5:]
        behavioral_main(mac, duration_seconds, sample_interval_seconds, is_ble)
        return

    if len(sys.argv) not in (2, 3):
        sys.exit(1)

    mac = sys.argv[1]
    # Defaults to False (not just "unspecified means True") so that any caller
    # that forgets to pass this - a stray direct invocation, a future script -
    # fails toward not writing an unverifiable row into research_evaluation.csv,
    # rather than silently polluting the ground-truth set. The dashboard always
    # passes this explicitly (see backend/routes/advanced_nmap.js) based on the
    # "I can verify this device" checkbox - unchecked by default there too, since
    # most scans (a public sweep of strangers' devices) can never be verified.
    log_ground_truth = len(sys.argv) == 3 and sys.argv[2] == "true"
    log(f"INITIALIZING SOFTWARE-LEVEL NMAP SCAN ON {mac}")
    log("-" * 50)

    dev_name = get_device_name(mac)
    rtt = measure_rtt(mac)
    bb_metrics = measure_baseband_metrics(mac)
    dbus_props = query_dbus_properties(mac)
    device_id_info = decode_modalias(dbus_props.get("modalias"))
    if device_id_info:
        device_id_info["vendor_name"] = lookup_company_id(device_id_info["vendor_id"])
        device_id_info = enrich_modalias_with_chipset(device_id_info)
        dbus_props["device_id_profile"] = device_id_info
        log(f"Device ID Profile decoded -> Vendor: {device_id_info['vendor_name']} | Product: 0x{device_id_info['product_id']} | Version: 0x{device_id_info['version']}")
        if device_id_info.get("chipset_model"):
            log(f"Chipset matched -> {device_id_info['chipset_model']} (~{device_id_info['estimated_chipset_release_year']}) | {device_id_info['estimated_min_os_hint']}")
    gatt_uuids = get_gatt_uuids(mac)
    lmp_features = parse_lmp_features(mac)

    # Layer 2 fingerprinting signals - GATT Appearance/Preferred Conn Params are
    # BLE-side (Generic Access Service 0x1800); the full SDP attribute tree is
    # Classic BR/EDR-side (sdptool). Kept as separate calls from the Layer 1
    # gatt_uuids/get_sdp_services extraction above so neither scan's parsing logic
    # gets tangled with the other's.
    gatt_appearance, _ = query_gatt_appearance(mac)
    gatt_conn_params, _ = query_gatt_preferred_conn_params(mac)
    sdp_full_records, _ = get_sdp_full_service_details(mac)

    # Aggressive Extractions
    deep_gatt = query_deep_gatt(mac)
    afh_state = measure_afh_state(mac)
    mtu_reliability = test_mtu_reliability(mac)

    c_data = run_c_version_finder(mac)
    hw_info = get_hcitool_info(mac)
    services, protocols, sdp_flags, sdp_handles = get_sdp_services(mac)
    vendor = lookup_oui(mac)
    
    if c_data["success"]:
        if hw_info["lmp_version"] == "Unknown":
            hw_info["lmp_version"] = f"Extracted via Socket (LMP {c_data['lmp_integer']})"
        hw_info["lmp_integer"] = c_data["lmp_integer"]
        
    if hw_info["lmp_subversion"] == "Unknown" and dbus_props["modalias"] != "N/A":
        hw_info["lmp_subversion"] = f"Hidden by Baseband (Modalias: {dbus_props['modalias']})"
    elif hw_info["lmp_subversion"] == "Unknown":
        hw_info["lmp_subversion"] = "Hidden by Controller Security"
    
    # Cross-encounter comparison. The observation is built and compared BEFORE
    # it is stored, so a device is never compared against the very scan being
    # made. Only raw readings are stored (see observation_store): comparing the
    # new prediction against archived predictions from the same scorer would
    # measure self-consistency rather than correctness, and the store exists
    # precisely to avoid that. The result can only annotate and lower
    # confidence, never raise it and never enter the score.
    prior_encounter = None
    observation = None
    try:
        observation = observation_store.build_observation(
            mac, dbus_props.get("class_of_device", "N/A"), vendor,
            device_id_info, hw_info, c_data, sdp_flags, gatt_uuids,
            gatt_appearance, dev_name)
        priors = observation_store.load_prior_observations(observation["device_key"])
        prior_encounter = observation_store.prior_encounter_entry(observation, priors)
        if priors:
            log(f"Seen before: {len(priors)} earlier observation(s) of this device")
            if prior_encounter and prior_encounter["direction"] == "conflicts":
                log(f"  -> {prior_encounter['inference']}")
    except Exception as exc:
        log(f"Observation store unavailable ({exc}) - continuing without cross-encounter check")

    prediction = predict_device(hw_info, services, sdp_flags, sdp_handles, gatt_uuids, vendor, dev_name, c_data, dbus_props.get("class_of_device", "N/A"), deep_gatt, lmp_features, device_id_info, gatt_appearance, gatt_conn_params, sdp_full_records, None, prior_encounter)

    if observation is not None:
        observation_store.record_observation(observation)
    permissions = extract_permissions(sdp_flags, dev_name)
    deep_meta = infer_deep_metadata(hw_info["lmp_integer"], vendor, rtt, sdp_handles, gatt_uuids, protocols)
    
    log("SCAN COMPLETE. COMPILING REPORT...")

    rtt_str = "Timeout (Device rejected ping)"
    if rtt: rtt_str = f"Min: {rtt['min']}ms | Avg: {rtt['avg']}ms | Max: {rtt['max']}ms"

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = {
        "timestamp": timestamp,
        "features": {
            "mac": mac, "name": dev_name, "vendor": vendor,
            "rtt_ms": rtt_str, "distance_est": bb_metrics["distance_m"],
            "uptime": bb_metrics.get("uptime", "Unknown"),
            "security_posture": bb_metrics.get("security", "Unknown"),
            "hardware_info": hw_info, "protocols": protocols,
            "services": services, "permissions": permissions,
            "lmp_features": lmp_features,
            "gatt_appearance": gatt_appearance,
            "gatt_preferred_conn_params": gatt_conn_params,
            "sdp_full_service_records": sdp_full_records,
            "packet_metrics": {
                "absolute_rssi_dbm": bb_metrics["rssi"],
                "link_quality_0_255": bb_metrics["link_quality"],
                "tx_power_level_dbm": bb_metrics["tx_power_level"],
                "sdp_record_handles": sdp_handles,
                "gatt_uuids": gatt_uuids
            },
            "dbus_cache": dbus_props
        },
        "aggressive_interrogation": {
            "deep_gatt_characteristics": deep_gatt,
            "afh_channel_map": afh_state,
            "mtu_fragmentation_test": mtu_reliability,
            "baseband_features_hex": hw_info.get("baseband_features", "Unknown"),
            "link_policy": bb_metrics.get("link_policy", "Unknown"),
            "supervision_timeout": bb_metrics.get("supervision_timeout", "Unknown"),
            "clock_offset": bb_metrics.get("clock_offset", "Unknown")
        },
        "inferences": prediction,
        "deep_metadata": deep_meta
    }
    
    import csv
    import os

    csv_file = "research_evaluation.csv"

    lmp_notable = ""
    if lmp_features and lmp_features.get("lmp_features"):
        lmp_notable = ", ".join(sorted(k for k, v in lmp_features["lmp_features"].items() if v))

    chipset_info = device_id_info or {}

    row = {
        "Timestamp": timestamp, "MAC Address": mac, "Device Name": dev_name, "Vendor": vendor,
        "Predicted OS": prediction.get("os", "Unknown") + " " + prediction.get("major_minor_version", ""),
        "OS Confidence": prediction.get("confidence", "Unknown"),
        "Predicted Device Type": prediction.get("device_type", "Unknown"),
        "Uptime": bb_metrics.get("uptime", "Unknown"),
        "Security": bb_metrics.get("security", "Unknown"),
        "Distance": bb_metrics.get("distance_m", "Unknown"),
        "RTT (ms)": rtt_str,
        "RSSI (dBm)": bb_metrics.get("rssi", "N/A"),
        "TX Power (dBm)": bb_metrics.get("tx_power_level", "N/A"),
        "Link Quality": bb_metrics.get("link_quality", "N/A"),
        "LMP Version": hw_info.get("lmp_integer", "Unknown"),
        "LMP Subversion": hw_info.get("lmp_subversion", "Unknown"),
        "Hardware Manufacturer": hw_info.get("manufacturer", "Unknown"),
        "Baseband Features": hw_info.get("baseband_features", "Unknown"),
        "Link Policy": bb_metrics.get("link_policy", "Unknown"),
        "Supervision Timeout": bb_metrics.get("supervision_timeout", "Unknown"),
        "Clock Offset": bb_metrics.get("clock_offset", "Unknown"),
        "AFH Map": afh_state.get("map", "Unknown"),
        "AFH Mode": afh_state.get("mode", "Unknown"),
        "MTU Reliability": mtu_reliability,
        "Permissions": " | ".join(permissions),
        "Protocols": " | ".join(protocols),
        "Services": " | ".join(services),
        "DBus Battery": dbus_props.get("battery", "N/A"),
        "Class of Device": dbus_props.get("class_of_device", "N/A"),
        "Modalias": dbus_props.get("modalias", "N/A"),
        "SDP Handles": " | ".join(sdp_handles),
        "GATT UUIDs": " | ".join(gatt_uuids),
        "Deep GATT Strings": " | ".join([f"{k}: {v}" for k, v in deep_gatt.items()]),
        "LMP Features Raw": (lmp_features or {}).get("lmp_features_raw", ""),
        "LMP Features (Notable)": lmp_notable,
        "Chipset Vendor": chipset_info.get("chipset_vendor") or "",
        "Chipset Product ID": chipset_info.get("chipset_product_id") or "",
        "Chipset Model": chipset_info.get("chipset_model") or "",
        "Chipset Release Year": chipset_info.get("estimated_chipset_release_year") or "",
        "Estimated Min OS Hint": chipset_info.get("estimated_min_os_hint") or "",
        "Inconsistency Flags": " | ".join(prediction.get("inconsistency_flags", [])),
        "GATT Appearance Raw": (gatt_appearance or {}).get("gatt_appearance_raw") or "",
        "GATT Appearance Category": (gatt_appearance or {}).get("gatt_appearance_category") or "",
        "Preferred Conn Interval Min (ms)": (gatt_conn_params or {}).get("preferred_conn_interval_min_ms") if gatt_conn_params else "",
        "Preferred Conn Interval Max (ms)": (gatt_conn_params or {}).get("preferred_conn_interval_max_ms") if gatt_conn_params else "",
        "Preferred Slave Latency": (gatt_conn_params or {}).get("preferred_slave_latency") if gatt_conn_params else "",
        "Preferred Supervision Timeout (ms)": (gatt_conn_params or {}).get("preferred_supervision_timeout_ms") if gatt_conn_params else "",
        "SDP Service Names (Raw)": " | ".join(filter(None, [r.get("service_name_raw") for r in sdp_full_records])),
        "SDP Service Descriptions (Raw)": " | ".join(filter(None, [r.get("service_description_raw") for r in sdp_full_records])),
        "SDP Extracted Hints": " | ".join(sorted(set(h for r in sdp_full_records for h in r.get("sdp_extracted_hints", [])))),
        "Confidence Score": prediction.get("confidence_score", ""),
        "Has Conflicting Signals": prediction.get("has_conflicting_signals", False),
        "Evidence Chain Summary": " | ".join(f"{e['signal_name']}:{e['direction']}" for e in prediction.get("evidence_chain", [])),
        "Discrepancy Notes": ""
    }

    try:
        with open("historical_scans.jsonl", "a") as f:
            f.write(json.dumps(report) + "\n")

        # research_evaluation.csv is a ground-truth EVALUATION set - every row
        # implicitly claims "someone can eventually say whether this prediction
        # was right." Only write one when the caller has actually said they can
        # do that (see log_ground_truth above); otherwise a scan of a device
        # nobody can verify (a stranger's phone in a public sweep) would sit in
        # this file forever as a permanently-blank row, indistinguishable from
        # a real ground-truth entry someone just hasn't gotten to yet.
        if log_ground_truth:
            file_exists = os.path.isfile(csv_file)
            if file_exists:
                ensure_csv_columns(csv_file, CSV_FIELDNAMES)
                with open(csv_file, newline="", encoding="utf-8") as hf:
                    existing_header = next(csv.reader(hf))
            else:
                existing_header = CSV_FIELDNAMES

            with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=existing_header, extrasaction="ignore")
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
    except Exception as e:
        with open("csv_error.log", "w") as ef:
            ef.write(str(e))

    report["ground_truth_logged"] = log_ground_truth
    print(json.dumps(report))

if __name__ == "__main__":
    main()
