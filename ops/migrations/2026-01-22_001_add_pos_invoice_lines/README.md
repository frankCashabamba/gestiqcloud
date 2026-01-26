# Migration: Add `pos_invoice_lines` table for POSLine polymorphic model

## Purpose

- Support SQLAlchemy polymorphic inheritance for `InvoiceLine` base model
- Map `invoice_lines.sector='pos'` records to `POSLine` model
- Create `pos_invoice_lines` table for joined table inheritance

## Problem Solved

Database has `invoice_lines` records with `sector='pos'` but Python models didn't have `POSLine` class.
This caused: `AssertionError: No such polymorphic_identity 'pos' is defined`

## Changes

1. Creates `pos_invoice_lines` table (joined table inheritance from `invoice_lines`)
2. Creates index on `pos_receipt_line_id` for FK lookups
3. Safe on existing databases: uses `IF NOT EXISTS` and conditional table existence check

## Rollback

If needed, the `down.sql` script drops the table and indexes.

## Notes

- This migration is idempotent (safe to apply multiple times)
- No data migration required (existing 'pos' records in `invoice_lines` will work automatically)
- Optional: migrate existing data to `pos_invoice_lines` using manual SQL if needed
