// Normaliza el formulario de creación de empresa a payload JSON
// para el backend (ajusta campos según tu API real)
import type { EmpresaPayload, FormularioEmpresa } from '../typesall/empresa'

// Mapea el formulario del FE al esquema esperado por el backend (EmpresaInSchema)
//
// Nota: el backend (CompanyInSchema) exige `config_json` como objeto (dict),
// no como string JSON. Este helper SIEMPRE devuelve un objeto, incluso si el
// raw del textarea estaba vacío o era inválido. Nunca pases `f.config_json`
// (string) directo al cliente HTTP.
export function buildEmpresaPayload(f: FormularioEmpresa): EmpresaPayload {
  let cfg: Record<string, unknown> | undefined
  const raw = typeof f.config_json === 'string' ? f.config_json.trim() : ''
  if (raw) {
    try {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        cfg = parsed as Record<string, unknown>
      }
    } catch {
      cfg = undefined
    }
  }
  const config_json: Record<string, unknown> = { ...(cfg || {}) }
  return {
    name: f.nombre_empresa?.trim(),
    initial_template: f.startTemplate || undefined,
    tax_id: f.ruc?.trim(),
    phone: f.telefono?.trim(),
    address: f.direccion?.trim(),
    city: f.ciudad?.trim(),
    state: f.provincia?.trim(),
    cp: f.cp?.trim(),
    country: f.pais?.trim(),
    country_code: f.country_code?.trim(),
    website: f.sitio_web?.trim(),
    config_json,
    default_language: f.default_language?.trim(),
    timezone: f.timezone?.trim(),
    currency: f.currency?.trim(),
  }
}

export async function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export async function buildEmpresaCompletaPayload(f: FormularioEmpresa) {
  const company = buildEmpresaPayload(f)
  const admin = {
    first_name: f.nombre_encargado?.trim(),
    last_name: [f.apellido_encargado, f.segundo_apellido_encargado].filter(Boolean).join(' ').trim(),
    email: f.email?.trim(),
    username: f.username?.trim(),
    password: f.password,
  }
  // IDs de módulos via API son UUID; normalizamos a strings para el backend (que ahora acepta UUID/str)
  const modulos = (f.modulos || []).map((m) => (m == null ? '' : String(m).trim()))
  // filtramos vacíos pero mantenemos el tipo string para que Pydantic los convierta a UUID
  .filter((m) => !!m)
  let logo: { data: string; filename?: string; content_type?: string } | undefined
  if (f.logo instanceof File) {
    const data = await fileToDataUrl(f.logo)
    logo = { data, filename: f.logo.name }
  }
  const sectorPayload = f.sector_plantilla_id ? { sector_plantilla_id: f.sector_plantilla_id } : {}
  return { company, admin, modulos, ...(logo ? { logo } : {}), ...sectorPayload }
}
