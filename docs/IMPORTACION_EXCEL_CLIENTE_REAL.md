# 📥 Importación de Excel de Cliente Real con Códigos de Barras

**Flujo completo: Desde Excel del cliente → Códigos de barras → Pistola lectora**

## 🎯 Caso de Uso Real

**Situación**: Cliente "Todo a 100" tiene Excel con catálogo de 67-68 productos:
- ✅ Tiene: SKU, nombre, precio
- ❌ NO tiene: Códigos de barras para pistola
- 🎯 Necesita: Generar códigos + imprimir etiquetas

**Archivo**: `67 Y 68 CATALOGO.xlsx`

---

## 📋 Flujo Paso a Paso

### 1️⃣ Usuario sube el Excel

**Desde cualquier plantilla** (todoa100, panaderia, taller):

```tsx
// En la interfaz del tenant:
http://localhost:8082/importador

// O desde botón en plantilla
<Link to="/importador">📤 Importar productos</Link>
```

**Pantalla**: 
- 🔘 Seleccionar tipo: **"Productos"**
- 📁 Subir archivo: `67 Y 68 CATALOGO.xlsx`
- ⚙️ Auto-mapeo de columnas

### 2️⃣ Sistema detecta columnas faltantes

El sistema mapea automáticamente:

| Columna Excel | Campo Sistema | Estado |
|---------------|---------------|--------|
| SKU / Código | `sku` | ✅ Mapeado |
| Nombre / Producto | `nombre` | ✅ Mapeado |
| Precio / PVP | `precio_venta` | ✅ Mapeado |
| Stock / Cantidad | `stock` | ✅ Mapeado |
| **Código Barras** | `codigo_barras` | ⚠️ **FALTA** |

**Banner de advertencia**:
```
⚠️ 67 productos sin código de barras
Algunos productos no tienen código de barras. 
Puedes generarlos automáticamente para usar con pistola lectora.

[🏷️ Generar códigos automáticamente]
```

### 3️⃣ Usuario genera códigos VIRTUALES automáticamente

Al hacer clic en **"Generar códigos virtuales"**:

**Importante**: Los códigos generados son **virtuales/internos**, NO son EAN del fabricante.

**Opciones**:
- 🔢 **Formato**: EAN-13 virtual (recomendado) - Prefijo 200-299 (uso interno)
- ✅ **Con checksum**: Sí (validación automática)
- 🎯 **Uso**: Solo para pistola lectora interna, NO para venta en supermercados externos

**Resultado**:
```javascript
// Producto 1 - Código VIRTUAL generado
{
  sku: 'COCA-2L',
  nombre: 'Coca Cola 2L',
  precio_venta: 2.50,
  codigo_barras: '2000000000018', // ⭐ CÓDIGO VIRTUAL (200 = interno)
  _barcode_generated: true,        // ⭐ Flag: código virtual generado por sistema
  _barcode_type: 'virtual'         // ⭐ Tipo: virtual (no es EAN del fabricante)
}

// Producto 2 - Código VIRTUAL generado
{
  sku: 'PAN-INT',
  nombre: 'Pan Integral',
  precio_venta: 1.20,
  codigo_barras: '2000000000025', // ⭐ CÓDIGO VIRTUAL
  _barcode_generated: true,
  _barcode_type: 'virtual'
}
```

**Prefijos de códigos virtuales**:
- `200-299`: Uso interno (recomendado para TODO a 100)
- Estos códigos **NO son válidos** para venta a distribuidores externos
- Solo para uso interno del negocio con pistola lectora

### 4️⃣ Preview y validación

**Pantalla de revisión**:
- ✅ 67 productos cargados
- ✅ 67 códigos de barras generados
- ✅ 0 errores de validación
- ℹ️ Los códigos generados son **únicos** y tienen **checksum válido**

**Tabla de preview**:
| SKU | Nombre | Precio | Código Barras | Estado |
|-----|--------|--------|---------------|--------|
| COCA-2L | Coca Cola 2L | €2.50 | `2000000000018` | ✅ Generado |
| PAN-INT | Pan Integral | €1.20 | `2000000000025` | ✅ Generado |

### 5️⃣ Importar a la base de datos

Usuario hace clic en **"Importar ahora"**:

```http
POST /api/v1/imports/batches/{batch_id}/ingest
Content-Type: application/json

{
  "items": [
    {
      "sku": "COCA-2L",
      "nombre": "Coca Cola 2L",
      "precio_venta": 2.50,
      "codigo_barras": "2000000000018"
    },
    // ... 66 productos más
  ],
  "dry_run": false,
  "dedupe": true
}
```

**Backend**:
- ✅ Valida datos
- ✅ Aplica RLS (tenant_id automático)
- ✅ Detecta duplicados por SKU
- ✅ Inserta en `productos` table
- ✅ Retorna: `{ accepted: 67, rejected: 0 }`

### 6️⃣ Imprimir etiquetas con códigos de barras

**Pantalla final**:
```
✅ 67 productos importados correctamente

[🖨️ Imprimir etiquetas] [📋 Ver productos]
```

Usuario hace clic en **"Imprimir etiquetas"**:

**Configuración de impresión**:
- 📏 **Tamaño**: 40x30mm | **50x40mm** (seleccionado) | 70x50mm
- 💰 **Mostrar precio**: ✅ Sí
- 🏷️ **Mostrar categoría**: ☐ No
- 📑 **Copias por producto**: 2

**Vista previa** (3 etiquetas por fila):

```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Coca Cola 2L │ │ Coca Cola 2L │ │ Pan Integral │
│ ┃┃┃┃┃┃┃┃┃┃  │ │ ┃┃┃┃┃┃┃┃┃┃  │ │ ┃┃┃┃┃┃┃┃┃┃  │
│ 2000000000018│ │ 2000000000018│ │ 2000000000025│
│   €2.50      │ │   €2.50      │ │   €1.20      │
└──────────────┘ └──────────────┘ └──────────────┘
```

**Botones**:
- `[🖨️ Imprimir]` → Abre diálogo del sistema
- `[Cancelar]` → Vuelve a la lista

**Impresión**:
- 📄 Se envía a impresora de etiquetas (Brother QL, Zebra, Dymo, etc.)
- 📄 O a impresora normal (papel adhesivo A4)

### 7️⃣ Usar con pistola lectora

Los códigos generados son **100% compatibles** con pistolas lectoras USB/Bluetooth:

**En el TPV/POS**:
1. Usuario escanea producto: `📷 [BEEP] 2000000000018`
2. Sistema busca por `codigo_barras = '2000000000018'`
3. Encuentra: "Coca Cola 2L - €2.50"
4. Añade al carrito ✅

---

## 🔧 Configuración Técnica

### Formatos de Código de Barras

#### 1. **EAN-13** (Recomendado para retail)
- **Longitud**: 13 dígitos
- **Estructura**: `XXX-YYYYYYYYY-C`
  - `XXX`: Prefijo (país o interno)
  - `YYYYYYYYY`: Código producto
  - `C`: Checksum
- **Ventajas**: Estándar mundial, checksum integrado
- **Ejemplos**:
  - España: `84` + 10 dígitos + checksum
  - Ecuador: `786` + 9 dígitos + checksum
  - Interno: `200-299` + resto

#### 2. **CODE-128** (Uso interno alfanumérico)
- **Longitud**: Variable
- **Estructura**: `PREFIX-NNNNNN`
- **Ventajas**: Soporta letras y números
- **Ejemplo**: `INT-000001`, `STORE-001234`

#### 3. **EAN-8** (Versión corta)
- **Longitud**: 8 dígitos
- **Uso**: Productos pequeños con poco espacio

### Prefijos de Códigos

| Tipo | Prefijo | Ejemplo | Uso |
|------|---------|---------|-----|
| Uso Interno (Virtual) | `200-299` | `2000000000018` | ⭐ **Recomendado** - Pistola lectora interna |
| España (EAN real) | `84` | `8400000000125` | Solo si tienes licencia GS1 España |
| Ecuador (EAN real) | `786` | `7860000000014` | Solo si tienes licencia GS1 Ecuador |

**⚠️ Importante**: 
- Códigos con prefijo `200-299` son **VIRTUALES/INTERNOS**
- NO son códigos EAN oficiales del fabricante
- Solo válidos para uso interno con tu pistola lectora
- **NO usar para venta a distribuidores externos**

### Generación Automática

```typescript
import { getBarcodeGeneratorForCountry } from './utils/barcodeGenerator'

// Para España
const generator = getBarcodeGeneratorForCountry('ES', 1)
generator.next() // => '8400000000125'

// Para uso interno (recomendado para TODO a 100)
const generator = getBarcodeGeneratorForCountry('INTERNAL', 1)
generator.next() // => '2000000000018'
generator.next() // => '2000000000025'
```

### Validación de Códigos

```typescript
import { validateBarcode } from './utils/barcodeGenerator'

validateBarcode('2000000000018', 'EAN13') // => true
validateBarcode('2000000000019', 'EAN13') // => false (checksum incorrecto)
```

---

## 📊 Flujo de Datos (Diagrama)

```
┌─────────────────┐
│ Excel Cliente   │
│ (67 productos)  │
└────────┬────────┘
         │ 1. Upload
         ▼
┌─────────────────────────────────┐
│ Módulo Importador Universal     │
├─────────────────────────────────┤
│ • Detecta columnas               │
│ • Mapea automáticamente          │
│ • Detecta códigos faltantes (67) │
└────────┬────────────────────────┘
         │ 2. Usuario: "Generar códigos"
         ▼
┌─────────────────────────────────┐
│ BarcodeGenerator                 │
├─────────────────────────────────┤
│ • Genera EAN-13: 2000000000018   │
│ • Genera EAN-13: 2000000000025   │
│ • ... (67 códigos únicos)        │
│ • Calcula checksums              │
└────────┬────────────────────────┘
         │ 3. Productos completos
         ▼
┌─────────────────────────────────┐
│ Backend /v1/imports/batches     │
├─────────────────────────────────┤
│ • Valida datos                   │
│ • Aplica RLS (tenant_id)         │
│ • INSERT productos table         │
└────────┬────────────────────────┘
         │ 4. Success
         ▼
┌─────────────────────────────────┐
│ PrintBarcodeLabels Component    │
├─────────────────────────────────┤
│ • Genera etiquetas 50x40mm       │
│ • Renderiza códigos con JsBarcode│
│ • 67 productos × 2 copias = 134  │
└────────┬────────────────────────┘
         │ 5. window.print()
         ▼
┌─────────────────────────────────┐
│ Impresora de Etiquetas          │
│ (Brother QL / Zebra / Dymo)     │
└─────────────────────────────────┘
         │ 6. Etiquetas físicas
         ▼
┌─────────────────────────────────┐
│ Pegadas en productos físicos    │
└─────────────────────────────────┘
         │ 7. Escanear con pistola
         ▼
┌─────────────────────────────────┐
│ TPV/POS Module                  │
├─────────────────────────────────┤
│ • Escanea: 2000000000018         │
│ • Busca producto: Coca Cola 2L   │
│ • Precio: €2.50                  │
│ • Añade a carrito ✅             │
└─────────────────────────────────┘
```

---

## 🛠️ Implementación en Código

### 1. Backend: Obtener siguiente secuencia de código

```python
# apps/backend/app/routers/imports.py

@router.get("/barcodes/next-sequence")
async def get_next_barcode_sequence(
    country: str = Query('INTERNAL'),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    """
    Obtiene la siguiente secuencia disponible para generar códigos de barras
    """
    # Buscar el último código del tenant con el prefijo
    prefix = {'ES': '84', 'EC': '786', 'INTERNAL': '200'}[country]
    
    last_barcode = await db.execute(
        select(Producto.codigo_barras)
        .where(
            Producto.tenant_id == tenant_id,
            Producto.codigo_barras.like(f'{prefix}%')
        )
        .order_by(Producto.codigo_barras.desc())
        .limit(1)
    )
    
    last = last_barcode.scalar_one_or_none()
    
    if not last:
        return {"next_sequence": 1, "prefix": prefix}
    
    # Extraer secuencia del último código
    try:
        sequence_part = last[len(prefix):-1]  # Quitar prefix y checksum
        next_seq = int(sequence_part) + 1
    except:
        next_seq = 1
    
    return {"next_sequence": next_seq, "prefix": prefix}
```

### 2. Frontend: Integración en ImportadorExcel

```tsx
// En ImportadorExcel.tsx

import { useBarcodeFiller, MissingBarcodesBanner } from './hooks/useBarcodeFiller'
import { usePrintBarcodeLabels } from './components/PrintBarcodeLabels'

function ImportadorExcel() {
  const [products, setProducts] = useState<ProductRow[]>([])
  
  const {
    productsWithBarcodes,
    generatedCount,
    hasMissingBarcodes,
    fillMissingBarcodes,
    validateAllBarcodes,
  } = useBarcodeFiller(products)

  const { open: openPrintLabels, PrintModal } = usePrintBarcodeLabels()

  // Después de mapear columnas
  const handleGenerateBarcodes = async () => {
    const tenant = await getTenantInfo()
    const country = tenant.country === 'ES' ? 'ES' : tenant.country === 'EC' ? 'EC' : 'INTERNAL'
    
    const updated = fillMissingBarcodes({ 
      country, 
      overwriteInvalid: true 
    })
    
    setProducts(updated)
    
    toast.success(`✅ ${generatedCount} códigos de barras generados`)
  }

  // Después de importar
  const handleImportSuccess = async () => {
    // Abrir impresión de etiquetas
    openPrintLabels(productsWithBarcodes, {
      labelSize: '50x40',
      showPrice: true,
      copies: 2, // 2 etiquetas por producto
    })
  }

  return (
    <div>
      {/* Banner si faltan códigos */}
      <MissingBarcodesBanner
        missingCount={analysis.missing}
        onGenerate={handleGenerateBarcodes}
      />

      {/* Tabla de productos */}
      <ProductTable products={productsWithBarcodes} />

      {/* Botón de importar */}
      <button onClick={handleImport}>Importar</button>

      {/* Modal de impresión */}
      {PrintModal}
    </div>
  )
}
```

---

## 📦 Dependencias Necesarias

### NPM Packages

```bash
# Para generar códigos de barras visuales
npm install jsbarcode

# TypeScript types
npm install -D @types/jsbarcode
```

### package.json

```json
{
  "dependencies": {
    "jsbarcode": "^3.11.5"
  },
  "devDependencies": {
    "@types/jsbarcode": "^3.11.1"
  }
}
```

---

## 🖨️ Tipos de Etiquetas Recomendados

### 1. Etiqueta Pequeña (40x30mm)
**Uso**: Productos muy pequeños
```
┌──────────────┐
│ Coca Cola 2L │
│ ┃┃┃┃┃┃┃┃┃┃  │
│ 2000000000018│
└──────────────┘
```

### 2. Etiqueta Estándar (50x40mm) ⭐ Recomendada
**Uso**: Mayoría de productos
```
┌────────────────┐
│  Coca Cola 2L  │
│  ┃┃┃┃┃┃┃┃┃┃  │
│  2000000000018 │
│    €2.50       │
└────────────────┘
```

### 3. Etiqueta Grande (70x50mm)
**Uso**: Productos con mucha info
```
┌──────────────────┐
│  Coca Cola 2L    │
│  ┃┃┃┃┃┃┃┃┃┃    │
│  2000000000018   │
│                  │
│  €2.50           │
│  SKU: COCA-2L    │
│  Bebidas         │
└──────────────────┘
```

---

## ⚙️ Configuración por Tenant

Cada tenant puede configurar su preferencia:

```json
// Configuración del tenant en settings
{
  "barcode": {
    "auto_generate": true,
    "format": "EAN13",
    "prefix": "200",
    "label_size": "50x40",
    "print_price": true,
    "copies_default": 2
  }
}
```

---

## 🧪 Testing del Flujo Completo

### Test 1: Importar Excel real sin códigos

```bash
# 1. Subir 67 Y 68 CATALOGO.xlsx
# 2. Verificar que detecta columnas
# 3. Generar códigos automáticamente
# 4. Validar que todos tienen checksum correcto
# 5. Importar a DB
# 6. Verificar que se insertaron 67 productos
```

### Test 2: Imprimir etiquetas

```bash
# 1. Después de importar, hacer clic en "Imprimir"
# 2. Configurar: 50x40mm, precio=Sí, copias=2
# 3. Verificar preview: 134 etiquetas (67 × 2)
# 4. Hacer clic en "Imprimir"
# 5. Verificar que se abre diálogo del sistema
```

### Test 3: Escanear con pistola

```bash
# 1. Ir a TPV/POS: http://localhost:8082/pos
# 2. Crear nuevo ticket
# 3. Escanear código: 2000000000018
# 4. Verificar que encuentra: Coca Cola 2L - €2.50
# 5. Añadir al carrito
# 6. Verificar total correcto
```

---

## 📝 Notas de Implementación

### Backend

```python
# apps/backend/app/models/core/producto.py

class Producto(Base):
    __tablename__ = 'productos'
    
    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey('tenants.id'), nullable=False)
    sku = Column(String(100), nullable=False, unique=True)
    nombre = Column(String(255), nullable=False)
    codigo_barras = Column(String(50), nullable=True, index=True)  # ⭐ Puede ser NULL
    barcode_generated = Column(Boolean, default=False)  # ⭐ Flag: generado automáticamente
    precio_venta = Column(Numeric(12, 2), nullable=False)
    # ... más campos
    
    __table_args__ = (
        Index('idx_productos_barcode', 'tenant_id', 'codigo_barras'),
        UniqueConstraint('tenant_id', 'sku', name='uq_productos_tenant_sku'),
    )
```

### Frontend: Configuración de país automática

```typescript
// Detectar país del tenant
const getTenantCountry = async (): Promise<'ES' | 'EC' | 'INTERNAL'> => {
  const tenant = await apiFetch('/v1/tenants/me')
  return tenant.country || 'INTERNAL'
}
```

---

## 🚀 Próximos Pasos (M2-M3)

### M2 (Corto plazo)
- [x] Generador de códigos EAN-13 con checksum
- [x] Componente de impresión de etiquetas
- [ ] Integración en ImportadorExcel
- [ ] Endpoint backend para siguiente secuencia
- [ ] Tests con Excel real

### M3 (Mediano plazo)
- [ ] Impresión térmica directa (ESC/POS)
- [ ] Generación de QR codes (para productos con mucha info)
- [ ] Re-impresión individual desde catálogo
- [ ] Exportar etiquetas a PDF
- [ ] Integración con impresoras Bluetooth

---

## 📚 Referencias

- **JsBarcode**: https://github.com/lindell/JsBarcode
- **EAN-13 Spec**: https://www.gs1.org/standards/barcodes/ean-upc
- **GS1 España**: https://www.gs1es.org/
- **CODE-128**: https://en.wikipedia.org/wiki/Code_128

---

**Versión**: 1.0.0  
**Última actualización**: Enero 2025  
**Caso de uso**: Cliente real TODO a 100 con catálogo 67-68 productos
