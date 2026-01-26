/**
 * Helpers to queue invoice operations for offline sync.
 */
import { storeEntity, queueDeletion, EntityType } from '@/lib/offlineStore'
import type { InvoiceCreate } from './services'

const entity: EntityType = 'invoice'

export async function queueInvoiceForSync(
  data: InvoiceCreate | Partial<InvoiceCreate> & { id?: string },
  op: 'create' | 'update' = 'create'
): Promise<string> {
  const id = data?.id ? String(data.id) : `invoice-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`

  await storeEntity(entity, id, { ...data, _op: op }, 'pending')
  return id
}

export async function queueInvoiceDeletion(id: string) {
  await queueDeletion(entity, id)
}
