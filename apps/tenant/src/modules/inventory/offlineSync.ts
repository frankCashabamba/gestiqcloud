/**
 * Inventory Offline Sync Adapter
 *
 * Handles synchronization of stock data.
 * - Stock items are read-cached for offline access
 * - Stock moves are create-only (append-only)
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities } from '@/lib/offlineStore'
import { listStockItems, createStockMove } from './services'
import type { StockItem } from './services'

export const InventoryAdapter: SyncAdapter = {
  entity: 'inventory',
  canSyncOffline: true,

  async fetchAll(): Promise<StockItem[]> {
    try {
      return await listStockItems()
    } catch (error) {
      console.error('Failed to fetch stock items:', error)
      return []
    }
  },

  async create(data: any): Promise<any> {
    const move = await createStockMove(data)
    await storeEntity('inventory', String(move.id ?? Date.now()), move, 'synced', 1)
    return move
  },

  async update(_id: string, _data: any): Promise<any> {
    throw new Error('Stock items are updated via stock moves')
  },

  async delete(_id: string): Promise<void> {
    throw new Error('Stock items cannot be deleted directly')
  },

  async getRemoteVersion(_id: string): Promise<number> {
    return 0
  },

  detectConflict(_local: any, _remote: any): boolean {
    return false
  }
}

export function registerInventorySyncAdapter() {
  getSyncManager().registerAdapter(InventoryAdapter)
}

export async function syncStockToOffline(items: StockItem[]): Promise<void> {
  for (const item of items) {
    await storeEntity('inventory', String(item.id), item, 'synced', Date.now())
  }
}

export async function getOfflineStock(): Promise<StockItem[]> {
  const items = await listEntities('inventory')
  return items.map(i => i.data)
}
