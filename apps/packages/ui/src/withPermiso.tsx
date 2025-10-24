import React, { useEffect, useState } from 'react'

export function withPermiso<TProps extends Record<string, any>>(
  Wrapped: React.ComponentType<TProps>,
  permiso: string,
  opts: { getToken: () => string | null; decode: (t: string) => any }
) {
  const Guarded: React.FC<TProps> = (props) => {
    const [ok, setOk] = useState<boolean | null>(null)
    useEffect(() => {
      const token = opts.getToken()
      if (!token) { setOk(false); return }
      try {
        const decoded: any = opts.decode(token)
        const isSuper = !!decoded?.is_superadmin
        const isAdminEmpresa = !!decoded?.es_admin_empresa
        const permisos = decoded?.permisos || {}
        setOk(!!(isSuper || isAdminEmpresa || permisos[permiso]))
      } catch { setOk(false) }
    }, [])
    if (ok === null) return <div className="text-center text-gray-500 p-10">Verificando acceso...</div>
    if (!ok) return <div className="text-center text-red-600 p-10">Acceso denegado</div>
    return <Wrapped {...props} />
  }
  return Guarded
}
