Titulo: Defaults de campos por sector (sector_field_defaults)

Motivo
- Evitar tocar código al añadir nuevos sectores. Permite definir visibilidad y
  obligatoriedad de campos por módulo y sector.

Cambios
- Tabla sector_field_defaults con (sector, module, field, visible, required, ord, label, help).
- Índices por (sector, module) y unique por (sector, module, field).
