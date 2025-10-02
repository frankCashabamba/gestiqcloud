import React, { createContext, useContext } from 'react'

export type UiEnv = {
  apiUrl: string
  basePath: string
  tenantOrigin: string
  adminOrigin: string
  mode: 'development' | 'production' | 'test'
  dev: boolean
  prod: boolean
}

const EnvContext = createContext<UiEnv | null>(null)

export function EnvProvider(props: { value: UiEnv; children: React.ReactNode }) {
  return <EnvContext.Provider value={props.value}>{props.children}</EnvContext.Provider>
}

export function useEnv(): UiEnv {
  const ctx = useContext(EnvContext)
  if (!ctx) throw new Error('useEnv() requires <EnvProvider value={...}>')
  return ctx
}
