import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CalendarDays, ClipboardList, Factory, Play, Plus, Printer, TimerReset } from 'lucide-react'
import { GcPageHeader } from '@ui'
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard'
import {
    createProductionOrder,
    listProductionPlanningSuggestions,
    listProductionOrders,
    startProductionOrder,
    updateProductionOrder,
    type ProductionPlanningSuggestion,
    type ProductionOrder,
} from './services'
import { listRecipes, type Recipe } from '../../services/api/recetas'
import { listWarehouses, type Warehouse } from '../inventory/services'
import { getErrorMessage, useToast } from '../../shared/toast'
import { usePermission } from '../../hooks/usePermission'
import './production-planner.css'

type PlannerDraft = {
    recipe_id: string
    qty_planned: string
    schedule_time: string
    warehouse_id: string
    notes: string
}

const EMPTY_DRAFT: PlannerDraft = {
    recipe_id: '',
    qty_planned: '',
    schedule_time: '05:00',
    warehouse_id: '',
    notes: '',
}

function todayLocalDate() {
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}

function buildDateTime(dateValue: string, timeValue: string) {
    return `${dateValue}T${timeValue}:00`
}

function formatHour(value?: string, locale = 'es-ES') {
    if (!value) return '--:--'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return value.slice(11, 16) || value
    return new Intl.DateTimeFormat(locale, {
        hour: '2-digit',
        minute: '2-digit',
    }).format(parsed)
}

function formatDateLabel(value: string, locale = 'es-ES') {
    const parsed = new Date(`${value}T12:00:00`)
    if (Number.isNaN(parsed.getTime())) return value
    return new Intl.DateTimeFormat(locale, {
        weekday: 'long',
        day: '2-digit',
        month: 'long',
        year: 'numeric',
    }).format(parsed)
}

function formatNumber(value: number, locale = 'es-ES') {
    return new Intl.NumberFormat(locale, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(value)
}

function formatStatusTone(status?: string) {
    if (status === 'completed') return 'planner-badge planner-badge--success'
    if (status === 'in_progress') return 'planner-badge planner-badge--info'
    if (status === 'cancelled') return 'planner-badge planner-badge--danger'
    return 'planner-badge planner-badge--neutral'
}

export default function ProductionPlanner() {
    return (
        <ProductionAvailabilityGuard>
            <ProductionPlannerContent />
        </ProductionAvailabilityGuard>
    )
}

function ProductionPlannerContent() {
    const { t, i18n } = useTranslation(['productions', 'common'])
    const can = usePermission()
    const canWrite = can('produccion:write')
    const { success, error: toastError } = useToast()
    const locale = i18n.resolvedLanguage || i18n.language || 'es-ES'

    const [selectedDate, setSelectedDate] = useState(todayLocalDate())
    const [orders, setOrders] = useState<ProductionOrder[]>([])
    const [suggestions, setSuggestions] = useState<ProductionPlanningSuggestion[]>([])
    const [recipes, setRecipes] = useState<Recipe[]>([])
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [loading, setLoading] = useState(true)
    const [draft, setDraft] = useState<PlannerDraft>(EMPTY_DRAFT)
    const [saving, setSaving] = useState(false)
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                const [recipeList, warehouseList] = await Promise.all([
                    listRecipes({ activo: true, limit: 500 }),
                    listWarehouses().catch(() => []),
                ])
                if (cancelled) return
                setRecipes(Array.isArray(recipeList) ? recipeList : [])
                setWarehouses(Array.isArray(warehouseList) ? warehouseList : [])
                const activeWarehouse =
                    (Array.isArray(warehouseList) && warehouseList.find((item) => item.is_active)) ||
                    (Array.isArray(warehouseList) ? warehouseList[0] : null)
                setDraft((prev) => ({
                    ...prev,
                    warehouse_id: prev.warehouse_id || String(activeWarehouse?.id || ''),
                }))
            } catch (error) {
                if (!cancelled) toastError(getErrorMessage(error))
            }
        })()
        return () => {
            cancelled = true
        }
    }, [toastError])

    useEffect(() => {
        void loadOrdersForDate(selectedDate)
    }, [selectedDate])

    const loadOrdersForDate = async (dateValue: string) => {
        try {
            setLoading(true)
            const [items, nextSuggestions] = await Promise.all([
                listProductionOrders({
                    scheduled_from: `${dateValue}T00:00:00`,
                    scheduled_to: `${dateValue}T23:59:59`,
                    limit: 200,
                }),
                listProductionPlanningSuggestions({
                    target_date: dateValue,
                    history_days: 14,
                    limit: 8,
                }).catch(() => []),
            ])
            setOrders(items)
            setSuggestions(nextSuggestions)
        } catch (error) {
            toastError(getErrorMessage(error))
            setOrders([])
            setSuggestions([])
        } finally {
            setLoading(false)
        }
    }

    const recipeMap = useMemo(
        () =>
            recipes.reduce<Record<string, Recipe>>((acc, recipe) => {
                acc[recipe.id] = recipe
                return acc
            }, {}),
        [recipes]
    )

    const warehouseMap = useMemo(
        () =>
            warehouses.reduce<Record<string, Warehouse>>((acc, warehouse) => {
                acc[String(warehouse.id)] = warehouse
                return acc
            }, {}),
        [warehouses]
    )

    const sortedOrders = useMemo(
        () =>
            [...orders].sort((left, right) =>
                String(left.scheduled_date || '').localeCompare(String(right.scheduled_date || ''))
            ),
        [orders]
    )

    const summary = useMemo(() => {
        return {
            total: sortedOrders.length,
            plannedQty: sortedOrders.reduce((sum, item) => sum + Number(item.qty_planned || 0), 0),
            inProgress: sortedOrders.filter((item) => item.status === 'in_progress').length,
            completed: sortedOrders.filter((item) => item.status === 'completed').length,
        }
    }, [sortedOrders])

    const selectedRecipe = draft.recipe_id ? recipeMap[draft.recipe_id] : undefined
    const printDateLabel = useMemo(() => formatDateLabel(selectedDate, locale), [locale, selectedDate])
    const generatedAtLabel = useMemo(
        () =>
            new Intl.DateTimeFormat(locale, {
                dateStyle: 'short',
                timeStyle: 'short',
            }).format(new Date()),
        [locale, orders, selectedDate, suggestions],
    )

    const applyRecipe = (recipeId: string) => {
        const recipe = recipeMap[recipeId]
        setDraft((prev) => ({
            ...prev,
            recipe_id: recipeId,
            qty_planned:
                prev.qty_planned && Number(prev.qty_planned) > 0
                    ? prev.qty_planned
                    : String(Number(recipe?.yield_qty || 1)),
        }))
    }

    const handlePrint = () => {
        if (typeof window === 'undefined' || typeof window.print !== 'function') return
        window.print()
    }

    const handleCreatePlannedOrder = async () => {
        if (!canWrite) return
        if (!draft.recipe_id) {
            toastError(t('productions:planner.recipeRequired'))
            return
        }
        const qtyPlanned = Number(draft.qty_planned)
        if (!qtyPlanned || qtyPlanned <= 0) {
            toastError(t('productions:planner.qtyRequired'))
            return
        }
        const recipe = recipeMap[draft.recipe_id]
        if (!recipe) {
            toastError(t('productions:planner.recipeRequired'))
            return
        }

        try {
            setSaving(true)
            const created = await createProductionOrder({
                recipe_id: recipe.id,
                product_id: recipe.product_id,
                warehouse_id: draft.warehouse_id || undefined,
                qty_planned: qtyPlanned,
                scheduled_date: buildDateTime(selectedDate, draft.schedule_time || '05:00'),
                notes: draft.notes.trim() || undefined,
                status: 'draft',
            })
            await updateProductionOrder(created.id, { status: 'scheduled' })
            setDraft((prev) => ({
                ...prev,
                qty_planned: String(Number(recipe.yield_qty || 1)),
                notes: '',
            }))
            success(t('productions:planner.created'))
            await loadOrdersForDate(selectedDate)
        } catch (error) {
            toastError(getErrorMessage(error))
        } finally {
            setSaving(false)
        }
    }

    const handleStart = async (order: ProductionOrder) => {
        if (!canWrite) return
        try {
            setActionLoadingId(order.id)
            await startProductionOrder(order.id)
            success(t('productions:messages.started'))
            await loadOrdersForDate(selectedDate)
        } catch (error) {
            toastError(getErrorMessage(error))
        } finally {
            setActionLoadingId(null)
        }
    }

    return (
        <div className="planner-shell">
            <section className="planner-hero">
                <GcPageHeader
                    badge={t('productions:planner.badge')}
                    title={t('productions:planner.title')}
                    subtitle={t('productions:planner.subtitle')}
                />
                <div className="planner-hero__actions">
                    <button type="button" className="gc-btn gc-btn--ghost" onClick={handlePrint}>
                        <Printer size={16} />
                        {t('productions:planner.print')}
                    </button>
                    <Link to="../ordenes" className="gc-btn gc-btn--ghost">
                        <ClipboardList size={16} />
                        {t('productions:planner.openOrders')}
                    </Link>
                </div>
            </section>

            <section className="planner-summary">
                <article className="planner-card">
                    <div className="planner-card__label">{t('productions:planner.totalOrders')}</div>
                    <div className="planner-card__value">
                        <CalendarDays size={18} />
                        {summary.total}
                    </div>
                </article>
                <article className="planner-card">
                    <div className="planner-card__label">{t('productions:planner.totalPlanned')}</div>
                    <div className="planner-card__value">
                        <Factory size={18} />
                        {summary.plannedQty}
                    </div>
                </article>
                <article className="planner-card">
                    <div className="planner-card__label">{t('productions:planner.inProgress')}</div>
                    <div className="planner-card__value">
                        <Play size={18} />
                        {summary.inProgress}
                    </div>
                </article>
                <article className="planner-card">
                    <div className="planner-card__label">{t('productions:planner.completed')}</div>
                    <div className="planner-card__value">
                        <TimerReset size={18} />
                        {summary.completed}
                    </div>
                </article>
            </section>

            <section className="planner-grid">
                <article className="planner-panel">
                    <div className="planner-panel__header">
                        <div>
                            <h3>{t('productions:planner.daySetup')}</h3>
                            <p>{t('productions:planner.daySetupHint')}</p>
                        </div>
                    </div>

                    <div className="planner-form">
                        <label className="planner-field">
                            <span>{t('productions:planner.day')}</span>
                            <input
                                type="date"
                                className="gc-input"
                                value={selectedDate}
                                onChange={(event) => setSelectedDate(event.target.value)}
                            />
                        </label>
                        <label className="planner-field">
                            <span>{t('productions:planner.recipe')}</span>
                            <select
                                className="gc-input gc-select"
                                value={draft.recipe_id}
                                onChange={(event) => applyRecipe(event.target.value)}
                            >
                                <option value="">{t('productions:planner.selectRecipe')}</option>
                                {recipes.map((recipe) => (
                                    <option key={recipe.id} value={recipe.id}>
                                        {recipe.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="planner-field">
                            <span>{t('productions:planner.qty')}</span>
                            <input
                                type="number"
                                min="0.01"
                                step="0.01"
                                className="gc-input"
                                value={draft.qty_planned}
                                onChange={(event) =>
                                    setDraft((prev) => ({ ...prev, qty_planned: event.target.value }))
                                }
                            />
                        </label>
                        <label className="planner-field">
                            <span>{t('productions:planner.time')}</span>
                            <input
                                type="time"
                                className="gc-input"
                                value={draft.schedule_time}
                                onChange={(event) =>
                                    setDraft((prev) => ({ ...prev, schedule_time: event.target.value }))
                                }
                            />
                        </label>
                        <label className="planner-field">
                            <span>{t('productions:planner.warehouse')}</span>
                            <select
                                className="gc-input gc-select"
                                value={draft.warehouse_id}
                                onChange={(event) =>
                                    setDraft((prev) => ({ ...prev, warehouse_id: event.target.value }))
                                }
                            >
                                <option value="">{t('productions:planner.selectWarehouse')}</option>
                                {warehouses.map((warehouse) => (
                                    <option key={warehouse.id} value={String(warehouse.id)}>
                                        {warehouse.code || warehouse.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="planner-field planner-field--wide">
                            <span>{t('productions:planner.notes')}</span>
                            <textarea
                                className="gc-input"
                                rows={3}
                                value={draft.notes}
                                onChange={(event) =>
                                    setDraft((prev) => ({ ...prev, notes: event.target.value }))
                                }
                                placeholder={t('productions:planner.notesPlaceholder')}
                            />
                        </label>
                    </div>

                    {selectedRecipe && (
                        <div className="planner-inline-note">
                            {t('productions:planner.recipeYield')}: {selectedRecipe.yield_qty}
                            {warehouseMap[draft.warehouse_id] && (
                                <>
                                    {' · '}
                                    {t('productions:planner.usingWarehouse')}:{' '}
                                    {warehouseMap[draft.warehouse_id].code ||
                                        warehouseMap[draft.warehouse_id].name}
                                </>
                            )}
                        </div>
                    )}

                    {canWrite && (
                        <button
                            type="button"
                            className="gc-btn gc-btn--primary"
                            onClick={() => void handleCreatePlannedOrder()}
                            disabled={saving}
                        >
                            <Plus size={16} />
                            {saving ? t('productions:planner.saving') : t('productions:planner.addToPlan')}
                        </button>
                    )}

                    {suggestions.length > 0 && (
                        <div className="planner-suggestions">
                            <div className="planner-suggestions__title">
                                {t('productions:planner.suggestionsTitle')}
                            </div>
                            <div className="planner-suggestions__hint">
                                {t('productions:planner.suggestionsHint')}
                            </div>
                            <div className="planner-suggestions__list">
                                {suggestions.map((item) => (
                                    <button
                                        key={item.recipe_id}
                                        type="button"
                                        className="planner-suggestion"
                                        onClick={() =>
                                            setDraft((prev) => ({
                                                ...prev,
                                                recipe_id: item.recipe_id,
                                                qty_planned: String(item.suggested_qty),
                                            }))
                                        }
                                    >
                                        <div className="planner-suggestion__head">
                                            <span>{item.recipe_name}</span>
                                            <strong>{item.suggested_qty}</strong>
                                        </div>
                                        <div className="planner-suggestion__meta">
                                            {item.product_name} · {t('productions:planner.avgSales')}:{' '}
                                            {item.avg_daily_sales.toFixed(1)} · {t('productions:planner.currentStock')}:{' '}
                                            {item.stock_on_hand.toFixed(1)}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </article>

                <article className="planner-panel">
                    <div className="planner-panel__header">
                        <div>
                            <h3>{t('productions:planner.dayOrders')}</h3>
                            <p>{t('productions:planner.dayOrdersHint')}</p>
                        </div>
                    </div>

                    {loading ? (
                        <div className="planner-empty">{t('productions:loading')}</div>
                    ) : sortedOrders.length === 0 ? (
                        <div className="planner-empty">{t('productions:planner.emptyDay')}</div>
                    ) : (
                        <div className="planner-list">
                            {sortedOrders.map((order) => {
                                const recipe = order.recipe_id ? recipeMap[order.recipe_id] : undefined
                                const busy = actionLoadingId === order.id
                                return (
                                    <div key={order.id} className="planner-order">
                                        <div className="planner-order__main">
                                            <div className="planner-order__time">
                                                {formatHour(order.scheduled_date)}
                                            </div>
                                            <div className="planner-order__content">
                                                <div className="planner-order__title">
                                                    {recipe?.name || order.numero || t('productions:number')}
                                                </div>
                                                <div className="planner-order__meta">
                                                    {order.numero || '-'} · {t('productions:plannedQty')}:{' '}
                                                    {order.qty_planned}
                                                    {order.notes ? ` · ${order.notes}` : ''}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="planner-order__actions">
                                            <span className={formatStatusTone(order.status)}>
                                                {t(`productions:statuses.${order.status || 'draft'}`)}
                                            </span>
                                            {canWrite && (order.status === 'draft' || order.status === 'scheduled') && (
                                                <button
                                                    type="button"
                                                    className="planner-link"
                                                    onClick={() => void handleStart(order)}
                                                    disabled={busy}
                                                >
                                                    {t('productions:actionsLabels.start')}
                                                </button>
                                            )}
                                            <Link to={`../ordenes/${order.id}/editar`} className="planner-link">
                                                {t('productions:edit')}
                                            </Link>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </article>
            </section>

            <section className="planner-print-sheet">
                <header className="planner-print-sheet__header">
                    <div>
                        <div className="planner-print-sheet__eyebrow">
                            {t('productions:planner.badge')}
                        </div>
                        <h2>{t('productions:planner.printTitle')}</h2>
                        <p>{t('productions:planner.printSubtitle', { date: printDateLabel })}</p>
                    </div>
                    <div className="planner-print-sheet__meta">
                        <div className="planner-print-sheet__meta-item">
                            <span>{t('productions:planner.day')}</span>
                            <strong>{printDateLabel}</strong>
                        </div>
                        <div className="planner-print-sheet__meta-item">
                            <span>{t('productions:planner.generatedAt')}</span>
                            <strong>{generatedAtLabel}</strong>
                        </div>
                    </div>
                </header>

                <div className="planner-print-summary">
                    <article className="planner-print-card">
                        <span>{t('productions:planner.totalOrders')}</span>
                        <strong>{summary.total}</strong>
                    </article>
                    <article className="planner-print-card">
                        <span>{t('productions:planner.totalPlanned')}</span>
                        <strong>{formatNumber(summary.plannedQty, locale)}</strong>
                    </article>
                    <article className="planner-print-card">
                        <span>{t('productions:planner.inProgress')}</span>
                        <strong>{summary.inProgress}</strong>
                    </article>
                    <article className="planner-print-card">
                        <span>{t('productions:planner.completed')}</span>
                        <strong>{summary.completed}</strong>
                    </article>
                </div>

                {suggestions.length > 0 && (
                    <section className="planner-print-block">
                        <div className="planner-print-block__title">
                            {t('productions:planner.suggestionsTitle')}
                        </div>
                        <div className="planner-print-suggestions">
                            {suggestions.map((item) => (
                                <div key={item.recipe_id} className="planner-print-suggestion">
                                    <strong>
                                        {item.recipe_name} ({formatNumber(item.suggested_qty, locale)})
                                    </strong>
                                    <span>
                                        {item.product_name} | {t('productions:planner.avgSales')}:{' '}
                                        {formatNumber(item.avg_daily_sales, locale)} |{' '}
                                        {t('productions:planner.currentStock')}:{' '}
                                        {formatNumber(item.stock_on_hand, locale)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <section className="planner-print-block">
                    <div className="planner-print-block__title">
                        {t('productions:planner.dayOrders')}
                    </div>
                    {sortedOrders.length === 0 ? (
                        <div className="planner-print-empty">{t('productions:planner.emptyDay')}</div>
                    ) : (
                        <table className="planner-print-table">
                            <thead>
                                <tr>
                                    <th>{t('productions:planner.time')}</th>
                                    <th>{t('productions:planner.recipe')}</th>
                                    <th>{t('productions:planner.qty')}</th>
                                    <th>{t('productions:planner.warehouse')}</th>
                                    <th>{t('productions:status')}</th>
                                    <th>{t('productions:planner.notes')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedOrders.map((order) => {
                                    const recipe = order.recipe_id ? recipeMap[order.recipe_id] : undefined
                                    const warehouse = order.warehouse_id
                                        ? warehouseMap[String(order.warehouse_id)]
                                        : undefined
                                    const noteParts = [
                                        order.batch_number
                                            ? `${t('productions:fields.batch')}: ${order.batch_number}`
                                            : '',
                                        order.notes || '',
                                    ].filter(Boolean)

                                    return (
                                        <tr key={order.id}>
                                            <td>{formatHour(order.scheduled_date, locale)}</td>
                                            <td>{recipe?.name || order.numero || t('productions:number')}</td>
                                            <td>{formatNumber(Number(order.qty_planned || 0), locale)}</td>
                                            <td>{warehouse?.code || warehouse?.name || '-'}</td>
                                            <td>{t(`productions:statuses.${order.status || 'draft'}`)}</td>
                                            <td>{noteParts.join(' | ') || '-'}</td>
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </section>
            </section>
        </div>
    )
}
