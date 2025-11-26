#!/usr/bin/env python
"""Test RUC checksum calculation."""

test_rucs = [
    "1713175071001",  # Natural
    "1792146739001",  # Juridical
    "1760001550001",  # Public
]

for ruc in test_rucs:
    weights = [3, 2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3]
    total = sum(int(digit) * weight for digit, weight in zip(ruc[:12], weights))
    check_digit = (11 - (total % 11)) % 11
    print(f"RUC: {ruc}")
    print(f"  Total: {total}")
    print(f"  Calculated check: {check_digit}")
    print(f"  Actual check: {ruc[12]}")
    print(f"  Match: {check_digit == int(ruc[12])}")
    print()
