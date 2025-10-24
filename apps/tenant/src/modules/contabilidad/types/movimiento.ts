export type Apunte = {
  cuenta: string
  descripcion: string
  debe: number
  haber: number
}

export type Asiento = {
  id: string | number
  fecha: string
  concepto: string
  apuntes: Apunte[]
}

