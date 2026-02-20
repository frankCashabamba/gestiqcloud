# Documento de trabajo: Emision y Plantillas (EC primero)

> Objetivo: llevar un control paso a paso de lo que vamos a desarrollar y lo que ya esta hecho.
> Foco actual: Ecuador. El diseno debe permitir sumar otros paises sin rehacer el core.

---

## 1) Principios base
- Reglas (logica) y plantillas (presentacion) estan separadas.
- El HTML nunca contiene reglas tributarias.
- Todo render consume un DocumentModel ya calculado.
- Cada emision guarda versiones: config, country pack, template.

---

## 2) Estructura objetivo (backend)
- DocumentOrchestrator: draft/issue y validaciones.
- CountryPack: reglas por pais (EC ahora).
- TaxEngine: calculo generico (por linea y total).
- TemplateEngine: seleccion por tipo + formato + tenant + version.
- Storage: documento emitido + versionado.

---

## 3) Fases y tareas

### Fase 1: Contratos y Orchestrator (core)
- [x] Definir modelos de dominio (SaleDraft, DocumentModel, IssuedDocument).
- [x] Crear DocumentOrchestrator con draft/issue.
- [x] Endpoints: POST /sales/draft y POST /sales/issue.
- [x] Persistir configVersionUsed + countryPackVersion + templateVersion (tabla documents).

### Fase 2: CountryPack Ecuador (MVP)
- [x] Implementar EcuadorPack.validate (consumidor final + monto maximo).
- [x] Implementar EcuadorPack.buildBuyer (idType NONE, idNumber 999...).
- [x] Implementar EcuadorPack.calculateTaxes (IVA 0, soporte tasas multiples).
- [x] Catalogo base de idTypes y tax codes para EC (tablas + loader).

### Fase 3: TemplateEngine y versionado
- [x] Definir clave de plantilla: type + format + tenant.
- [x] Implementar fallback default si no hay override del tenant.
- [x] Mover el HTML inline del ticket a templates versionados.
- [x] Endpoint GET /documents/{id}/render?format=...
- [x] Endpoint GET /documents/{id}/print (HTML listo para imprimir).

### Fase 4: Config por tenant
- [x] Extender tenant settings: buyer_policy, tax_profile, render_format_default (soportado en loader).
- [x] Agregar document_mode_default y branding (soportado en loader).
- [x] Versionado de config con effectiveFrom + version (leido desde company_settings.settings.documents).

### Fase 5: Tests minimos
- [x] Unit tests: EcuadorPack.validate.
- [x] Unit tests: TaxEngine totales coherentes.
- [x] Snapshot tests: HTML de templates.

### Fase 6: Frontend POS (UX minimo)
- [x] Toggle comprador: Consumidor final vs Con datos.
- [x] Validacion en UI: bloquear o alertar si supera monto maximo.
- [x] Preview HTML desde /tenant/documents/{id}/render.
- [x] Boton Imprimir (window.print) en pagina dedicada.
- [x] Footer/branding desde tenant config.
- [x] Catalogo idTypes por pais expuesto en settings (documents.id_types).
- [x] Sync offline para document_issue en POS outbox.

---

## 4) Estado actual (resumen rapido)
- POS receipts funcionan, ticket imprime HTML inline.
- Facturas PDF usan template fijo.
- Numeracion de documentos existe.
- Config por tenant existe pero sin buyer_policy/tax_profile.
- DocumentOrchestrator MVP con draft/issue y CountryPack Ecuador.
- TemplateEngine con render/print y template 80mm default.
- Documentos emitidos se guardan en tabla `documents` (payload JSON).
- Numeracion real con `generar_numero_documento` y series/secuencial derivado.
- Branding del tenant disponible en template (logo, footer, email, website).
- Tax profile default por categoria con fallback DEFAULT.
- effectiveFrom guardado en tabla y expuesto en DocumentModel (document.meta + render).
- Catalogos por pais: country_id_types + country_tax_codes (sin hardcode).
- POS frontend emite documento al cobrar, imprime HTML del template (fallback a ticket).
- Tipo de documento se selecciona en modal previo al cobro.
- Outbox offline sincroniza document_issue automaticamente.

---

## 5) Registro de decisiones
- Decision 001: usar DocumentModel unificado para render.
- Decision 002: CountryPack define reglas, no las plantillas.
- Decision 003: template selection por type+format+tenant con fallback.

---

## 6) Backlog futuro (otros paises)
- [ ] SpainPack (IVA 21/10/4, NIF/NIE/CIF).
- [ ] PeruPack, ChilePack.
- [ ] Integracion con autoridad tributaria (si aplica).

---

## 7) Notas de seguimiento
- Fecha:
- Hecho:
- Proximo paso:
  - Modelado de tax_profile/catalogos por pais.
  - Catalogo EC (idTypes/tax codes).
  - Snapshot tests de templates.
