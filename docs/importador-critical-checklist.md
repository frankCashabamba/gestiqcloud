# Checklist crítico del importador

Fecha: 2026-06-13

## Reglas UI

1. No mostrar `raw_ai_json` salvo modo debug/técnico.
2. Marcar campos derivados por IA, OCR, regla o usuario.
3. Exigir confirmación humana antes de guardar en destino.
4. Mostrar destino sugerido, confianza y campos faltantes.
5. Registrar usuario y timestamp de confirmación.
6. Permitir reprocess/reject antes de guardar.

## Estado actual

| Control | Estado |
|---|---|
| Revisión humana por documento | Parcial |
| `SaveDocumentModal` con destino y confirmación | Hecho |
| `confirmation_required` desde capacidades/destino | Hecho |
| Confianza visible | Hecho |
| Raw/debug JSON restringido | Hecho en vista normal |
| Campos derivados marcados visualmente | Parcial: badges IA/OCR/regla/usuario en detalle |
| Historial visible de cambios | Parcial |
| E2E importador | Añadido smoke inicial |

## Tests mínimos

- Upload de archivo.
- Documento queda en revisión.
- Confirmar datos.
- Guardar en destino.
- Rechazar documento.
- Verificar que raw JSON no aparece en UI normal.

## Cierres 2026-06-13

- `DocumentDetail` filtra campos internos/sensibles como `raw_ai_json`, prompts, completions y debug info.
- El modo edicion no incluye esos campos sensibles.
- `ReprocessPanel` filtra claves internas/sensibles en columnas y preview.
- E2E importador verifica que la UI normal no expone raw/debug JSON.
