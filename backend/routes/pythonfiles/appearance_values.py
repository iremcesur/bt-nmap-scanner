# GATT "Appearance" (UUID 0x2A01) value table.
# Source: Bluetooth SIG Assigned Numbers - "Appearance Values" document. A 16-bit
# Appearance value packs a 10-bit category in the high bits and a 6-bit subcategory
# in the low 6 bits (value = category << 6 | subcategory), so raw_value & 0xFFC0
# recovers the base category even for an unlisted subcategory.
#
# This is a seed table covering the categories most useful for device-type
# fingerprinting (see predict_device_core's use of resolve_appearance() as a CoD
# substitute for BLE-only devices) - it is not the SIG's full assigned numbers list.
# The newer LE Audio "Generic Audio Source/Sink" values (0x09xx range) were added to
# the spec later than the classic categories below and are less consistently
# implemented by vendors - treat those two entries as lower-confidence than the rest.

APPEARANCE_VALUES = {
    0x0000: "Unknown",
    0x0040: "Generic Phone",
    0x0080: "Generic Computer",
    0x00C0: "Generic Watch",
    0x00C1: "Watch: Sports Watch",
    0x0100: "Generic Clock",
    0x0140: "Generic Display",
    0x0180: "Generic Remote Control",
    0x01C0: "Generic Eye-glasses",
    0x0200: "Generic Tag",
    0x0240: "Generic Keyring",
    0x0280: "Generic Media Player",
    0x02C0: "Generic Barcode Scanner",
    0x0300: "Generic Thermometer",
    0x0301: "Thermometer: Ear",
    0x0340: "Generic Heart Rate Sensor",
    0x0341: "Heart Rate Sensor: Heart Rate Belt",
    0x0380: "Generic Blood Pressure",
    0x0381: "Blood Pressure: Arm",
    0x0382: "Blood Pressure: Wrist",
    0x03C0: "Generic HID",
    0x03C1: "HID: Keyboard",
    0x03C2: "HID: Mouse",
    0x03C3: "HID: Joystick",
    0x03C4: "HID: Gamepad",
    0x03C5: "HID: Digitizer Tablet",
    0x03C6: "HID: Card Reader",
    0x03C7: "HID: Digital Pen",
    0x03C8: "HID: Barcode Scanner",
    0x0400: "Generic Glucose Meter",
    0x0440: "Generic Running/Walking Sensor",
    0x0480: "Generic Cycling",
    0x0481: "Cycling: Cycling Computer",
    0x0482: "Cycling: Speed Sensor",
    0x0483: "Cycling: Cadence Sensor",
    0x0484: "Cycling: Power Sensor",
    0x0485: "Cycling: Speed and Cadence Sensor",
    # LE Audio categories (Bluetooth 5.2+ Assigned Numbers addition) - lower confidence,
    # vendor adoption is inconsistent. Verify against the current SIG doc if this
    # matters for a specific device.
    0x0940: "Generic Audio (Sink)",
    0x0941: "Audio: Wireless Headset",
    0x0942: "Audio: Speaker",
    0x0980: "Generic Audio (Source)",
    0x0981: "Audio Source: Microphone",
    0x0C40: "Generic Pulse Oximeter",
    0x0C41: "Pulse Oximeter: Fingertip",
    0x0C42: "Pulse Oximeter: Wrist Worn",
    0x0C80: "Generic Weight Scale",
}


def resolve_appearance(raw_value):
    """raw_value: int (0-65535). Falls back to the base category (subcategory 0)
    when the exact subcategory isn't in the table, then to 'Unknown'."""
    if raw_value in APPEARANCE_VALUES:
        return APPEARANCE_VALUES[raw_value]
    base_category = raw_value & 0xFFC0
    if base_category in APPEARANCE_VALUES:
        return f"{APPEARANCE_VALUES[base_category]} (Unlisted Subcategory)"
    return "Unknown"


def appearance_category_to_cod_major(category):
    """
    Maps a resolved Appearance category string onto the same Class-of-Device "major
    class" integers used throughout predict_device_core (2=Phone, 1=Computer,
    7=Wearable, 4=Audio/Video, 5=Peripheral) - see decode_cod_major_class(). This lets
    Appearance stand in for CoD on BLE-only devices that never expose CoD at all
    (CoD is a BR/EDR-era inquiry field).
    """
    if not category:
        return None
    c = category.lower()
    if "phone" in c: return 2
    if "computer" in c: return 1
    if "watch" in c: return 7
    if "audio" in c or "headset" in c or "speaker" in c: return 4
    if "hid" in c or "keyboard" in c or "mouse" in c or "joystick" in c or "gamepad" in c: return 5
    return None
