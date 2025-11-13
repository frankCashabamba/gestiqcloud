Fix payments.factura_id FK to reference invoices(id)

Summary
- Drops any existing FK from payments.factura_id → facturas(id).
- Adds FK payments.factura_id → invoices(id).
- Ensures index on payments.factura_id exists.

Notes
- Safe to run multiple times (guards with IF/EXISTS logic).
- Down migration restores FK to facturas(id) only if that table exists.
