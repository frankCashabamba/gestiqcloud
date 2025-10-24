export function formToFormData(obj: Record<string, any>) {
  const fd = new FormData()
  Object.entries(obj || {}).forEach(([k, v]) => {
    if (v === undefined || v === null) fd.append(k, '')
    else fd.append(k, v as any)
  })
  return fd
}

