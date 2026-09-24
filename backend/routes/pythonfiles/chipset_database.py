# Seed chipset database for Modalias (vendor_id, product_id) -> chipset info.
#
# Sources (best-effort, cross-referenced from public data - VERIFY before relying on
# for anything beyond a soft hint):
#   - Linux kernel drivers/bluetooth/btusb.c USB device ID tables
#   - USB-IF public vendor/product listings (the usb.ids project, linux-usb.org)
#   - Bluetooth SIG assigned Company Identifiers (for `source: "bluetooth"` modalias
#     entries, as opposed to `source: "usb"` entries which use USB-IF vendor IDs -
#     these are two different numbering spaces and must not be cross-matched)
#
# Keys are (source, vendor_id, product_id), IDs as uppercase 4-hex-digit strings,
# matching the fields produced by decode_modalias(). This table is intentionally
# small - it's a seed to extend as new (vendor, product) pairs are observed in scans.
#
# "min_os_hint" is a soft, non-authoritative hint (a chipset being common on a given
# OS release does not mean the device can't run something else) - never treat it as
# a hard fact.

CHIPSET_DATABASE = {
    # Intel (USB vendor 8087)
    ("usb", "8087", "0025"): {"chipset": "Intel Bluetooth 3168", "release_year": 2016, "min_os_hint": "Windows 10 likely"},
    ("usb", "8087", "0029"): {"chipset": "Intel Bluetooth 9260/9560", "release_year": 2018, "min_os_hint": "Windows 10 1809+ likely"},
    ("usb", "8087", "0032"): {"chipset": "Intel Bluetooth AX200", "release_year": 2019, "min_os_hint": "Windows 10 1903+ likely"},
    ("usb", "8087", "0033"): {"chipset": "Intel Bluetooth AX201/AX210", "release_year": 2020, "min_os_hint": "Windows 10 2004+ likely"},

    # Broadcom (USB vendor 0A5C)
    ("usb", "0A5C", "216F"): {"chipset": "Broadcom BCM20702A0", "release_year": 2012, "min_os_hint": "Windows 7+ likely"},
    ("usb", "0A5C", "21E8"): {"chipset": "Broadcom BCM20702", "release_year": 2011, "min_os_hint": "Windows 7+ likely"},
    ("usb", "0A5C", "6412"): {"chipset": "Broadcom BCM4350C5 (Apple)", "release_year": 2016, "min_os_hint": "macOS Sierra+ likely"},

    # Realtek (USB vendor 0BDA)
    ("usb", "0BDA", "8771"): {"chipset": "Realtek RTL8761", "release_year": 2015, "min_os_hint": "Windows 8.1+ likely"},
    ("usb", "0BDA", "B00C"): {"chipset": "Realtek RTL8761B", "release_year": 2019, "min_os_hint": "Windows 10 likely"},
    ("usb", "0BDA", "B029"): {"chipset": "Realtek RTL8822CE", "release_year": 2018, "min_os_hint": "Windows 10 likely"},

    # Qualcomm Atheros (USB vendor 0CF3)
    ("usb", "0CF3", "3004"): {"chipset": "Qualcomm Atheros QCA6174", "release_year": 2014, "min_os_hint": "Windows 8.1+ likely"},
    ("usb", "0CF3", "E300"): {"chipset": "Qualcomm Atheros QCA9377", "release_year": 2015, "min_os_hint": "Windows 10 likely"},

    # MediaTek (USB vendor 0E8D)
    ("usb", "0E8D", "763F"): {"chipset": "MediaTek MT7921", "release_year": 2020, "min_os_hint": "Windows 10 2004+ likely"},

    # Apple (Bluetooth SIG company ID 004C). Apple does not publish a public PID->model
    # table the way USB-IF does for USB vendors, and the one third-party community
    # source found (theapplewiki.com/wiki/Bluetooth_PIDs) was inaccessible (HTTP 403)
    # when checked - so unlike every entry above, this one is NOT cross-referenced
    # against an independent published source. It is a single empirical observation
    # from this project's own hardware: product ID 201B was read via Modalias from a
    # real, named "AirPods" device (Class of Device 0x240418, audio major class) during
    # the Layer 2 availability audit on 2026-08-17. Treat "chipset" as "device family
    # observed", not a confirmed silicon identification (H1 vs H2 vs other), and
    # release_year/min_os_hint are deliberately left unset rather than guessed.
    ("bluetooth", "004C", "201B"): {"chipset": "Apple AirPods (family, exact SoC unconfirmed - empirical observation only)", "release_year": None, "min_os_hint": None},
}


def lookup_chipset(source, vendor_id, product_id):
    if not source or not vendor_id or not product_id:
        return None
    return CHIPSET_DATABASE.get((source, vendor_id.upper(), product_id.upper()))


# USB-IF vendor IDs (source: usb.ids project). This is a SEPARATE numbering space from
# Bluetooth SIG Company Identifiers - do not resolve "usb" source vendor_id values with
# a Bluetooth SIG company ID table, and vice versa.
USB_VENDOR_NAMES = {
    "8087": "Intel Corp.",
    "0A5C": "Broadcom Corp.",
    "0BDA": "Realtek Semiconductor Corp.",
    "0CF3": "Qualcomm Atheros Communications",
    "0E8D": "MediaTek Inc.",
}


def resolve_usb_vendor_name(vendor_id_hex):
    if not vendor_id_hex:
        return None
    return USB_VENDOR_NAMES.get(vendor_id_hex.upper())
