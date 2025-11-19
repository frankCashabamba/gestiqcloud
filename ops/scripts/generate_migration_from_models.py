#!/usr/bin/env python3
"""
Generate SQL migration from SQLAlchemy models.
This script inspects all models and generates CREATE TABLE statements.
"""

import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from sqlalchemy.schema import CreateTable

from app.config.database import Base


def generate_migration():
    """Generate SQL from all registered models."""

    # Get all table metadata
    metadata = Base.metadata

    sql_statements = []

    # Add header
    sql_statements.append("""-- =====================================================
-- Consolidated Schema Migration
-- Auto-generated from SQLAlchemy models
-- =====================================================

BEGIN;

-- Drop all existing tables in reverse dependency order
DROP TABLE IF EXISTS auth_refresh_token;
DROP TABLE IF EXISTS auth_refresh_family;
DROP TABLE IF EXISTS crm_activities;
DROP TABLE IF EXISTS crm_opportunities;
DROP TABLE IF EXISTS crm_leads;
DROP TABLE IF EXISTS auth_audit;
DROP TABLE IF EXISTS company_user_roles;
DROP TABLE IF EXISTS assigned_modules;
DROP TABLE IF EXISTS company_modules;
DROP TABLE IF EXISTS modules;
DROP TABLE IF EXISTS store_credit_events;
DROP TABLE IF EXISTS store_credits;
DROP TABLE IF EXISTS payroll_concepts;
DROP TABLE IF EXISTS payroll_templates;
DROP TABLE IF EXISTS payrolls;
DROP TABLE IF EXISTS vacations;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS sii_batch_items;
DROP TABLE IF EXISTS sii_batches;
DROP TABLE IF EXISTS sri_submissions;
DROP TABLE IF EXISTS einv_credentials;
DROP TABLE IF EXISTS pos_payments;
DROP TABLE IF EXISTS pos_receipt_lines;
DROP TABLE IF EXISTS pos_receipts;
DROP TABLE IF EXISTS pos_shifts;
DROP TABLE IF EXISTS pos_registers;
DROP TABLE IF EXISTS doc_series;
DROP TABLE IF EXISTS internal_transfers;
DROP TABLE IF EXISTS bank_transactions;
DROP TABLE IF EXISTS bank_accounts;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS invoices_temp;
DROP TABLE IF EXISTS workshop_lines;
DROP TABLE IF EXISTS bakery_lines;
DROP TABLE IF EXISTS invoice_lines;
DROP TABLE IF EXISTS purchase_lines;
DROP TABLE IF EXISTS purchases;
DROP TABLE IF EXISTS production_order_lines;
DROP TABLE IF EXISTS production_orders;
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS sales_order_items;
DROP TABLE IF EXISTS sales_orders;
DROP TABLE IF EXISTS deliveries;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS supplier_addresses;
DROP TABLE IF EXISTS supplier_contacts;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS inventory_alert_history;
DROP TABLE IF EXISTS inventory_alert_configs;
DROP TABLE IF EXISTS stock_moves;
DROP TABLE IF EXISTS stock_items;
DROP TABLE IF EXISTS warehouses;
DROP TABLE IF EXISTS cash_closings;
DROP TABLE IF EXISTS cash_movements;
DROP TABLE IF EXISTS bank_movements;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS import_lineage;
DROP TABLE IF EXISTS import_item_corrections;
DROP TABLE IF EXISTS import_ocr_jobs;
DROP TABLE IF EXISTS import_mappings;
DROP TABLE IF EXISTS import_attachments;
DROP TABLE IF EXISTS import_items;
DROP TABLE IF EXISTS import_batches;
DROP TABLE IF EXISTS import_column_mappings;
DROP TABLE IF EXISTS ui_templates;
DROP TABLE IF EXISTS sector_field_defaults;
DROP TABLE IF EXISTS tenant_field_configs;
DROP TABLE IF EXISTS inventory_settings;
DROP TABLE IF EXISTS company_settings;
DROP TABLE IF EXISTS tenant_settings;
DROP TABLE IF EXISTS auth_user;
DROP TABLE IF EXISTS company_roles;
DROP TABLE IF EXISTS company_user_roles;
DROP TABLE IF EXISTS company_users;
DROP TABLE IF EXISTS user_profiles;
DROP TABLE IF EXISTS company_categories;
DROP TABLE IF EXISTS global_action_permissions;
DROP TABLE IF EXISTS currencies;
DROP TABLE IF EXISTS languages;
DROP TABLE IF EXISTS locales;
DROP TABLE IF EXISTS timezones;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_categories;
DROP TABLE IF EXISTS clients;
DROP TABLE IF EXISTS import_audits;
DROP TABLE IF EXISTS business_categories;
DROP TABLE IF EXISTS business_types;
DROP TABLE IF EXISTS base_roles;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS tenants;

-- =====================================================
-- CREATE ALL TABLES FROM MODELS
-- =====================================================

""")

    # Generate CREATE TABLE for each table
    for table_name, table in sorted(metadata.tables.items()):
        try:
            create_sql = str(
                CreateTable(table).compile(compile_kwargs={"literal_binds": True})
            )
            sql_statements.append(f"-- Table: {table_name}")
            sql_statements.append(create_sql + ";\n")
        except Exception as e:
            print(f"Warning: Could not generate SQL for {table_name}: {e}")

    sql_statements.append("\nCOMMIT;")

    return "\n".join(sql_statements)


if __name__ == "__main__":
    sql = generate_migration()
    print(sql)
