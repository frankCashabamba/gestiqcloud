/**
 * Product Card - Card individual de producto (touch-optimized)
 */


type Product = {
  id: string
  name: string
  sku?: string
  price: number
  image_url?: string
  stock?: number
  category?: string
}

type ProductCardProps = {
  product: Product
  onClick: () => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
    }).format(price)
  }

  const hasLowStock = product.stock !== undefined && product.stock < 10
  const outOfStock = product.stock !== undefined && product.stock <= 0

  return (
    <button
      onClick={onClick}
      disabled={outOfStock}
      className="product-card relative flex flex-col items-center justify-between disabled:cursor-not-allowed disabled:opacity-50"
    >
      {/* Image */}
      <div className="mb-3 flex h-24 w-24 items-center justify-center overflow-hidden rounded-xl bg-slate-100">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl">
            {getProductEmoji(product.category || product.name)}
          </div>
        )}
      </div>

      {/* Name */}
      <h3 className="mb-2 line-clamp-2 text-center text-sm font-semibold text-slate-900">
        {product.name}
      </h3>

      {/* Price */}
      <p className="text-2xl font-bold text-blue-600">
        {formatPrice(product.price)}
      </p>

      {/* Stock Badge */}
      {hasLowStock && !outOfStock && (
        <span className="absolute right-2 top-2 rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700">
          {product.stock} left
        </span>
      )}
      
      {outOfStock && (
        <span className="absolute right-2 top-2 rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700">
          Agotado
        </span>
      )}

      {/* SKU */}
      {product.sku && (
        <p className="mt-1 text-xs text-slate-500">{product.sku}</p>
      )}
    </button>
  )
}

// Helper para emojis según categoría/producto
function getProductEmoji(text: string): string {
  const lower = text.toLowerCase()
  
  // Panadería
  if (lower.includes('pan')) return '🥖'
  if (lower.includes('empanada')) return '🥟'
  if (lower.includes('croissant')) return '🥐'
  if (lower.includes('muffin') || lower.includes('magdalena')) return '🧁'
  if (lower.includes('tarta') || lower.includes('pastel')) return '🎂'
  if (lower.includes('galleta') || lower.includes('cookie')) return '🍪'
  if (lower.includes('donut') || lower.includes('rosquilla')) return '🍩'
  
  // Bebidas
  if (lower.includes('café') || lower.includes('coffee')) return '☕'
  if (lower.includes('té') || lower.includes('tea')) return '🍵'
  if (lower.includes('agua') || lower.includes('water')) return '💧'
  if (lower.includes('refresco') || lower.includes('soda')) return '🥤'
  if (lower.includes('zumo') || lower.includes('juice')) return '🧃'
  
  // Otros
  if (lower.includes('leche') || lower.includes('milk')) return '🥛'
  if (lower.includes('queso') || lower.includes('cheese')) return '🧀'
  if (lower.includes('mantequilla') || lower.includes('butter')) return '🧈'
  
  // Default
  return '📦'
}
