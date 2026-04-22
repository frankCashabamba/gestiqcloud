export function shouldUseParentRouteBack(pathname: string): boolean {
  const segments = pathname.replace(/\/+$/, '').split('/').filter(Boolean)

  return segments.length > 2
}
