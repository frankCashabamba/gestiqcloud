import { manifest as clientes } from './clientes/manifest'
import { manifest as pos } from './pos/manifest'

export const MODULES = [pos, clientes]

export type ModuleManifest = typeof clientes

