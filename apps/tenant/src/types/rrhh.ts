export interface Empleado {
  id: string
  tenant_id: string
  sku?: string
  codigo?: string
  name: string
  apellidos: string
  tipo_documento: 'DNI' | 'NIE' | 'PASAPORTE' | 'CEDULA'
  numero_documento: string
  email?: string
  phone?: string
  telefono?: string
  fecha_nacimiento?: string
  fecha_ingreso: string
  fecha_salida?: string
  departamento_id?: string
  puesto?: string
  tipo_contrato: 'indefinido' | 'temporal' | 'practicas' | 'formacion' | 'autonomo'
  jornada: 'completa' | 'parcial' | 'por_horas'
  salario_base: number
  banco?: string
  numero_cuenta?: string
  seguridad_social?: string
  estado: 'activo' | 'baja' | 'suspendido'
  notas?: string
  usuario_id?: string
  created_at: string
  updated_at: string
}

export interface EmpleadoDepartamento {
  id: string
  tenant_id: string
  name: string
  descripcion?: string
  responsable_id?: string
  active: boolean
  created_at: string
}

export interface Vacacion {
  id: string
  tenant_id: string
  empleado_id: string
  fecha_inicio: string
  fecha_fin: string
  dias: number
  tipo: 'vacaciones' | 'baja_medica' | 'permiso' | 'otros'
  estado: 'pendiente' | 'aprobada' | 'rechazada' | 'cancelada'
  motivo?: string
  notas?: string
  aprobado_por?: string
  fecha_aprobacion?: string
  created_at: string
  updated_at: string
}

export interface Nomina {
  id: string
  tenant_id: string
  empleado_id: string
  periodo: string
  salario_base: number
  complementos: number
  horas_extra: number
  deducciones: number
  seguridad_social: number
  irpf: number
  liquido: number
  estado: 'draft' | 'calculated' | 'approved' | 'paid'
  fecha_pago?: string
  notas?: string
  created_at: string
  updated_at: string
}

export interface EmpleadoCreate {
  sku?: string
  codigo?: string
  name: string
  apellidos: string
  tipo_documento: 'DNI' | 'NIE' | 'PASAPORTE' | 'CEDULA'
  numero_documento: string
  email?: string
  phone?: string
  telefono?: string
  fecha_nacimiento?: string
  fecha_ingreso: string
  departamento_id?: string
  puesto?: string
  tipo_contrato: 'indefinido' | 'temporal' | 'practicas' | 'formacion' | 'autonomo'
  jornada: 'completa' | 'parcial' | 'por_horas'
  salario_base: number
  banco?: string
  numero_cuenta?: string
  seguridad_social?: string
  estado?: 'activo' | 'baja' | 'suspendido'
  notas?: string
}

export interface EmpleadoUpdate extends Partial<EmpleadoCreate> {}

export interface VacacionCreate {
  empleado_id: string
  fecha_inicio: string
  fecha_fin: string
  dias?: number
  tipo: 'vacaciones' | 'baja_medica' | 'permiso' | 'otros'
  motivo?: string
  notas?: string
}

export interface VacacionUpdate extends Partial<VacacionCreate> {
  estado?: 'pendiente' | 'aprobada' | 'rechazada' | 'cancelada'
}

export interface RRHHStats {
  total_empleados: number
  empleados_activos: number
  por_departamento: Array<{
    departamento_id: string
    departamento_nombre: string
    cantidad: number
  }>
  por_tipo_contrato: Record<string, number>
  vacaciones_pendientes: number
  nomina_mes_actual: number
}

export interface EmpleadoFilters {
  estado?: string
  departamento_id?: string
  tipo_contrato?: string
  search?: string
}
