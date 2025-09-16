import React, { useEffect, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext"; // ajusta ruta

type Props = {
  warnAfterMs?: number;        // cuándo mostrar el aviso
  responseWindowMs?: number;   // ventana para responder antes de cerrar sesión
};

export default function SessionKeepAlive({
  warnAfterMs = 60_000,        // 1 min (pruebas)
  responseWindowMs = 60_000,   // 1 min (pruebas)
}: Props) {
  const { refresh, logout, token } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [remaining, setRemaining] = useState(Math.floor(responseWindowMs / 1000));
  const [rev, setRev] = useState(0); // para reiniciar timers tras "Seguir"

  const warnTimer = useRef<number | null>(null);
  const autoTimer = useRef<number | null>(null);
  const tickTimer = useRef<number | null>(null);

  function clearAll() {
    if (warnTimer.current) window.clearTimeout(warnTimer.current);
    if (autoTimer.current) window.clearTimeout(autoTimer.current);
    if (tickTimer.current) window.clearInterval(tickTimer.current);
    warnTimer.current = autoTimer.current = tickTimer.current = null;
  }

  useEffect(() => {
    if (!token) return; // no iniciar si no hay sesión
    clearAll();

    warnTimer.current = window.setTimeout(() => {
      setOpen(true);
      setRemaining(Math.floor(responseWindowMs / 1000));

      tickTimer.current = window.setInterval(
        () => setRemaining((s) => (s > 0 ? s - 1 : 0)),
        1000
      );

      autoTimer.current = window.setTimeout(async () => {
        setOpen(false);
        clearAll();
        await logout();
      }, responseWindowMs);
    }, warnAfterMs);

    return clearAll;
    // reinicia cuando cambie token (p.ej. tras refresh) o rev
  }, [token, warnAfterMs, responseWindowMs, logout, rev]);

  // Cierra y limpia al cambiar de ruta (navegación interna)
  useEffect(() => {
    if (!open) return;
    clearAll();
    setOpen(false);
    setRemaining(Math.floor(responseWindowMs / 1000));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname, location.search]);

  // Cierra/Resetea timers ante actividad del usuario (click/teclado/mouse/touch)
  useEffect(() => {
    if (!token) return;
    let last = 0;
    const throttleMs = 1000; // evita reinicios excesivos
    const handler = () => {
      const now = Date.now();
      if (now - last < throttleMs) return;
      last = now;
      clearAll();
      if (open) setOpen(false);
      setRemaining(Math.floor(responseWindowMs / 1000));
      setRev((x) => x + 1); // reinicia la programación de warn/auto
    };
    const events = ["click", "keydown", "mousemove", "touchstart", "visibilitychange"] as const;
    events.forEach((ev) => window.addEventListener(ev, handler));
    return () => {
      events.forEach((ev) => window.removeEventListener(ev, handler));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, responseWindowMs, open]);

  const onContinue = async () => {
    clearAll();
    const ok = await refresh();     // 🔄 pide nuevo access_token
    if (!ok) return logout();       // si falló el refresh, fuera
    setOpen(false);
    setRev((x) => x + 1);           // reinicia timers
  };

  const onExit = async () => {
    clearAll();
    setOpen(false);
    await logout();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-gray-800">
          Sesión a punto de expirar
        </h2>
        <p className="text-sm text-gray-600 mt-2">
          Tu sesión expirará en <span className="font-semibold">{remaining}s</span>.
          ¿Quieres seguir dentro?
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onExit}
            className="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm"
          >
            Salir
          </button>
          <button
            onClick={onContinue}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm"
          >
            Seguir conectado
          </button>
        </div>
      </div>
    </div>
  );
}
