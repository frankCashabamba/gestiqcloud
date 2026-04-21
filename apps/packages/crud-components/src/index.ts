/**
 * CRUD Components - Componentes genéricos reutilizables
 */

export { GenericList } from './GenericList'
export { GenericForm } from './GenericForm'
export { GenericTable } from './GenericTable'
export { GenericModal } from './GenericModal'

export type { 
  GenericListProps, 
  ColumnConfig, 
  ActionConfig,
  SortConfig 
} from './GenericList'

export type { 
  GenericFormProps, 
  FieldConfig,
  FormFieldType 
} from './GenericForm'

export type { 
  GenericTableProps,
  TableColumn,
  TableAction 
} from './GenericTable'

export type { 
  GenericModalProps 
} from './GenericModal'
