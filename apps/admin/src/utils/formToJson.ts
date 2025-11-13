// Normaliza el formulario de creación de empresa a payload JSON
// para el backend (ajusta campos según tu API real)
import type { FormularioEmpresa } from '../typesall/empresa'

// Mapea el formulario del FE al esquema esperado por el backend (EmpresaInSchema)
export function buildEmpresaPayload(f: FormularioEmpresa) {
  let cfg: any = undefined
  if (f.config_json && f.config_json.trim()) {
    try { cfg = JSON.parse(f.config_json) } catch { cfg = undefined }
  }
  const extra: any = {}
  if (f.tipo_empresa) extra.tipo_empresa = f.tipo_empresa
  if (f.tipo_negocio) extra.tipo_negocio = f.tipo_negocio
  const config_json = { ...(cfg || {}), ...extra }
  return {
    name: f.nombre_empresa?.trim(),
    initial_template: f.plantilla_inicio || 'cliente',
    tax_id: f.ruc?.trim(),
    phone: f.telefono?.trim(),
    address: f.direccion?.trim(),
    city: f.ciudad?.trim(),
    state: f.provincia?.trim(),
    cp: f.cp?.trim(),
    country: f.pais?.trim(),
    website: f.sitio_web?.trim(),
    primary_color: f.color_primario || '#4f46e5',
    config_json,
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
  const empresa = buildEmpresaPayload(f)
  const admin = {
    nombre_encargado: f.nombre_encargado,
    apellido_encargado: f.apellido_encargado,
    email: f.email,
    username: f.username,
    password: f.password,
  }
  const modulos = f.modulos || []
  let logo: { data: string; filename?: string; content_type?: string } | undefined
  if (f.logo instanceof File) {
    const data = await fileToDataUrl(f.logo)
    logo = { data, filename: f.logo.name }
  }
  const sectorPayload = f.sector_plantilla_id ? { sector_plantilla_id: f.sector_plantilla_id } : {}
  return { empresa, admin, modulos, ...(logo ? { logo } : {}), ...sectorPayload }
}
