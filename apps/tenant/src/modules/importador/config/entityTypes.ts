/**
 * Configuración de tipos de entidades importables
 * Módulo universal de importación para todos los tenants y plantillas
 */

export type EntityType =
  | 'productos'
  | 'clientes'
  | 'proveedores'
  | 'inventario'
  | 'ventas'
  | 'compras'
  | 'facturas'
  | 'gastos'
  | 'empleados'

export type ImportFieldConfig = {
  /** Nombre del campo en el sistema */
  field: string
  /** Nombre(s) común(es) en Excel */
  aliases: string[]
  /** ¿Es obligatorio? */
  required: boolean
  /** Tipo de dato esperado */
  type: 'string' | 'number' | 'date' | 'boolean' | 'email' | 'url'
  /** Validación adicional */
  validation?: (value: any) => boolean
  /** Transformación antes de guardar */
  transform?: (value: any) => any
  /** Descripción para el usuario */
  description?: string
}

export type EntityTypeConfig = {
  /** Tipo de entidad */
  type: EntityType
  /** Nombre legible */
  label: string
  /** Icono (emoji o clase CSS) */
  icon: string
  /** Endpoint del backend */
  endpoint: string
  /** Configuración de campos */
  fields: ImportFieldConfig[]
  /** ¿Requiere validación de duplicados? */
  checkDuplicates?: boolean
  /** Campo(s) para identificar duplicados */
  duplicateKeys?: string[]
  /** Plantillas que pueden usar este tipo */
  allowedTemplates?: string[]
}

/**
 * Configuración de todos los tipos de entidades importables
 */
export const ENTITY_TYPES: Record<EntityType, EntityTypeConfig> = {
  productos: {
    type: 'productos',
    label: 'Productos',
    icon: '📦',
    endpoint: '/api/v1/imports/batches',
    checkDuplicates: true,
    duplicateKeys: ['sku', 'codigo', 'codigo_barras'],
    fields: [
      {
        field: 'nombre',
        aliases: ['nombre', 'producto', 'descripcion', 'description', 'name'],
        required: true,
        type: 'string',
        description: 'Nombre del producto',
      },
      {
        field: 'sku',
        aliases: ['sku', 'codigo', 'code', 'ref', 'referencia'],
        required: true,
        type: 'string',
        description: 'Código único del producto',
      },
      {
        field: 'codigo_barras',
        aliases: ['codigo_barras', 'barcode', 'ean', 'ean13', 'upc'],
        required: false, // No obligatorio - se puede generar automáticamente
        type: 'string',
        description: 'Código de barras (se genera automáticamente si falta)',
        transform: (v) => v?.toString().trim() || '', // Normalizar vacíos
      },
      {
        field: 'precio_venta',
        aliases: ['precio', 'precio_venta', 'pvp', 'price', 'sale_price'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Precio de venta',
      },
      {
        field: 'precio_compra',
        aliases: ['costo', 'precio_compra', 'cost', 'purchase_price'],
        required: false,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Precio de compra/costo',
      },
      {
        field: 'stock',
        aliases: ['stock', 'cantidad', 'qty', 'quantity', 'existencias'],
        required: false,
        type: 'number',
        transform: (v) => parseInt(String(v).replace(/[^\d]/g, ''), 10),
        description: 'Cantidad en stock',
      },
      {
        field: 'categoria',
        aliases: ['categoria', 'category', 'tipo', 'type', 'grupo'],
        required: false,
        type: 'string',
        description: 'Categoría del producto',
      },
      {
        field: 'proveedor',
        aliases: ['proveedor', 'supplier', 'fabricante', 'marca', 'brand'],
        required: false,
        type: 'string',
        description: 'Proveedor o marca',
      },
      {
        field: 'iva',
        aliases: ['iva', 'tax', 'impuesto', 'vat'],
        required: false,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.]/g, '')),
        description: 'IVA (porcentaje)',
      },
      {
        field: 'activo',
        aliases: ['activo', 'active', 'enabled', 'estado', 'status'],
        required: false,
        type: 'boolean',
        transform: (v) => {
          const val = String(v).toLowerCase()
          return val === 'true' || val === '1' || val === 'si' || val === 'sí' || val === 'yes'
        },
        description: '¿Está activo?',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller', 'default'],
  },

  clientes: {
    type: 'clientes',
    label: 'Clientes',
    icon: '👥',
    endpoint: '/api/v1/imports/batches',
    checkDuplicates: true,
    duplicateKeys: ['email', 'documento', 'telefono'],
    fields: [
      {
        field: 'nombre',
        aliases: ['nombre', 'name', 'razon_social', 'company'],
        required: true,
        type: 'string',
        description: 'Nombre o razón social',
      },
      {
        field: 'documento',
        aliases: ['documento', 'nif', 'cif', 'dni', 'ruc', 'cedula', 'tax_id'],
        required: false,
        type: 'string',
        description: 'Documento de identidad',
      },
      {
        field: 'email',
        aliases: ['email', 'correo', 'mail', 'e-mail'],
        required: false,
        type: 'email',
        validation: (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v),
        description: 'Email',
      },
      {
        field: 'telefono',
        aliases: ['telefono', 'phone', 'movil', 'celular', 'tel'],
        required: false,
        type: 'string',
        description: 'Teléfono',
      },
      {
        field: 'direccion',
        aliases: ['direccion', 'address', 'calle'],
        required: false,
        type: 'string',
        description: 'Dirección',
      },
      {
        field: 'ciudad',
        aliases: ['ciudad', 'city', 'localidad'],
        required: false,
        type: 'string',
        description: 'Ciudad',
      },
      {
        field: 'codigo_postal',
        aliases: ['cp', 'codigo_postal', 'postal_code', 'zip'],
        required: false,
        type: 'string',
        description: 'Código postal',
      },
      {
        field: 'pais',
        aliases: ['pais', 'country'],
        required: false,
        type: 'string',
        description: 'País',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller', 'default'],
  },

  proveedores: {
    type: 'proveedores',
    label: 'Proveedores',
    icon: '🏭',
    endpoint: '/api/v1/imports/batches',
    checkDuplicates: true,
    duplicateKeys: ['documento', 'nombre'],
    fields: [
      {
        field: 'nombre',
        aliases: ['nombre', 'name', 'razon_social', 'company'],
        required: true,
        type: 'string',
        description: 'Nombre del proveedor',
      },
      {
        field: 'documento',
        aliases: ['documento', 'nif', 'cif', 'ruc', 'tax_id'],
        required: true,
        type: 'string',
        description: 'Documento fiscal',
      },
      {
        field: 'email',
        aliases: ['email', 'correo', 'mail'],
        required: false,
        type: 'email',
        validation: (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v),
        description: 'Email',
      },
      {
        field: 'telefono',
        aliases: ['telefono', 'phone', 'tel'],
        required: false,
        type: 'string',
        description: 'Teléfono',
      },
      {
        field: 'direccion',
        aliases: ['direccion', 'address'],
        required: false,
        type: 'string',
        description: 'Dirección',
      },
      {
        field: 'condiciones_pago',
        aliases: ['condiciones_pago', 'pago', 'payment_terms'],
        required: false,
        type: 'string',
        description: 'Condiciones de pago',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller', 'default'],
  },

  inventario: {
    type: 'inventario',
    label: 'Inventario',
    icon: '📊',
    endpoint: '/api/v1/imports/batches',
    fields: [
      {
        field: 'sku',
        aliases: ['sku', 'codigo', 'producto_id'],
        required: true,
        type: 'string',
        description: 'SKU del producto',
      },
      {
        field: 'cantidad',
        aliases: ['cantidad', 'stock', 'qty', 'quantity'],
        required: true,
        type: 'number',
        transform: (v) => parseInt(String(v).replace(/[^\d]/g, ''), 10),
        description: 'Cantidad en inventario',
      },
      {
        field: 'ubicacion',
        aliases: ['ubicacion', 'location', 'almacen', 'warehouse'],
        required: false,
        type: 'string',
        description: 'Ubicación física',
      },
      {
        field: 'lote',
        aliases: ['lote', 'batch', 'lot'],
        required: false,
        type: 'string',
        description: 'Número de lote',
      },
      {
        field: 'fecha_caducidad',
        aliases: ['caducidad', 'expiry', 'expiration', 'vencimiento'],
        required: false,
        type: 'date',
        description: 'Fecha de caducidad',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'default'],
  },

  ventas: {
    type: 'ventas',
    label: 'Ventas',
    icon: '💰',
    endpoint: '/api/v1/imports/batches',
    fields: [
      {
        field: 'fecha',
        aliases: ['fecha', 'date'],
        required: true,
        type: 'date',
        description: 'Fecha de venta',
      },
      {
        field: 'numero',
        aliases: ['numero', 'number', 'factura', 'invoice'],
        required: true,
        type: 'string',
        description: 'Número de venta/factura',
      },
      {
        field: 'cliente',
        aliases: ['cliente', 'customer', 'client'],
        required: false,
        type: 'string',
        description: 'Cliente',
      },
      {
        field: 'total',
        aliases: ['total', 'importe', 'amount'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Total de la venta',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller', 'default'],
  },

  compras: {
    type: 'compras',
    label: 'Compras',
    icon: '🛒',
    endpoint: '/api/v1/imports/batches',
    fields: [
      {
        field: 'fecha',
        aliases: ['fecha', 'date'],
        required: true,
        type: 'date',
        description: 'Fecha de compra',
      },
      {
        field: 'proveedor',
        aliases: ['proveedor', 'supplier'],
        required: true,
        type: 'string',
        description: 'Proveedor',
      },
      {
        field: 'total',
        aliases: ['total', 'importe', 'amount'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Total de la compra',
      },
    ],
    allowedTemplates: ['panaderia', 'default'],
  },

  facturas: {
    type: 'facturas',
    label: 'Facturas',
    icon: '🧾',
    endpoint: '/api/v1/imports/batches',
    fields: [
      {
        field: 'numero',
        aliases: ['numero', 'number', 'factura'],
        required: true,
        type: 'string',
        description: 'Número de factura',
      },
      {
        field: 'fecha',
        aliases: ['fecha', 'date'],
        required: true,
        type: 'date',
        description: 'Fecha de factura',
      },
      {
        field: 'cliente',
        aliases: ['cliente', 'customer'],
        required: true,
        type: 'string',
        description: 'Cliente',
      },
      {
        field: 'base',
        aliases: ['base', 'subtotal', 'base_imponible'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Base imponible',
      },
      {
        field: 'iva',
        aliases: ['iva', 'tax', 'impuesto'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'IVA',
      },
      {
        field: 'total',
        aliases: ['total', 'amount'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Total',
      },
    ],
    allowedTemplates: ['todoa100', 'panaderia', 'taller', 'default'],
  },

  gastos: {
    type: 'gastos',
    label: 'Gastos',
    icon: '💸',
    endpoint: '/api/v1/imports/batches',
    fields: [
      {
        field: 'fecha',
        aliases: ['fecha', 'date'],
        required: true,
        type: 'date',
        description: 'Fecha del gasto',
      },
      {
        field: 'concepto',
        aliases: ['concepto', 'description', 'descripcion'],
        required: true,
        type: 'string',
        description: 'Concepto del gasto',
      },
      {
        field: 'importe',
        aliases: ['importe', 'total', 'amount'],
        required: true,
        type: 'number',
        transform: (v) => parseFloat(String(v).replace(/[^\d.-]/g, '')),
        description: 'Importe',
      },
      {
        field: 'categoria',
        aliases: ['categoria', 'category', 'tipo'],
        required: false,
        type: 'string',
        description: 'Categoría',
      },
    ],
    allowedTemplates: ['default'],
  },

  empleados: {
    type: 'empleados',
    label: 'Empleados',
    icon: '👔',
    endpoint: '/api/v1/imports/batches',
    checkDuplicates: true,
    duplicateKeys: ['documento', 'email'],
    fields: [
      {
        field: 'nombre',
        aliases: ['nombre', 'name'],
        required: true,
        type: 'string',
        description: 'Nombre completo',
      },
      {
        field: 'documento',
        aliases: ['documento', 'dni', 'cedula', 'id'],
        required: true,
        type: 'string',
        description: 'Documento de identidad',
      },
      {
        field: 'email',
        aliases: ['email', 'correo', 'mail'],
        required: false,
        type: 'email',
        validation: (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v),
        description: 'Email',
      },
      {
        field: 'telefono',
        aliases: ['telefono', 'phone', 'movil'],
        required: false,
        type: 'string',
        description: 'Teléfono',
      },
      {
        field: 'puesto',
        aliases: ['puesto', 'cargo', 'position', 'role'],
        required: false,
        type: 'string',
        description: 'Puesto de trabajo',
      },
      {
        field: 'fecha_ingreso',
        aliases: ['fecha_ingreso', 'ingreso', 'start_date'],
        required: false,
        type: 'date',
        description: 'Fecha de ingreso',
      },
    ],
    allowedTemplates: ['default'],
  },
}

/**
 * Obtiene la configuración de un tipo de entidad
 */
export function getEntityConfig(type: EntityType): EntityTypeConfig {
  return ENTITY_TYPES[type]
}

/**
 * Obtiene los tipos de entidad disponibles para una plantilla
 */
export function getEntityTypesForTemplate(templateSlug: string): EntityTypeConfig[] {
  return Object.values(ENTITY_TYPES).filter(
    (config) => !config.allowedTemplates || config.allowedTemplates.includes(templateSlug)
  )
}

/**
 * Busca un campo por alias en la configuración
 */
export function findFieldByAlias(config: EntityTypeConfig, alias: string): ImportFieldConfig | undefined {
  const normalized = alias.toLowerCase().trim()
  return config.fields.find((field) =>
    field.aliases.some((a) => a.toLowerCase() === normalized)
  )
}
