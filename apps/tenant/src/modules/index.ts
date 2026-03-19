// GESTIQCLOUD MODULES - Complete system
import { manifest as pos } from './pos/manifest'
import { manifest as productions } from './productions/manifest'
import { inventoryManifest } from './inventory/manifest'
import { manifest as sales } from './sales/manifest'
import { manifest as purchases } from './purchases/manifest'
import { manifest as suppliers } from './suppliers/manifest'
import { manifest as expenses } from './expenses/manifest'
import { manifest as users } from './users/manifest'
import { productsManifest } from './products/manifest'
import { crmManifest } from './crm/manifest'
import { manifest as reports } from './reports/manifest'
import { manifest as templates } from './templates/manifest'
import { manifest as webhooks } from './webhooks/manifest'
import { manifest as einvoicing } from './einvoicing/manifest'
import { manifest as reconciliation } from './reconciliation/manifest'
import { manifest as notifications } from './notifications/manifest'
// OLD IMPORTER DISABLED (renamed to _old_importer)
// import { manifest as importer } from './importer/manifest'
import { manifest as importador } from './importador/manifest'

export const MODULES = [
  productsManifest,    // 0 - Products
  inventoryManifest,   // 1 - Inventory
  pos,                 // 2 - Point of Sale
  productions,         // 3 - Recipes and Costs
  sales,               // 4 - Sales and Reports
  purchases,           // 5 - Supply Purchases
  suppliers,           // 6 - Suppliers
  expenses,            // 7 - Daily Expenses
  users,               // 8 - Users
  crmManifest,         // 9 - CRM
  reports,             // 10 - Reports
  templates,           // 11 - Templates
  webhooks,            // 13 - Webhooks
  einvoicing,          // 14 - Electronic Invoicing (stub)
  reconciliation,      // 15 - Bank Reconciliation (stub)
  notifications,       // 16 - Notifications
  // importer,            // 17 - Importer (disabled)
  importador,            // 18 - Universal Accounting Importer v1.1
]

export type ModuleManifest = typeof pos
