Titulo: Configuración de campos por tenant (UI Field Config)

Motivo
- Permitir ocultar/mostrar y marcar como obligatorios campos del módulo Clientes
  por tenant/sector, sin romper otros sectores.

Cambios
- Nueva tabla tenant_field_config con (tenant_id, module, field, visible, required, ord, label, help).
- Índices por tenant y módulo; unique por (tenant_id, module, field).

Uso previsto
- GET /api/v1/tenant/settings/fields?module=clientes&empresa=:slug devuelve
  la configuración; si no hay filas, retorna defaults por sector.
