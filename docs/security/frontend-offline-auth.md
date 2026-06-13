# Auditoría frontend offline auth

Fecha: 2026-06-13

## Estado actual

- No se guarda password plano.
- La contraseña se guarda como hash SHA-256 con salt.
- Las credenciales offline expiran a 30 días.
- Se guarda token y snapshot de perfil offline en IndexedDB.
- La sesión offline se marca en `sessionStorage`.

## Riesgos abiertos

| Riesgo | Estado | Acción mínima |
|---|---|---|
| Token offline persistido | Abierto | Cifrar snapshot/token con clave derivada o reducir alcance/duración. |
| Revocación si usuario fue deshabilitado | Abierto | Revalidar al volver online y limpiar snapshot si backend rechaza. |
| Política por tenant/rol | Abierto | Añadir setting `offline_login_enabled` y lista de roles permitidos. |
| Dispositivo compartido | Abierto | Logout debe limpiar snapshot y credenciales offline. |
| Auditoría de datos IndexedDB | Parcial | Documentar stores y PII persistida. |

## Reglas para producción

1. Offline login solo para roles permitidos por tenant.
2. Expiración recomendada: máximo 7 días para credenciales offline.
3. Logout debe borrar token runtime, fallback token y snapshot offline.
4. Al recuperar conexión, llamar `/me` o refresh y revocar modo offline si falla.
5. No persistir datos personales innecesarios en snapshots.

## Checks manuales

- Login online, cerrar red, login offline válido.
- Intentar login offline tras expirar timestamp.
- Logout y comprobar IndexedDB/localStorage/sessionStorage.
- Simular usuario deshabilitado y verificar limpieza al volver online.
