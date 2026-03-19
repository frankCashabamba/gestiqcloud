export const MAX_BAKERY_SHORTCUTS = 10

export type BulkPricingItem = {
    product_id: string
    product_name?: string
    quantity: number
    unit_price: number
    shortcut_letter?: string | null
}

export const normalizeBakeryShortcutLetter = (value?: string | null): string => {
    const normalized = (value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/[^A-Za-z]/g, '')
        .trim()
        .toUpperCase()
    return normalized.slice(0, 1)
}

export const sanitizeBulkPricingItem = (item: BulkPricingItem): BulkPricingItem => ({
    product_id: String(item.product_id || '').trim(),
    product_name: item.product_name ? String(item.product_name).trim() : undefined,
    quantity: Number(item.quantity) || 0,
    unit_price: Number(item.unit_price) || 0,
    shortcut_letter: normalizeBakeryShortcutLetter(item.shortcut_letter),
})

export const getBulkPricingShortcutItems = (items?: BulkPricingItem[] | null): BulkPricingItem[] =>
    (items || [])
        .map(sanitizeBulkPricingItem)
        .filter((item) => !!item.shortcut_letter)

export const getBakeryShortcutMultiplierFromFunctionKey = (code: string): number | null => {
    const match = /^F([1-9]|10)$/i.exec((code || '').trim())
    if (!match) return null
    const multiplier = Number(match[1])
    return Number.isFinite(multiplier) && multiplier >= 1 && multiplier <= MAX_BAKERY_SHORTCUTS
        ? multiplier
        : null
}

export const getBakeryShortcutValidationError = (
    items: BulkPricingItem[],
    nextShortcutLetter?: string | null,
    nextProductId?: string | null
): string | null => {
    const shortcutItems = getBulkPricingShortcutItems(items)
    if (shortcutItems.length > MAX_BAKERY_SHORTCUTS) {
        return `Solo se permiten ${MAX_BAKERY_SHORTCUTS} teclas alfabeticas para panaderia.`
    }

    const normalizedLetter = normalizeBakeryShortcutLetter(nextShortcutLetter)
    if (!normalizedLetter) return null

    const totalLetters = new Set(shortcutItems.map((item) => item.shortcut_letter)).size
    const alreadyExists = shortcutItems.some(
        (item) => item.shortcut_letter === normalizedLetter && item.product_id !== nextProductId
    )
    if (alreadyExists) {
        return `La tecla ${normalizedLetter} ya esta asignada a otro producto.`
    }

    const letterExistsOnCurrentProduct = shortcutItems.some(
        (item) => item.shortcut_letter === normalizedLetter && item.product_id === nextProductId
    )
    if (!letterExistsOnCurrentProduct && totalLetters >= MAX_BAKERY_SHORTCUTS) {
        return `Solo se permiten ${MAX_BAKERY_SHORTCUTS} teclas alfabeticas para panaderia.`
    }

    return null
}
