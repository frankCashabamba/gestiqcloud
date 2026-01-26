import api from '../shared/api/client';

export type POSBackfillResult = {
  ok: boolean;
  receipt_id: string;
  documents_created?: Record<string, any>;
};

export type POSBackfillCandidate = {
  receipt_id: string;
  number: string;
  paid_at: string | null;
  gross_total: number;
  tax_total: number;
  currency: string | null;
  tenant_currency?: string | null;
  currency_mismatch?: boolean;
  invoice_id: string | null;
  sales_order_id: string | null;
  missing_invoice: boolean;
  missing_sale: boolean;
};

export type POSBackfillCandidatesResponse = {
  ok: boolean;
  tenant_id: string;
  tenant_currency?: string | null;
  missing: 'any' | 'invoice' | 'sale' | string;
  limit: number;
  offset: number;
  items: POSBackfillCandidate[];
};

export async function backfillPosReceiptDocuments(
  tenantId: string,
  receiptId: string
): Promise<POSBackfillResult> {
  const response = await api.post(
    `/v1/admin/companies/${tenantId}/pos/receipts/${receiptId}/backfill_documents`
  );
  return response.data;
}

export async function listPosBackfillCandidates(
  tenantId: string,
  params?: {
    missing?: 'any' | 'invoice' | 'sale';
    since?: string;
    until?: string;
    limit?: number;
    offset?: number;
  }
): Promise<POSBackfillCandidatesResponse> {
  const response = await api.get(
    `/v1/admin/companies/${tenantId}/pos/receipts/backfill_candidates`,
    { params }
  );
  return response.data;
}
