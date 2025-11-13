export type Apunte = {
  cuenta: string
  description: string
  debe: number
  haber: number
}

export type Asiento = {
  id: string | number
  fecha: string
  concepto: string
  apuntes: Apunte[]
}
