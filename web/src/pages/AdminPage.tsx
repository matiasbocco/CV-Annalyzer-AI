import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  adminCreateUser,
  adminExpireCVs,
  adminGetCosts,
  adminGetMetrics,
  adminListCVs,
  adminListUsers,
  adminPatchUser,
  adminResetPassword,
} from '../api/endpoints'
import type {
  AdminCV,
  AdminUser,
  CostsResponse,
  CVListResponse,
  MetricsResponse,
} from '../api/types'
import { cn } from '../lib/utils'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return '—'
  return n.toFixed(decimals)
}

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

/** Fill gaps in analyses_by_day so the chart always shows 30 bars. */
function fillDays(data: { date: string; count: number }[]): { date: string; count: number }[] {
  const map = new Map(data.map((d) => [d.date, d.count]))
  const result: { date: string; count: number }[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    result.push({ date: key.slice(5), count: map.get(key) ?? 0 }) // show MM-DD
  }
  return result
}

// ── Toast ─────────────────────────────────────────────────────────────────────

type ToastKind = 'success' | 'error'

function useToast() {
  const [toast, setToast] = useState<{ msg: string; kind: ToastKind } | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const show = useCallback((msg: string, kind: ToastKind = 'success') => {
    if (timer.current) clearTimeout(timer.current)
    setToast({ msg, kind })
    timer.current = setTimeout(() => setToast(null), 4000)
  }, [])

  return { toast, show }
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-md p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="text-slate-100 font-semibold">{title}</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-xl leading-none"
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ── Badge ─────────────────────────────────────────────────────────────────────

function Badge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        'text-xs font-medium px-2 py-0.5 rounded-full',
        active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-400',
      )}
    >
      {active ? 'Activo' : 'Inactivo'}
    </span>
  )
}

// ── Tab 1 — Usuarios ──────────────────────────────────────────────────────────

function UsuariosTab() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast, show } = useToast()

  // Create user modal
  const [showCreate, setShowCreate] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newRole, setNewRole] = useState<'admin' | 'recruiter'>('recruiter')
  const [newFirstName, setNewFirstName] = useState('')
  const [newLastName, setNewLastName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createdPassword, setCreatedPassword] = useState<string | null>(null)

  // Reset password modal
  const [resetPassword, setResetPassword] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      setUsers(await adminListUsers())
    } catch {
      setError('No se pudo cargar la lista de usuarios.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleToggleActive(u: AdminUser) {
    try {
      await adminPatchUser(u.id, { is_active: !u.is_active })
      show(u.is_active ? 'Usuario desactivado.' : 'Usuario activado.')
      setUsers((prev) =>
        prev.map((x) => (x.id === u.id ? { ...x, is_active: !u.is_active } : x)),
      )
    } catch {
      show('No se pudo actualizar el usuario.', 'error')
    }
  }

  async function handleResetPassword(u: AdminUser) {
    try {
      const res = await adminResetPassword(u.id)
      setResetPassword(res.new_password)
    } catch {
      show('No se pudo resetear la contraseña.', 'error')
    }
  }

  async function handleCreate() {
    if (!newEmail) return
    setCreating(true)
    try {
      const res = await adminCreateUser(newEmail, newRole, newFirstName, newLastName)
      setCreatedPassword(res.temporary_password)
      setShowCreate(false)
      setNewEmail('')
      setNewRole('recruiter')
      setNewFirstName('')
      setNewLastName('')
      load()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'No se pudo crear el usuario.'
      show(msg, 'error')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={cn(
            'text-sm px-4 py-2 rounded-lg',
            toast.kind === 'success'
              ? 'bg-emerald-500/20 text-emerald-300'
              : 'bg-red-500/20 text-red-400',
          )}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-slate-100 font-semibold">Usuarios del sistema</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
        >
          + Nuevo usuario
        </button>
      </div>

      {loading ? (
        <p className="text-slate-400 text-sm">Cargando...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-slate-800">
                {['Nombre', 'Email', 'Rol', 'Estado', 'Último login', 'Análisis', 'Acciones'].map((h) => (
                  <th key={h} className="pb-2 pr-4 text-slate-400 font-medium whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                  <td className="py-3 pr-4 text-slate-300 whitespace-nowrap">
                    {u.first_name || u.last_name
                      ? `${u.first_name ?? ''} ${u.last_name ?? ''}`.trim()
                      : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="py-3 pr-4 text-slate-200">{u.email}</td>
                  <td className="py-3 pr-4">
                    <span
                      className={cn(
                        'text-xs font-medium px-2 py-0.5 rounded',
                        u.role === 'admin'
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-sky-500/20 text-sky-300',
                      )}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge active={u.is_active} />
                  </td>
                  <td className="py-3 pr-4 text-slate-400 whitespace-nowrap">
                    {fmtDate(u.last_login)}
                  </td>
                  <td className="py-3 pr-4 text-slate-300">{u.analysis_count}</td>
                  <td className="py-3 pr-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleToggleActive(u)}
                        className={cn(
                          'text-xs px-2 py-1 rounded transition-colors',
                          u.is_active
                            ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                            : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30',
                        )}
                      >
                        {u.is_active ? 'Desactivar' : 'Activar'}
                      </button>
                      <button
                        onClick={() => handleResetPassword(u)}
                        className="text-xs px-2 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
                      >
                        Reset pass
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create user modal */}
      {showCreate && (
        <Modal title="Nuevo usuario" onClose={() => setShowCreate(false)}>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-slate-300 mb-1">Nombre</label>
                <input
                  type="text"
                  value={newFirstName}
                  onChange={(e) => setNewFirstName(e.target.value)}
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  placeholder="María"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-1">Apellido</label>
                <input
                  type="text"
                  value={newLastName}
                  onChange={(e) => setNewLastName(e.target.value)}
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                  placeholder="García"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Email</label>
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
                placeholder="usuario@ejemplo.com"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-300 mb-1">Rol</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as 'admin' | 'recruiter')}
                className="w-full rounded-lg bg-slate-800 border border-slate-700 text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="recruiter">Recruiter</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <p className="text-xs text-slate-500">
              Se generará una contraseña temporal que el usuario deberá cambiar al ingresar.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setShowCreate(false)}
              className="text-sm text-slate-400 hover:text-slate-200 px-3 py-1.5"
            >
              Cancelar
            </button>
            <button
              onClick={handleCreate}
              disabled={creating || !newEmail}
              className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
            >
              {creating ? 'Creando...' : 'Crear usuario'}
            </button>
          </div>
        </Modal>
      )}

      {/* Temporary password display */}
      {createdPassword && (
        <Modal title="Usuario creado" onClose={() => setCreatedPassword(null)}>
          <p className="text-sm text-slate-300">
            Copiá esta contraseña temporal —{' '}
            <span className="text-amber-400 font-semibold">no se va a mostrar de nuevo</span>.
          </p>
          <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 font-mono text-sky-300 text-sm select-all break-all">
            {createdPassword}
          </div>
          <div className="flex justify-end">
            <button
              onClick={() => {
                navigator.clipboard.writeText(createdPassword)
                show('Contraseña copiada.')
                setCreatedPassword(null)
              }}
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
            >
              Copiar y cerrar
            </button>
          </div>
        </Modal>
      )}

      {/* Reset password display */}
      {resetPassword && (
        <Modal title="Contraseña reseteada" onClose={() => setResetPassword(null)}>
          <p className="text-sm text-slate-300">
            Copiá esta contraseña temporal —{' '}
            <span className="text-amber-400 font-semibold">no se va a mostrar de nuevo</span>.
          </p>
          <div className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 font-mono text-sky-300 text-sm select-all break-all">
            {resetPassword}
          </div>
          <div className="flex justify-end">
            <button
              onClick={() => {
                navigator.clipboard.writeText(resetPassword)
                show('Contraseña copiada.')
                setResetPassword(null)
              }}
              className="bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
            >
              Copiar y cerrar
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}

// ── Tab 2 — Métricas ──────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-2xl font-bold text-slate-100">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

function MetricasTab() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminGetMetrics()
      .then(setMetrics)
      .catch(() => setError('No se pudieron cargar las métricas.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-400 text-sm">Cargando métricas...</p>
  if (error) return <p className="text-red-400 text-sm">{error}</p>
  if (!metrics) return null

  const chartData = fillDays(metrics.analyses_by_day)
  const maxCat = Math.max(...metrics.top_categories.map((c) => c.count), 1)

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total análisis" value={metrics.total_analyses} />
        <MetricCard label="Últimos 30 días" value={metrics.analyses_last_30_days} />
        <MetricCard
          label="Rating promedio"
          value={metrics.average_rating != null ? `${fmt(metrics.average_rating)} / 5` : '—'}
        />
        <MetricCard label="CVs en banco" value={metrics.total_cvs_in_bank} />
      </div>

      {/* Bar chart */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <p className="text-sm font-medium text-slate-300 mb-4">Análisis por día (últimos 30 días)</p>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="date"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              interval={4}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '8px',
                color: '#e2e8f0',
                fontSize: 12,
              }}
              cursor={{ fill: 'rgba(148,163,184,0.08)' }}
            />
            <Bar dataKey="count" name="Análisis" fill="#0ea5e9" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top categories */}
      {metrics.top_categories.length > 0 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p className="text-sm font-medium text-slate-300 mb-3">Top 5 categorías</p>
          <div className="space-y-2">
            {metrics.top_categories.map((c) => (
              <div key={c.slug} className="flex items-center gap-3">
                <span className="text-sm text-slate-300 w-48 truncate">{c.display_name}</span>
                <div className="flex-1 bg-slate-800 rounded-full h-2">
                  <div
                    className="bg-sky-500 h-2 rounded-full"
                    style={{ width: `${(c.count / maxCat) * 100}%` }}
                  />
                </div>
                <span className="text-sm text-slate-400 w-8 text-right">{c.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CV bank health */}
      <div>
        <p className="text-sm font-medium text-slate-300 mb-3">Estado del banco de CVs</p>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-emerald-300">{metrics.active_cvs}</p>
            <p className="text-xs text-emerald-400 mt-1">Activos</p>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-amber-300">{metrics.expiring_soon_cvs}</p>
            <p className="text-xs text-amber-400 mt-1">Próximos a expirar</p>
          </div>
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center">
            <p className="text-2xl font-bold text-red-400">{metrics.expired_cvs}</p>
            <p className="text-xs text-red-400 mt-1">Expirados</p>
          </div>
        </div>
      </div>

      {/* Users */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Usuarios totales" value={metrics.total_users} />
        <MetricCard label="Usuarios activos" value={metrics.active_users} />
      </div>
    </div>
  )
}

// ── Tab 3 — Banco de CVs ──────────────────────────────────────────────────────

function BancoCVsTab() {
  const [data, setData] = useState<CVListResponse | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expiring, setExpiring] = useState(false)
  const { toast, show } = useToast()

  const load = useCallback(async (p: number) => {
    try {
      setLoading(true)
      setError(null)
      setData(await adminListCVs(p))
    } catch {
      setError('No se pudo cargar el banco de CVs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(page) }, [load, page])

  async function handleExpire() {
    setExpiring(true)
    try {
      const res = await adminExpireCVs()
      show(`${res.expired} CV(s) expirado(s).`)
      load(page)
    } catch {
      show('Error al expirar CVs.', 'error')
    } finally {
      setExpiring(false)
    }
  }

  function cvStatus(cv: AdminCV) {
    if (cv.is_expired) return { label: 'Expirado', cls: 'bg-red-500/20 text-red-400' }
    if (cv.days_until_expiry <= 30) return { label: 'Por expirar', cls: 'bg-amber-500/20 text-amber-300' }
    return { label: 'Activo', cls: 'bg-emerald-500/20 text-emerald-300' }
  }

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={cn(
            'text-sm px-4 py-2 rounded-lg',
            toast.kind === 'success'
              ? 'bg-emerald-500/20 text-emerald-300'
              : 'bg-red-500/20 text-red-400',
          )}
        >
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-slate-100 font-semibold">Banco de CVs</h2>
        <button
          onClick={handleExpire}
          disabled={expiring}
          className="bg-red-600/80 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-medium px-4 py-1.5 rounded-lg transition-colors"
        >
          {expiring ? 'Expirando...' : 'Forzar expiración de CVs viejos'}
        </button>
      </div>

      {loading ? (
        <p className="text-slate-400 text-sm">Cargando...</p>
      ) : error ? (
        <p className="text-red-400 text-sm">{error}</p>
      ) : data ? (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-slate-800">
                  {['Nombre / Archivo', 'Email', 'Último uso', 'Encontrado', 'Estado', 'Días p/expirar'].map(
                    (h) => (
                      <th key={h} className="pb-2 pr-4 text-slate-400 font-medium whitespace-nowrap">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.items.map((cv) => {
                  const status = cvStatus(cv)
                  return (
                    <tr key={cv.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                      <td className="py-3 pr-4 max-w-[200px]">
                        <p className="text-slate-200 truncate">{cv.full_name ?? cv.filename}</p>
                        {cv.full_name && (
                          <p className="text-slate-500 text-xs truncate">{cv.filename}</p>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-slate-400 truncate max-w-[180px]">
                        {cv.email ?? '—'}
                      </td>
                      <td className="py-3 pr-4 text-slate-400 whitespace-nowrap">
                        {fmtDate(cv.last_seen_at)}
                      </td>
                      <td className="py-3 pr-4 text-slate-300">{cv.times_matched}</td>
                      <td className="py-3 pr-4">
                        <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', status.cls)}>
                          {status.label}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-slate-400">
                        {cv.is_expired ? '—' : `${cv.days_until_expiry}d`}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              {data.total} CV(s) en total · página {data.page} de {data.total_pages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Anterior
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Siguiente →
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}

// ── Tab 4 — Costos OpenAI ─────────────────────────────────────────────────────

const COST_ROWS: {
  label: string
  key: keyof CostsResponse
  unit: number
  breakdownKey: keyof CostsResponse['cost_breakdown']
}[] = [
  { label: 'Ranking (IA)', key: 'estimated_ranking_calls', unit: 0.005, breakdownKey: 'ranking' },
  { label: 'Clasificación de categoría', key: 'estimated_category_calls', unit: 0.001, breakdownKey: 'category' },
  { label: 'Extracción de contacto', key: 'estimated_contact_extraction_calls', unit: 0.001, breakdownKey: 'contact' },
  { label: 'Embeddings', key: 'estimated_embedding_calls', unit: 0.0001, breakdownKey: 'embeddings' },
]

function CostosTab() {
  const [costs, setCosts] = useState<CostsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    adminGetCosts()
      .then(setCosts)
      .catch(() => setError('No se pudieron cargar los costos estimados.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-400 text-sm">Cargando costos...</p>
  if (error) return <p className="text-red-400 text-sm">{error}</p>
  if (!costs) return null

  const perAnalysis =
    costs.total_analyses > 0
      ? costs.estimated_total_cost_usd / costs.total_analyses
      : 0

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          label="Costo total estimado"
          value={`$${fmt(costs.estimated_total_cost_usd, 4)} USD`}
          sub={`${costs.total_analyses} análisis procesados`}
        />
        <MetricCard
          label="Costo promedio por análisis"
          value={`$${fmt(perAnalysis, 4)} USD`}
        />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-800/40">
              {['Llamada', 'Cantidad', 'Costo unitario', 'Total'].map((h) => (
                <th key={h} className="px-4 py-3 text-slate-400 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COST_ROWS.map((row) => (
              <tr key={row.label} className="border-b border-slate-800/50">
                <td className="px-4 py-3 text-slate-200">{row.label}</td>
                <td className="px-4 py-3 text-slate-300">{costs[row.key] as number}</td>
                <td className="px-4 py-3 text-slate-400">${row.unit.toFixed(4)}</td>
                <td className="px-4 py-3 text-slate-300">
                  ${fmt(costs.cost_breakdown[row.breakdownKey], 4)}
                </td>
              </tr>
            ))}
            <tr className="bg-slate-800/30">
              <td className="px-4 py-3 text-slate-100 font-semibold" colSpan={3}>
                Total estimado
              </td>
              <td className="px-4 py-3 text-sky-300 font-semibold">
                ${fmt(costs.estimated_total_cost_usd, 4)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500 italic">
        Estos son costos estimados basados en uso promedio. Los costos reales pueden variar según
        el modelo, la longitud de los textos y los precios vigentes de OpenAI.
      </p>
    </div>
  )
}

// ── AdminPage ──────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'usuarios', label: 'Usuarios' },
  { id: 'metricas', label: 'Métricas' },
  { id: 'banco', label: 'Banco de CVs' },
  { id: 'costos', label: 'Costos OpenAI' },
] as const

type TabId = (typeof TABS)[number]['id']

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>('usuarios')

  return (
    <div className="min-h-screen bg-[#111118] px-4 py-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Panel de <span className="text-amber-400">administración</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Gestión de usuarios, métricas del sistema y banco de CVs.
          </p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 border-b border-slate-800">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-amber-400 text-amber-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200',
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div>
          {activeTab === 'usuarios' && <UsuariosTab />}
          {activeTab === 'metricas' && <MetricasTab />}
          {activeTab === 'banco' && <BancoCVsTab />}
          {activeTab === 'costos' && <CostosTab />}
        </div>
      </div>
    </div>
  )
}
