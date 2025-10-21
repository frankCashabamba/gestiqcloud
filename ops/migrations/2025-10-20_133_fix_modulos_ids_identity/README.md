Fix: Ensure auto-increment on modulos_* id columns

Purpose
- Add IDENTITY or sequence defaults to id columns for:
  - public.modulos_modulo
  - public.modulos_empresamodulo
  - public.modulos_moduloasignado

Context
- Some environments skipped baseline defaults, leaving id without auto-increment.
- Inserts then fail with: null value in column "id" violates not-null constraint.

