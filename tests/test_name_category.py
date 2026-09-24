"""
Regression tests for infer_device_category_from_name.

These exist because the evidence chain found the defect they cover. The
single-table version resolved by first-match-wins over dict order, so an
accessory carrying a brand-family name ("Galaxy Buds2") matched "galaxy"
(Phone) before "buds" (Audio). The CoD-vs-name pair disagreed with
Class-of-Device on four archived scans of that device, which is the mechanism
working as intended - but the derivation was wrong and is now two-tiered:
product-type words resolve first, brand-family words only as a fallback.
"""

import _runner_bootstrap  # noqa: F401  (sys.path setup)
import advanced_nmap_scanner as scanner


def test_product_type_beats_brand_family():
    """The defect itself: an accessory whose name also carries a phone brand."""
    assert scanner.infer_device_category_from_name("Galaxy Buds2 (C7D2)") == 4
    assert scanner.infer_device_category_from_name("Galaxy Watch4") == 7


def test_brand_family_still_resolves_when_nothing_more_specific_matches():
    """The fallback tier must keep working - a bare brand name is still a phone."""
    assert scanner.infer_device_category_from_name("Galaxy S21") == 2
    assert scanner.infer_device_category_from_name("Pixel 7") == 2


def test_unambiguous_names_are_unaffected():
    assert scanner.infer_device_category_from_name("iPhone") == 2
    assert scanner.infer_device_category_from_name("MacBook Pro") == 1
    assert scanner.infer_device_category_from_name("AirPods") == 4
    assert scanner.infer_device_category_from_name("Logitech Mouse") == 5


def test_no_match_and_empty_input_return_none():
    """None means 'this signal is unavailable', which the chain treats as a
    missing precondition rather than as a category - so a wrong guess here is
    worse than no answer."""
    assert scanner.infer_device_category_from_name("realme 11 Pro+ 5G") is None
    assert scanner.infer_device_category_from_name("") is None
    assert scanner.infer_device_category_from_name(None) is None


def test_non_ascii_names_still_match_ascii_keywords():
    """
    A plain .lower() silently dropped these. Turkish dotted capital I (U+0130)
    lower-cases to "i" plus a combining dot above, so a device advertising as
    "Irem Ipad" with a Turkish capital folded to something that never matched
    "ipad" and contributed no name signal at all. Device names are user-chosen
    free text; non-ASCII is normal, not an edge case.
    """
    assert scanner.infer_device_category_from_name("\u0130rem \u0130pad") == 1
    assert scanner.infer_device_category_from_name("\u0130rem iPhone") == 2
    assert scanner.infer_device_category_from_name("\u0130rem (AirPods)") == 4
    # accented forms of the same keywords must fold identically
    assert scanner.infer_device_category_from_name("W\u00c4TCH") == 7


def test_ipad_maps_to_computer_as_measured():
    """
    Empirically grounded rather than assumed: a paired iPad in our own device
    set reports CoD 0x006a0110, major class 1 (Computer). A guessed mapping
    would manufacture conflicts in the CoD-vs-name pair instead of finding them.
    """
    assert scanner.infer_device_category_from_name("iPad Pro") == 1
    assert scanner.decode_cod_major_class("0x006a0110") == 1


def test_no_keyword_appears_in_both_tiers():
    """A word in both tiers would make the tier split meaningless."""
    specific = {kw for kws in scanner.NAME_CATEGORY_KEYWORDS_SPECIFIC.values() for kw in kws}
    brand = {kw for kws in scanner.NAME_CATEGORY_KEYWORDS_BRAND_FAMILY.values() for kw in kws}
    assert specific & brand == set()


if __name__ == "__main__":
    from _runner import run

    raise SystemExit(run())
