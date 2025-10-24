/**
 * Offline Indicator - Indicador de estado de conexión
 */


type OfflineIndicatorProps = {
  isOnline: boolean
}

export default function OfflineIndicator({ isOnline }: OfflineIndicatorProps) {
  return (
    <div
      className={`flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${
        isOnline
          ? 'bg-green-100 text-green-700'
          : 'bg-amber-100 text-amber-700 animate-pulse'
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-600' : 'bg-amber-600'}`} />
      {isOnline ? '🟢 Online' : '🔴 Offline'}
    </div>
  )
}
