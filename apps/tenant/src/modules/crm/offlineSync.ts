/**
 * CRM/Leads Offline Sync Adapter
 *
 * Synchronizes leads with offline support.
 * - Full CRUD with conflict detection
 */

import { SyncAdapter, getSyncManager } from '@/lib/syncManager'
import { storeEntity, listEntities, queueDeletion } from '@/lib/offlineStore'
import { listLeads, getLead, createLead, updateLead, deleteLead } from './services'
import type { Lead } from './services'

export const LeadsAdapter: SyncAdapter = {
  entity: 'lead',
  canSyncOffline: true,

  async fetchAll(): Promise<Lead[]> {
    try {
      return await listLeads()
    } catch (error) {
      console.error('Failed to fetch leads:', error)
      return []
    }
  },

  async create(data: any): Promise<Lead> {
    const lead = await createLead(data)
    const remoteVersion = (lead as any)?.updated_at ? new Date((lead as any).updated_at as string).getTime() : Date.now()
    await storeEntity('lead', String(lead.id), lead, 'synced', remoteVersion)
    return lead
  },

  async update(id: string, data: any): Promise<Lead> {
    const lead = await updateLead(id, data)
    const remoteVersion = (lead as any)?.updated_at ? new Date((lead as any).updated_at as string).getTime() : Date.now()
    await storeEntity('lead', String(id), lead, 'synced', remoteVersion)
    return lead
  },

  async delete(id: string): Promise<void> {
    try {
      await deleteLead(id)
      await storeEntity('lead', String(id), { _deleted: true, _op: 'delete' }, 'synced', Date.now())
    } catch (error) {
      await queueDeletion('lead', id)
      console.warn('[offline] Queued lead deletion for later sync:', id)
    }
  },

  async getRemoteVersion(id: string): Promise<number> {
    try {
      const lead = await getLead(id)
      const timestamp = (lead as any)?.updated_at ?? (lead as any)?.created_at
      return timestamp ? new Date(timestamp as string).getTime() : 0
    } catch {
      return 0
    }
  },

  detectConflict(local: any, remote: any): boolean {
    if (!remote) return false
    return local.status !== remote.status ||
           local.stage !== remote.stage ||
           local.value !== remote.value ||
           local.assigned_to !== remote.assigned_to
  }
}

export function registerLeadsSyncAdapters() {
  getSyncManager().registerAdapter(LeadsAdapter)
}

export async function getLeadsWithPendingChanges(): Promise<any[]> {
  const items = await listEntities('lead')
  return items
    .filter(i => i.syncStatus === 'pending')
    .map(i => ({ ...i.data, _id: i.id, _status: i.syncStatus }))
}
