import sys
import json
import re
import subprocess

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

import dbus
from gi.repository import GLib

BUS_NAME = "org.bluez"
ADAPTER_PATH = "/org/bluez/hci0"
DEVICE_IFACE = "org.bluez.Device1"
ADAPTER_IFACE = "org.bluez.Adapter1"
SCAN_DURATION_SECONDS = 6


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def read_connected_rssi(mac_address):
    """Devices already holding an ACL link don't get inquiry-scan RSSI reports
    (Device1.RSSI only comes from advertising/inquiry, not live connections), so
    fall back to an HCI-level read. Only called for already-connected devices —
    never forces a new connection, keeping discovery passive."""
    try:
        result = subprocess.run(
            ["hcitool", "rssi", mac_address], capture_output=True, text=True, timeout=3
        )
        match = re.search(r"RSSI return value:\s*(-?\d+)", result.stdout)
        if match:
            return -60 + int(match.group(1))
    except (subprocess.SubprocessError, OSError) as e:
        log(f"hcitool rssi fallback failed for {mac_address}: {e}")
    return None


def classify_device(device_props):
    """BlueZ only populates Class (Class of Device) from classic BR/EDR
    inquiry responses — BLE-only peripherals never get one, and mostly
    advertise with a random address. hcitool rssi/SDP baseband queries
    only work over a classic ACL link, so classic devices get full
    fingerprint support and BLE devices get limited support."""
    has_class = "Class" in device_props
    address_type = str(device_props.get("AddressType", ""))

    if has_class:
        device_type = "classic"
    elif address_type in ("public", "random"):
        device_type = "ble"
    else:
        device_type = "unknown"

    support_level = {"classic": "full", "ble": "limited"}.get(device_type, "unknown")
    return device_type, support_level


def discover_devices(scan_duration=SCAN_DURATION_SECONDS):
    """
    GetManagedObjects() returns every Device1 object BlueZ currently holds in
    memory - which is BlueZ's entire known-device cache (anything ever seen or
    paired, kept around until explicitly removed or aged out on its own
    schedule), not a snapshot of what this scan window actually saw. Naively
    returning that whole set is exactly what produced "nearby" devices that
    were nowhere near the adapter during this call - they were seen at some
    earlier, unrelated point and never got evicted from BlueZ's cache.

    Fixed by tracking which device paths actually received a signal (a brand
    new InterfacesAdded, or a PropertiesChanged - typically an RSSI update on
    an already-known object) while discovery was actively running, via a GLib
    main loop pumped for exactly scan_duration seconds instead of a plain
    time.sleep(). Only those paths, plus any device the adapter currently
    holds a live ACL link to (Connected: true is itself stronger proof of
    proximity than a signal, and such devices are documented above as not
    always re-triggering PropertiesChanged with RSSI mid-connection), are
    reported - not the full cache.
    """
    bus = dbus.SystemBus()

    adapter = dbus.Interface(
        bus.get_object(BUS_NAME, ADAPTER_PATH), ADAPTER_IFACE
    )

    seen_paths = set()

    def on_interfaces_added(path, interfaces):
        if DEVICE_IFACE in interfaces:
            seen_paths.add(str(path))

    def on_properties_changed(interface, changed, invalidated, path=None):
        if interface == DEVICE_IFACE and path is not None:
            seen_paths.add(str(path))

    bus.add_signal_receiver(
        on_interfaces_added, signal_name="InterfacesAdded",
        dbus_interface="org.freedesktop.DBus.ObjectManager", path="/",
    )
    bus.add_signal_receiver(
        on_properties_changed, signal_name="PropertiesChanged",
        dbus_interface="org.freedesktop.DBus.Properties", path_keyword="path",
    )

    log(f"Starting discovery on {ADAPTER_PATH} for {scan_duration}s...")
    adapter.StartDiscovery()
    try:
        loop = GLib.MainLoop()
        GLib.timeout_add_seconds(scan_duration, loop.quit)
        loop.run()
    finally:
        try:
            adapter.StopDiscovery()
        except dbus.exceptions.DBusException as e:
            log(f"StopDiscovery failed (already stopped?): {e}")
    log(f"Discovery finished, {len(seen_paths)} device path(s) signaled during "
        f"this window, reading managed objects...")

    obj_manager = dbus.Interface(
        bus.get_object(BUS_NAME, "/"), "org.freedesktop.DBus.ObjectManager"
    )
    managed_objects = obj_manager.GetManagedObjects()

    devices = []
    for path, interfaces in managed_objects.items():
        device_props = interfaces.get(DEVICE_IFACE)
        if not device_props:
            continue

        connected = bool(device_props.get("Connected", False))
        if str(path) not in seen_paths and not connected:
            continue

        mac = str(device_props.get("Address", "Unknown"))
        rssi = int(device_props["RSSI"]) if "RSSI" in device_props else None

        if rssi is None and connected:
            rssi = read_connected_rssi(mac)

        device_type, support_level = classify_device(device_props)

        devices.append({
            "mac": mac,
            "name": str(device_props.get("Name", device_props.get("Alias", "Unknown"))),
            "rssi": rssi,
            "class_of_device": hex(int(device_props["Class"])) if "Class" in device_props else "N/A",
            "connected": connected,
            "paired": bool(device_props.get("Paired", False)),
            "device_type": device_type,
            "support_level": support_level,
        })

    devices.sort(key=lambda d: (d["rssi"] is None, -(d["rssi"] or 0)))
    return devices


def main():
    try:
        devices = discover_devices()
        print(json.dumps({"devices": devices}))
    except dbus.exceptions.DBusException as e:
        log(f"DBus error: {e}")
        print(json.dumps({"error": str(e), "devices": []}))
        sys.exit(1)


if __name__ == "__main__":
    main()
