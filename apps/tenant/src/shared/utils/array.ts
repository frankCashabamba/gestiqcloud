export function ensureArray<T = unknown>(data: any): T[] {
  if (Array.isArray(data)) return data as T[]
  if (data && Array.isArray((data as any).items)) return (data as any).items as T[]
  return []
}
