/**
 * IndexedDB Operations - Cache local de productos y ventas
 */
import { openDB, DBSchema } from 'idb'

interface TPVDatabase extends DBSchema {
  products: {
    key: string
    value: {
      id: string
      name: string
      sku?: string
      price: number
      stock?: number
      tax_rate: number
      image_url?: string
      category?: string
      cached_at: number
    }
  }
  pending_sales: {
    key: string
    value: {
      id: string
      items: any[]
      total: number
      method: string
      created_at: number
      synced: boolean
    }
  }
}

const DB_NAME = 'tpv-db'
const DB_VERSION = 1

async function getDB() {
  return openDB<TPVDatabase>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Products store
      if (!db.objectStoreNames.contains('products')) {
        db.createObjectStore('products', { keyPath: 'id' })
      }
      
      // Pending sales store
      if (!db.objectStoreNames.contains('pending_sales')) {
        const store = db.createObjectStore('pending_sales', { keyPath: 'id' })
        store.createIndex('synced', 'synced')
      }
    },
  })
}

// Products
export async function saveProductsToCache(products: any[]) {
  const db = await getDB()
  const tx = db.transaction('products', 'readwrite')
  
  for (const product of products) {
    await tx.store.put({
      ...product,
      cached_at: Date.now(),
    })
  }
  
  await tx.done
}

export async function getProductsFromCache(): Promise<any[]> {
  const db = await getDB()
  return db.getAll('products')
}

// Pending Sales
export async function savePendingSale(sale: {
  id: string
  items: any[]
  total: number
  method: string
}) {
  const db = await getDB()
  await db.put('pending_sales', {
    ...sale,
    created_at: Date.now(),
    synced: false,
  })
}

export async function getPendingSales() {
  const db = await getDB()
  const index = db.transaction('pending_sales').store.index('synced')
  return index.getAll(IDBKeyRange.only(false))
}

export async function markSaleAsSynced(id: string) {
  const db = await getDB()
  const sale = await db.get('pending_sales', id)
  if (sale) {
    sale.synced = true
    await db.put('pending_sales', sale)
  }
}
