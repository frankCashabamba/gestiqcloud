Titulo: Campos profesionales para clientes (multi‑sector)

Motivación
- Alinear el modelo de clientes con un CRM/ERP profesional multi‑país.
- Soportar personas y empresas, direcciones de facturación/envío, y
  condiciones comerciales (crédito, plazos, idioma, moneda).

Resumen de cambios (solo DDL, compatible hacia atrás)
- Añade campos opcionales: tipo_persona, identificacion_tipo, nombre_comercial,
  razon_social, contacto_* (nombre/email/telefono), whatsapp, website.
- Direcciones: direccion2, ciudad, más bloque de envío (envio_*).
- Comerciales: payment_terms_days, credit_limit, descuento_pct, moneda, idioma.
- Gestión: notas, tags (TEXT[]), bloqueado.
- Índices útiles y unique parcial por tenant en identificacion cuando no es NULL.

Notas
- No se eliminan columnas existentes (p. ej. ruc).
- Todos los nuevos campos son NULLables.
- Requiere Postgres (índice parcial).

