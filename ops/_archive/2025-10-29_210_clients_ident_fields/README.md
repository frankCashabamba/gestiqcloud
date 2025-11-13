Titulo: Alinear esquema de clients con modelo ORM (identificacion y direccion)

Motivo
- El modelo ORM app/models/core/clients.py espera las columnas:
  identificacion, localidad, provincia, pais, codigo_postal.
- La tabla clients del baseline no las tenía (solo ruc, direccion básica),
  lo que provocaba errores 500 al listar clientes.

Cambios
- Añade columnas faltantes con IF NOT EXISTS.
- Migra ruc -> identificacion para no perder datos.

Impacto
- Backward compatible. No elimina columnas.
- No afecta RLS.
