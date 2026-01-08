Clientes — Módulo Empresa

Resumen
- Este módulo implementa el CRUD de clientes en la PWA de tenant y se integra con el sistema centralizado de configuración de campos per‑módulo/per‑tenant.
- El formulario de creación/edición consume la configuración desde la API para decidir qué campos mostrar, cuáles son obligatorios, etiquetas/ayudas y el orden.

Arquitectura del módulo
- Rutas: apps/tenant/src/modules/clientes/manifest.ts
- Formulario: apps/tenant/src/modules/clientes/Form.tsx
- Servicios HTTP: apps/tenant/src/modules/clientes/services.ts

Integración con configuración de campos
- El formulario obtiene la configuración con GET /api/v1/company/settings/fields?module=clientes&empresa=:slug
  - Implementación: apps/tenant/src/modules/clientes/Form.tsx:27
  - La respuesta incluye items: [{ field, visible, required, ord, label?, help? }]
  - El formulario filtra items con visible !== false y renderiza inputs en orden ascendente por ord.
- Backend resuelve la configuración combinando:
  - Configuración base administrada (catálogo)
  - Configuración por sector (sector_field_defaults)
  - Overrides por tenant (tenant_field_config)
  - Modo por tenant+módulo (tenant_module_settings.form_mode): ‘mixed’ (por defecto), ‘tenant’, ‘sector’, ‘basic’.
  - Servicio: apps/backend/app/services/field_config.py
  - Endpoint: apps/backend/app/modules/settings/interface/http/tenant.py:217 (GET /fields)

Modos de formulario (profesional y reutilizable)
- mixed (por defecto): fusiona configuración del sector con overrides del tenant (gana tenant). Nuevos campos definidos a nivel sector se incorporan automáticamente.
- tenant: usa solo la lista del tenant. Si está vacía, cae a sector y luego base.
- sector: usa solo configuración del sector. Si no hay, cae a base.
- basic: usa la lista base administrada.

Cómo añadir un campo (ej. “catalogo”)
1) Global para un sector (todos los tenants del sector):
   - Ir a Admin → Configuración → Campos → seleccionar Sector y módulo ‘clientes’.
   - Añadir fila field=catalogo, visible=✓, required=según necesidad, ord=…
   - Guardar. En tenants con modo ‘mixed’ o ‘sector’, el campo aparecerá.
2) Solo para un tenant concreto (100% personalizado o ajuste puntual):
   - En la misma vista, rellenar Empresa (slug), p. ej. kusi-panaderia.
   - Añadir la fila ‘catalogo’ y Guardar.
   - Opcional: cambia el Modo a ‘tenant’ si quieres que se ignore el sector.

Verificación rápida
- Llamada directa a API: curl "http://localhost:8000/api/v1/company/settings/fields?module=clientes&empresa=kusi-panaderia"
  - Debe listar un item con "field":"catalogo" y "visible":true si lo has configurado.
- UI: abre /:empresa/clientes/nuevo y comprueba que el campo aparece según el orden indicado.

Validación en el formulario
- El formulario valida required en cliente; cualquier item con required=true debe venir relleno antes de enviar.
- Email tiene una validación básica de formato: apps/tenant/src/modules/clientes/Form.tsx:33–47

Extender el formulario
- Añadir una nueva columna “core” (persistida):
  - Agregar la propiedad en el tipo Cliente en apps/tenant/src/modules/clientes/services.ts
  - Asegurarse de que el backend persiste ese campo en el recurso de clientes.
  - Añadirlo a la configuración de sector/base administrada si quieres que aparezca por defecto.
- Campo sólo UI / experimental:
  - Definirlo en la configuración de campos (sector o tenant) con un field único y usa help/label para guiar.

Endpoints relacionados
- GET /api/v1/company/settings/fields
  - Params: module=clientes, empresa=:slug (opcional)
- PUT /api/v1/admin/field-config/tenant
  - Guarda la lista de items para un tenant+módulo.
- PUT /api/v1/admin/field-config/sector
  - Guarda la lista de items por sector+módulo.
- PUT /api/v1/admin/field-config/tenant/mode
  - Cambia el form_mode de un tenant+módulo (‘mixed’, ‘tenant’, ‘sector’, ‘basic’).

Resolución y orden de campos (detalles)
- En modo ‘mixed’: se parte de los items del sector (o base si el sector no tiene) y se aplican los del tenant por clave ‘field’.
- El orden final se calcula por ‘ord’ ascendente (nulls al final) y luego por nombre de ‘field’.

Problemas comunes y soluciones
- “He añadido un campo en sector y no sale en un tenant”: ese tenant puede tener overrides. Usa modo ‘mixed’, o elimina/actualiza sus overrides del módulo ‘clientes’.
- “No cambia nada en la PWA”: forzar recarga dura para evitar caché del Service Worker (Ctrl+F5) o usar el prompt de actualización si aparece.
- “Orden incorrecto”: revisa ‘ord’ en la configuración. En fusión, si el override no define ‘ord’, se conserva el del sector.

Buenas prácticas
- Usar ‘mixed’ por defecto para heredar mejoras globales sin perder personalización.
- Dar un ‘ord’ espaciado (10, 20, 30…) para facilitar inserciones posteriores.
- Rellenar ‘label’ y ‘help’ en campos que no sean autoexplicativos.
