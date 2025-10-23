# 2025-10-21_135_assign_modules_to_tenants

## Description
Assign default modules to all tenants and their users.

## Changes
- INSERT into `modulos_empresamodulo` for each tenant x module
- INSERT into `modulos_moduloasignado` for each user x module
- Uses ON CONFLICT DO NOTHING to avoid duplicates

## Rollback
Removes all module assignments (use with caution in production).
