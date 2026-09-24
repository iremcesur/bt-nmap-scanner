# LMP Features (Page 0) bit table.
# Source: Bluetooth Core Specification, Vol 2, Part C, Section 3.3 ("Feature Mask
# Definition"), as mirrored in the Linux kernel's LMP_* bit definitions
# (include/net/bluetooth/hci.h). Byte index 0-7 / bit index 0-7 (LSB first) matches
# the raw octets returned by `hcitool info <mac>` after "Features:" / "Features page 0:".
#
# Only named (non-reserved) bits are listed. Reserved/unassigned bits are omitted
# rather than guessed.

LMP_FEATURES_PAGE0 = {
    (0, 0): "three_slot_packets",
    (0, 1): "five_slot_packets",
    (0, 2): "encryption",
    (0, 3): "slot_offset",
    (0, 4): "timing_accuracy",
    (0, 5): "role_switch",
    (0, 6): "hold_mode",
    (0, 7): "sniff_mode",

    (1, 1): "power_control_requests",
    (1, 2): "channel_quality_driven_data_rate",
    (1, 3): "sco_link",
    (1, 4): "hv2_packets",
    (1, 5): "hv3_packets",
    (1, 6): "ulaw_log_synchronous_data",
    (1, 7): "alaw_log_synchronous_data",

    (2, 0): "cvsd_synchronous_data",
    (2, 1): "paging_parameter_negotiation",
    (2, 2): "power_control",
    (2, 3): "transparent_synchronous_data",
    (2, 7): "broadcast_encryption",

    (3, 1): "enhanced_data_rate_acl_2mbps",
    (3, 2): "enhanced_data_rate_acl_3mbps",
    (3, 3): "enhanced_inquiry_scan",
    (3, 4): "interlaced_inquiry_scan",
    (3, 5): "interlaced_page_scan",
    (3, 6): "rssi_with_inquiry_results",
    (3, 7): "extended_sco_link_ev3",

    (4, 0): "ev4_packets",
    (4, 1): "ev5_packets",
    (4, 3): "afh_capable_slave",
    (4, 4): "afh_classification_slave",
    (4, 5): "bredr_not_supported",
    (4, 6): "le_supported_controller",
    (4, 7): "three_slot_enhanced_data_rate_acl",

    (5, 0): "five_slot_enhanced_data_rate_acl",
    (5, 1): "sniff_subrating",
    (5, 2): "pause_encryption",
    (5, 3): "afh_capable_master",
    (5, 4): "afh_classification_master",
    (5, 5): "enhanced_data_rate_esco_2mbps",
    (5, 6): "enhanced_data_rate_esco_3mbps",
    (5, 7): "three_slot_enhanced_data_rate_esco",

    (6, 0): "extended_inquiry_response",
    (6, 1): "simultaneous_le_bredr",
    (6, 3): "secure_simple_pairing",
    (6, 4): "encapsulated_pdu",
    (6, 5): "erroneous_data_reporting",
    (6, 6): "non_flushable_packet_boundary_flag",

    (7, 0): "link_supervision_timeout_changed_event",
    (7, 1): "inquiry_response_tx_power_level",
    (7, 2): "enhanced_power_control",
    (7, 6): "extended_features",
}


def decode_features_bitmap(byte_values):
    """byte_values: list of 8 ints (0-255), MSB-first order as printed by hcitool.
    Returns a dict of feature_name -> bool for every named bit in LMP_FEATURES_PAGE0."""
    result = {}
    for (byte_idx, bit_idx), feature_name in LMP_FEATURES_PAGE0.items():
        if byte_idx < len(byte_values):
            result[feature_name] = bool((byte_values[byte_idx] >> bit_idx) & 1)
    return result
