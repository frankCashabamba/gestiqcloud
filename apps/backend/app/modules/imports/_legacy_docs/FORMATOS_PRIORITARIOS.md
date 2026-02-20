# Formatos de Importación Prioritarios

Lista de formatos identificados para soporte inicial del importador universal.

## 📊 Inventario de Formatos

### 1. **Excel (.xlsx, .xls)** - ✅ Implementado
- **Productos**: Estructura con nombre, precio, cantidad, categoría
- **Genérico**: Auto-detección de tipo por headers
- **Parsers**: `products_excel.py`, `generic_excel.py`

### 2. **CSV (.csv)** - 🔄 Pendiente
- **Productos**: Formato delimitado por comas con headers
- **Ventas**: Registros de transacciones
- **Contactos**: Información de proveedores/clientes

### 3. **XML (.xml)** - 🔄 Pendiente
- **Facturas electrónicas**: Facturas XML de SRI (Ecuador)
- **Recibos**: Tickets de gastos en XML
- **Catálogos**: Listas de productos en XML

### 4. **PDF con QR (.pdf)** - 🔄 Pendiente
- **Facturas digitales**: PDF con código QR de validación
- **Recibos**: Tickets de compra con QR
- **Documentos oficiales**: Con códigos de verificación

### 5. **JSON (.json)** - 🔄 Futuro
- **APIs**: Respuestas de servicios web
- **Configuraciones**: Datos estructurados
- **Backups**: Exportaciones de otros sistemas

## 🎯 Priorización por Impacto

### Alta Prioridad (Semana 1-2)
1. **CSV productos** - Muy común en exportaciones de sistemas legacy
2. **XML facturas** - Requerido para cumplimiento tributario Ecuador
3. **PDF con QR** - Cada vez más común en facturación digital

### Media Prioridad (Semana 3-4)
4. **Excel bancos** - Estados de cuenta bancarios
5. **CSV ventas** - Registros de transacciones comerciales
6. **XML recibos** - Gastos y tickets en formato XML

### Baja Prioridad (Futuro)
7. **JSON APIs** - Integraciones con servicios externos
8. **Formatos propietarios** - Archivos específicos de software contable

## 📋 Especificaciones por Formato

### CSV Productos
```csv
nombre,precio,cantidad,categoria,sku,descripcion
"Producto A",15.50,100,"Electrónicos","PROD001","Producto de prueba"
```

### XML Factura Ecuador
```xml
<factura>
  <infoTributaria>
    <ruc>1792012345001</ruc>
    <razonSocial>EMPRESA SA</razonSocial>
  </infoTributaria>
  <infoFactura>
    <fechaEmision>2025-01-15</fechaEmision>
    <totalSinImpuestos>100.00</totalSinImpuestos>
    <totalDescuento>0.00</totalDescuento>
  </infoFactura>
</factura>
```

### PDF con QR
- Código QR contiene URL de validación SRI
- Texto OCR para extraer datos principales
- Imágenes para casos donde OCR falla

## 🔧 Requisitos Técnicos

### Dependencias Nuevas
- `pandas` - Para manipulación avanzada de datos CSV
- `lxml` - Para parsing XML robusto
- `PyPDF2` o `pdfplumber` - Para extracción de PDF
- `pyzbar` o `opencv` - Para lectura de códigos QR

### Validaciones Específicas
- **CSV**: Encoding detection (UTF-8, ISO-8859-1, etc.)
- **XML**: Schema validation contra XSD oficiales
- **PDF**: Verificación de integridad QR vs datos extraídos

## 📈 Métricas de Éxito

- **Coverage**: 80% de casos de uso cubiertos con parsers principales
- **Accuracy**: >95% de parsing correcto en formatos soportados
- **Performance**: <30 segundos para archivos típicos (<10MB)
- **Robustness**: Graceful fallback para formatos malformados</content>
</xai:function_call">
