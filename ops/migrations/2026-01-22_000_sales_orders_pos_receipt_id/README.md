# Migration: add `pos_receipt_id` to `sales_orders`

Purpose:
- Link CRM sales orders (`sales_orders`) to POS receipts (`pos_receipts`) for traceability and idempotent creation during POS checkout.

Notes:
- Safe to apply on existing databases: uses `IF NOT EXISTS`.
- Includes an index and a partial unique index to prevent duplicate orders per POS receipt per tenant.

