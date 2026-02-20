import { apiFetch } from '../../../lib/http'

export type ImportAliasDocType =
  | 'invoices'
  | 'bank_transactions'
  | 'products'
  | 'generic'
  | 'expenses'

export type ImportAliasField = {
  field: string
  aliases: string[]
  field_type?: string | null
  required?: boolean
}

export async function getImportFieldAliases(docType: ImportAliasDocType, authToken?: string) {
  return apiFetch<{ doc_type: string; module: string; fields: ImportAliasField[] }>(
    `/api/v1/tenant/imports/field-aliases?doc_type=${encodeURIComponent(docType)}`,
    { authToken },
  )
}

export async function saveImportFieldAliases(
  docType: ImportAliasDocType,
  fields: ImportAliasField[],
  authToken?: string,
) {
  return apiFetch<{ ok: boolean; doc_type: string; module: string }>(
    '/api/v1/tenant/imports/field-aliases',
    {
      method: 'PUT',
      authToken,
      body: JSON.stringify({
        doc_type: docType,
        fields,
      }),
    },
  )
}

