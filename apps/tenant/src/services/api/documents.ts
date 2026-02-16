/**
 * Document Storage API Service
 * Connects to Blueprint V2 /api/v1/documents/storage endpoints
 */

import { apiClient } from './client'

export interface DocumentUploadResponse {
  document_id: string
  version_id: string
  version: number
  sha256: string
  is_duplicate: boolean
  file_name: string
  size: number
}

export interface DocumentVersion {
  id: string
  version: number
  file_name: string
  mime: string
  size: number
  sha256: string
  created_at: string
}

export interface Document {
  id: string
  doc_type: string
  source: string
  status: string
  created_at: string
  versions: DocumentVersion[]
}

export interface DocumentListItem {
  id: string
  doc_type: string
  source: string
  status: string
  created_at: string
}

/**
 * Upload a document with SHA256 deduplication
 */
export async function uploadDocument(
  file: File,
  docType: string = 'unknown',
  source: string = 'upload'
): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('doc_type', docType)
  formData.append('source', source)

  const response = await apiClient.post<DocumentUploadResponse>(
    '/api/v1/documents/storage/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )

  return response.data
}

/**
 * List documents with filters
 */
export async function listDocuments(
  filters?: {
    doc_type?: string
    status?: string
    limit?: number
    offset?: number
  }
): Promise<DocumentListItem[]> {
  const response = await apiClient.get<DocumentListItem[]>(
    '/api/v1/documents/storage',
    {
      params: {
        limit: filters?.limit || 50,
        offset: filters?.offset || 0,
        ...(filters?.doc_type && { doc_type: filters.doc_type }),
        ...(filters?.status && { status: filters.status }),
      },
    }
  )

  return response.data
}

/**
 * Get document with all versions
 */
export async function getDocument(documentId: string): Promise<Document> {
  const response = await apiClient.get<Document>(
    `/api/v1/documents/storage/${documentId}`
  )

  return response.data
}
