/**
 * Products Offline Sync Adapter
 *
 * Handles synchronization of product data
 * - Products can be created, updated, deleted
 * - Conflict detection on price and stock changes
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import * as productServices from './productsApi'
import type { Producto } from './types'

export const ProductsAdapter: SyncAdapter = {
  entity: 'product',
  canSyncOffline: true,

  async fetchAll(): Promise<Producto[]> {
    try {
      return await productServices.listProductos()
    } catch (error) {
      console.error('Failed to fetch products:', error)
      return []
    }
  },

  async create(data: any): Promise<Producto> {
    const product = await productServices.createProducto(data)
    const remoteVersion = product.updated_at ? new Date(product.updated_at).getTime() : Date.now()
    await storeEntity('product', String(product.id), product, 'synced', remoteVersion)
    return product
  },

  async update(id: string, data: any): Promise<Producto> {
    const product = await productServices.updateProducto(id, data)
    const remoteVersion = product.updated_at ? new Date(product.updated_at).getTime() : Date.now()
    await storeEntity('product', String(id), product, 'synced', remoteVersion)
    return product
  },

  async delete(id: string): Promise<void> {
    try {
      await productServices.removeProducto(id)
      await storeEntity('product', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      // If offline or server fails, queue deletion to ensure it is processed later
      await queueDeletion('product', id)
      console.warn('[offline] Queued product deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const product = await productServices.getProducto(id)
      // Use updated_at timestamp as version indicator
      return product?.updated_at ? new Date(product.updated_at).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    // Conflict if critical fields differ
    if (!remote) return false

    return local.price !== remote.price ||
           local.stock !== remote.stock ||
           local.name !== remote.name ||
           local.active !== remote.active
  }
}

export function registerProductsSyncAdapter() {
  getSyncManager().registerAdapter(ProductsAdapter)
  console.log('✅ Products sync adapter registered')
}

/**
 * Cache products locally for offline access
 */
export async function syncProductsToOffline(products: Producto[]) {
  for (const product of products) {
    const remoteVersion = product.updated_at ? new Date(product.updated_at).getTime() : Date.now()
    await storeEntity('product', product.id, product, 'synced', remoteVersion)
  }
}

/**
 * Get locally cached products
 */
export async function getOfflineProducts(): Promise<Producto[]> {
  const items = await listEntities('product')
  return items.map(i => i.data)
}

/**
 * Get products with pending changes
 */
export async function getProductsWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('product')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
