export type Fichaje = {
  id: string
  empleadoId: string
  fecha: string
  horaInicio: string
  horaFin?: string
  tipo: 'trabajo' | 'descanso' | 'otro'
}

