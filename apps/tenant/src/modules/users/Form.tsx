
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import {
  createUsuario,
  getUsuario,
  updateUsuario,
  listModuloOptions,
  listRolOptions,
  checkUsernameAvailability,
  listRoles,
} from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { UsuarioCreatePayload, UsuarioUpdatePayload, ModuloOption, RolOption } from './types'
import { useAuth } from '../../auth/AuthContext'
import RolModal from './RoleModal'

const emptyForm: UsuarioCreatePayload = {
  first_name: '',
  last_name: '',
  email: '',
  username: '',
  password: '',
  is_company_admin: false,
  active: true,
  as_employee: true,
  employee_hire_date: new Date().toISOString().slice(0, 10),
  employee_department: '',
  employee_job_title: '',
  employee_salary_base: 0,
  employee_payment_mode: 'mensual',
  modules: [],
  roles: [],
}

function slugifyUsername(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '.')
    .replace(/(^[.]+|[.]+$)/g, '')
    .replace(/[.]{2,}/g, '.')
}

export default function UsuarioForm() {
  const { t } = useTranslation(['users', 'common'])
  const { id } = useParams()
  const nav = useNavigate()
  // Validación de permisos: solo admins de empresa pueden gestionar usuarios
  const { loading, profile } = useAuth()
  const isAdmin =
    Boolean((profile as any)?.es_admin_empresa) ||
    Boolean((profile as any)?.is_company_admin) ||
    Boolean(profile?.roles?.includes('admin'))
  const [form, setForm] = useState<UsuarioCreatePayload>(emptyForm)
  const [editMode, setEditMode] = useState(false)
  const [busy, setBusy] = useState(false)
  const [modules, setModules] = useState<ModuloOption[]>([])
  const [roles, setRoles] = useState<RolOption[]>([])
  const [showRoleModal, setShowRoleModal] = useState(false)
  const [checkingUsername, setCheckingUsername] = useState(false)
  const toast = useToast()
  const success = toast.success
  const errorRef = useRef(toast.error)
  const usernameAutoRef = useRef(true)

  useEffect(() => {
    errorRef.current = toast.error
  }, [toast.error])

  useEffect(() => {
    if (loading || !isAdmin) return
    let cancelled = false
    ;(async () => {
      try {
        const [modOpts, rolOpts] = await Promise.all([listModuloOptions(), listRolOptions()])
        if (!cancelled) {
          setModules(modOpts)
          setRoles(rolOpts)
        }
      } catch (e: any) {
        errorRef.current(getErrorMessage(e))
      }
    })()
    return () => {
      cancelled = true
    }
  }, [loading, isAdmin])

  useEffect(() => {
    if (loading || !isAdmin) return
    if (!id) return
    setBusy(true)
    let cancelled = false
    ;(async () => {
      try {
        const usuario = await getUsuario(id)
        if (cancelled) return
        setForm({
          first_name: usuario.first_name ?? '',
          last_name: usuario.last_name ?? '',
          email: usuario.email,
          username: usuario.username ?? '',
          password: '',
          is_company_admin: usuario.is_company_admin,
          active: usuario.active,
          as_employee: usuario.as_employee ?? false,
          employee_hire_date: usuario.employee_hire_date ?? new Date().toISOString().slice(0, 10),
          employee_department: usuario.employee_department ?? '',
          employee_job_title: usuario.employee_job_title ?? '',
          employee_salary_base: usuario.employee_salary_base ?? 0,
          employee_payment_mode: usuario.employee_payment_mode ?? 'mensual',
          modules: usuario.modules ?? [],
          roles: usuario.roles ?? [],
        })
        usernameAutoRef.current = false
        setEditMode(true)
      } catch (e: any) {
        if (!cancelled) {
          errorRef.current(getErrorMessage(e))
        }
      } finally {
        if (!cancelled) {
          setBusy(false)
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [id, loading, isAdmin])

  useEffect(() => {
    if (editMode || !usernameAutoRef.current) return
    const generated = slugifyUsername([form.first_name, form.last_name].filter(Boolean).join(' '))
    setForm((prev) => {
      if ((prev.username ?? '') === generated) return prev
      return { ...prev, username: generated }
    })
  }, [editMode, form.first_name, form.last_name])

  const canEditModulos = useMemo(() => !form.is_company_admin, [form.is_company_admin])

  const reloadRoles = async () => {
    const [roleOptions, fullRoles] = await Promise.all([listRolOptions(), listRoles()])
    setRoles(roleOptions.length > 0 ? roleOptions : fullRoles.map((role) => ({
      id: role.id,
      name: role.name,
      description: role.description ?? null,
    })))
    return fullRoles
  }

  const handleCheckboxChange = (key: 'modules' | 'roles', value: string) => {
    setForm((prev) => {
      const list = new Set(prev[key])
      if (list.has(value)) list.delete(value)
      else list.add(value)
      return { ...prev, [key]: Array.from(list) }
    })
  }

  const onSubmit: React.FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    try {
      if (!form.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
        throw new Error(t('users:form.invalidEmail'))
      }
      if (!form.first_name?.trim()) {
        throw new Error(t('users:form.nameRequired'))
      }
      if (!editMode && !form.password) {
        throw new Error(t('users:form.passwordRequired'))
      }
      if (form.as_employee && !form.is_company_admin) {
        if (!form.employee_hire_date) {
          throw new Error(t('users:form.employeeHireDateRequired'))
        }
        if (Number(form.employee_salary_base || 0) <= 0) {
          throw new Error(t('users:form.employeeSalaryRequired'))
        }
      }

      if (editMode && id) {
        const payload: UsuarioUpdatePayload = {
          first_name: form.first_name,
          last_name: form.last_name,
          email: form.email,
          username: form.username || undefined,
          password: form.password || undefined,
          is_company_admin: form.is_company_admin,
          active: form.active,
          as_employee: Boolean(form.as_employee && !form.is_company_admin),
          employee_hire_date: form.employee_hire_date || undefined,
          employee_department: form.employee_department || undefined,
          employee_job_title: form.employee_job_title || undefined,
          employee_salary_base: form.employee_salary_base,
          employee_payment_mode: form.employee_payment_mode || 'mensual',
          modules: canEditModulos ? form.modules : undefined,
          roles: canEditModulos ? form.roles : undefined,
        }
        await updateUsuario(id, payload)
        success(t('users:form.updated'))
      } else {
        const payload: UsuarioCreatePayload = {
          ...form,
          as_employee: Boolean(form.as_employee && !form.is_company_admin),
          employee_hire_date: form.employee_hire_date || undefined,
          employee_department: form.employee_department || undefined,
          employee_job_title: form.employee_job_title || undefined,
          employee_salary_base: form.employee_salary_base,
          employee_payment_mode: form.employee_payment_mode || 'mensual',
          modules: canEditModulos ? form.modules : [],
          roles: canEditModulos ? form.roles : [],
        }
        await createUsuario(payload)
        success(t('users:form.created'))
      }
      nav('..')
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    }
  }

  const handleUsernameBlur = async (event: React.FocusEvent<HTMLInputElement>) => {
    if (loading || !isAdmin) return
    const value = event.target.value.trim()
    if (!value) return
    try {
      setCheckingUsername(true)
      const available = await checkUsernameAvailability(value)
      if (!available) {
        errorRef.current(t('users:form.usernameInUse'))
      }
    } catch (e: any) {
      errorRef.current(getErrorMessage(e))
    } finally {
      setCheckingUsername(false)
    }
  }

  if (loading) return null
  if (!isAdmin) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold text-slate-900">{t('users:form.accessRestricted')}</h2>
        <p className="mt-2 text-sm text-slate-600">{t('users:form.noPermission')}</p>
        <button className="gc-button gc-button--ghost mt-4" onClick={() => nav('..')}>{t('users:form.back')}</button>
      </div>
    )
  }

  return (
    <div className="p-4 max-w-3xl">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <h3 className="text-xl font-semibold text-slate-900 mb-4">
        {editMode ? t('users:form.editUser') : t('users:form.newUser')}
      </h3>
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">{t('users:form.firstName')}</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.first_name ?? ''}
              onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              required
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">{t('users:form.lastName')}</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.last_name ?? ''}
              onChange={(e) => setForm({ ...form, last_name: e.target.value })}
            />
          </label>
        </div>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-600">{t('users:form.email')}</span>
          <input
            type="email"
            className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={form.email ?? ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">{t('users:form.username')}</span>
            <input
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              value={form.username ?? ''}
              onChange={(e) => {
                const value = e.target.value
                usernameAutoRef.current = value.trim() === '' || value === slugifyUsername([form.first_name, form.last_name].filter(Boolean).join(' '))
                setForm({ ...form, username: value })
              }}
              onBlur={handleUsernameBlur}
            />
            {checkingUsername && <span className="text-xs text-slate-400">{t('users:form.checking')}</span>}
          </label>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-600">{t('users:form.password')} {editMode && `(${t('users:form.optional')})`}</span>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder={editMode ? t('users:form.leaveBlank') : ''}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
          <input
            type="checkbox"
            checked={form.is_company_admin}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                is_company_admin: e.target.checked,
                as_employee: e.target.checked ? false : prev.as_employee,
              }))
            }
          />
          {t('users:form.companyAdmin')}
        </label>

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <h4 className="text-sm font-semibold text-slate-700">{t('users:form.enabledModules')}</h4>
            <p className="mb-2 text-xs text-slate-500">{t('users:form.enabledModulesDesc')}</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {modules.map((mod) => (
                <label key={mod.id} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form.modules.includes(mod.id)}
                    onChange={() => handleCheckboxChange('modules', mod.id)}
                  />
                  <span>{mod.name || `Módulo #${mod.id}`}</span>
                </label>
              ))}
              {!modules.length && <p className="text-xs text-slate-400">{t('users:form.noModules')}</p>}
            </div>
          </div>
        )}

        {canEditModulos && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-700">{t('users:form.rolesSection')}</h4>
                <p className="text-xs text-slate-500">{t('users:form.rolesDesc')}</p>
              </div>
              <button
                type="button"
                className="rounded-md border border-blue-600 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50"
                onClick={() => setShowRoleModal(true)}
              >
                {t('users:roleManagement.createRole')}
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {roles.map((rol) => (
                <label key={rol.id} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form.roles.includes(rol.id)}
                    onChange={() => handleCheckboxChange('roles', rol.id)}
                  />
                  <span>{rol.name}</span>
                </label>
              ))}
              {!roles.length && <p className="text-xs text-slate-400">{t('users:form.noRoles')}</p>}
            </div>
          </div>
        )}

        {Boolean(form.as_employee) && !form.is_company_admin && (
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="mb-3">
              <h4 className="text-sm font-semibold text-slate-700">{t('users:form.employeeData')}</h4>
              <p className="text-xs text-slate-500">{t('users:form.employeeDataDesc')}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-600">{t('users:form.employeePaymentMode')}</span>
                <select
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={form.employee_payment_mode ?? 'mensual'}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      employee_payment_mode: e.target.value as 'mensual' | 'diario' | 'por_hora',
                    })
                  }
                >
                  <option value="mensual">{t('users:form.employeePaymentModeMonthly')}</option>
                  <option value="diario">{t('users:form.employeePaymentModeDaily')}</option>
                  <option value="por_hora">{t('users:form.employeePaymentModeHourly')}</option>
                </select>
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-600">{t('users:form.employeeHireDate')}</span>
                <input
                  type="date"
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={form.employee_hire_date ?? ''}
                  onChange={(e) => setForm({ ...form, employee_hire_date: e.target.value })}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-600">
                  {form.employee_payment_mode === 'diario'
                    ? t('users:form.employeeDailyRate')
                    : form.employee_payment_mode === 'por_hora'
                    ? t('users:form.employeeHourlyRate')
                    : t('users:form.employeeSalary')}
                </span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={Number(form.employee_salary_base ?? 0)}
                  onChange={(e) =>
                    setForm({ ...form, employee_salary_base: Number(e.target.value || 0) })
                  }
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-600">{t('users:form.employeeJobTitle')}</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={form.employee_job_title ?? ''}
                  onChange={(e) => setForm({ ...form, employee_job_title: e.target.value })}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-600">{t('users:form.employeeDepartment')}</span>
                <input
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={form.employee_department ?? ''}
                  onChange={(e) => setForm({ ...form, employee_department: e.target.value })}
                />
              </label>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-5">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
            {t('users:form.activeUser')}
          </label>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-600">
            <input
              type="checkbox"
              checked={Boolean(form.as_employee) && !form.is_company_admin}
              disabled={form.is_company_admin}
              onChange={(e) => setForm({ ...form, as_employee: e.target.checked })}
            />
            {t('users:form.employee')}
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            className="gc-button gc-button--primary"
            disabled={busy}
          >
            {editMode ? t('users:form.saveChanges') : t('users:form.createUser')}
          </button>
          <button
            type="button"
            className="gc-button gc-button--ghost"
            onClick={() => nav('..')}
          >
            {t('users:form.cancel')}
          </button>
        </div>
      </form>

      {showRoleModal && (
        <RolModal
          rol={null}
          onClose={() => setShowRoleModal(false)}
          onSuccess={async () => {
            await reloadRoles()
            setShowRoleModal(false)
          }}
        />
      )}
    </div>
  )
}
