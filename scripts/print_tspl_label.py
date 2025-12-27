#!/usr/bin/env python3
"""
Helper script for the P1_4E7D label printer (TSPL / CPCL) to print a single product label.

Install dependencies with:

    pip install pyserial

Usage example:

    python scripts/print_tspl_label.py --port COM5 \
      --name "ADORNO DE FLORES" \
      --price "4.80 €" \
      --barcode BT8524 \
      --copies 2 \
      --dry-run

When run without `--dry-run`, the script opens the requested serial port (Bluetooth COM5
from pairing wizard) and streams plain TSPL commands to draw the name, barcode and price
on a 50x40mm label for the P1_4E7D printer.
"""

"""
CLI helper for printing a TSPL label via the backend module so the action can be
reused by the frontend calling `POST /tenant/printing/labels`.
"""
import argparse
import logging

from apps.backend.app.modules.printing.tspl import (
    LabelConfig,
    ProductLabel,
    build_tspl_payload,
    send_to_printer,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a TSPL product label via Bluetooth COM port.")
    parser.add_argument("--port", required=True, help="Serial port for the printer (COM5, COM7, ...).")
    parser.add_argument("--name", required=True, help="Product name to print.")
    parser.add_argument("--barcode", required=True, help="Barcode value for the label.")
    parser.add_argument("--price", help="Price text to show below the barcode.")
    parser.add_argument("--copies", type=int, default=1, help="Number of copies to print.")
    parser.add_argument("--dry-run", action="store_true", help="Print the TSPL commands without sending them.")
    parser.add_argument("--baudrate", type=int, default=9600, help="Serial port baud rate (default 9600).")
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR).")

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(message)s")

    label = ProductLabel(name=args.name, barcode=args.barcode, price=args.price, copies=args.copies)
    payload = build_tspl_payload(label, LabelConfig())

    logging.debug("TSPL payload:\n%s", payload)

    if args.dry_run:
        print(payload)
        return

    logging.info("Sending %d copies to %s at %d baud…", label.copies, args.port, args.baudrate)
    send_to_printer(args.port, payload, baudrate=args.baudrate)
    logging.info("✅ Enviado.")


if __name__ == "__main__":
    main()
