
import React, { Children } from 'react'
import { NavLink, useParams } from 'react-router-dom'

type NavItem = { label: string; to: string }

type Props = {
  title: string
  subtitle?: string
  topNav?: NavItem[]
  sideNav?: NavItem[]
  kpis?: React.ReactNode
  children?: React.ReactNode
}

export default function SectorLayout({ title, subtitle, topNav = [], sideNav = [], kpis, children }: Props) {
  const { empresa } = useParams()
  const prefix = empresa ? `/${empresa}` : ''
  const kpiItems = kpis ? Children.toArray(kpis) : []

  return (
    <div className="relative min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50 pb-16">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-6 focus:top-6 focus:z-50 focus:rounded-md focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Saltar al contenido
      </a>

      <div className="gc-container pt-10">
        <header className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-700">
              Espacio de trabajo
            </span>
            <div>
              <h1 className="text-3xl font-semibold text-slate-900">{title}</h1>
              {subtitle && <p className="mt-2 max-w-3xl text-sm text-slate-500">{subtitle}</p>}
            </div>
          </div>

          {topNav.length > 0 && (
            <nav aria-label="Acciones r?pidas" className="flex flex-wrap gap-2">
              {topNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={`${prefix}${item.to}`}
                  className={({ isActive }) =>
                    `gc-button px-4 py-2 ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-100'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          )}
        </header>

        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,260px)_1fr]">
          <aside className="lg:sticky lg:top-10">
            <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
              {sideNav.length > 0 ? (
                <nav aria-label="Navegaci?n de m?dulos" className="space-y-1">
                  {sideNav.map((item) => (
                    <NavLink
                      key={item.to}
                      to={`${prefix}${item.to}`}
                      className={({ isActive }) =>
                        `flex items-center justify-between rounded-xl px-4 py-2 text-sm font-medium transition ${
                          isActive
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                        }`
                      }
                    >
                      <span>{item.label}</span>
                      <span aria-hidden="true" className="text-xs">
                        ?
                      </span>
                    </NavLink>
                  ))}
                </nav>
              ) : (
                <p className="text-xs text-slate-400">Todav?a no tienes m?dulos asignados en este espacio.</p>
              )}
            </div>
          </aside>

          <main id="main" className="space-y-8">
            {kpiItems.length > 0 && (
              <section aria-label="Indicadores clave" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {kpiItems}
              </section>
            )}

            <section className="space-y-6">{children}</section>
          </main>
        </div>
      </div>
    </div>
  )
}
