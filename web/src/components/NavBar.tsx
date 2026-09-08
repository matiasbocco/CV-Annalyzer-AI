import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { cn } from '../lib/utils'
import { clearToken, getToken, getUser } from '../auth'
import { logout } from '../api/endpoints'

const LINKS = [
  { to: '/',         label: 'Analizar CVs',    end: true  },
  { to: '/match',    label: 'Buscar en banco', end: false },
  { to: '/history',  label: 'Historial',       end: false },
  { to: '/upload',   label: 'Subir CV',        end: false },
]

export default function NavBar() {
  const navigate = useNavigate()
  const isLoggedIn = !!getToken()
  const user = getUser()
  const [menuOpen, setMenuOpen] = useState(false)

  async function handleLogout() {
    try {
      await logout()
    } finally {
      clearToken()
      navigate('/login', { replace: true })
    }
  }

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'text-sm font-medium pb-1 border-b-2 transition-colors',
      isActive
        ? 'border-sky-500 text-sky-400'
        : 'border-transparent text-slate-400 hover:text-slate-200',
    )

  const adminLinkClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      'text-sm font-medium pb-1 border-b-2 transition-colors',
      isActive
        ? 'border-amber-400 text-amber-300'
        : 'border-transparent text-amber-500 hover:text-amber-300',
    )

  // Full link list (reused by desktop row and mobile dropdown).
  const links = (onClick?: () => void) => (
    <>
      {LINKS.map(({ to, label, end }) => (
        <NavLink key={to} to={to} end={end} onClick={onClick} className={navLinkClass}>
          {label}
        </NavLink>
      ))}
      {user?.role === 'admin' && (
        <NavLink to="/admin" onClick={onClick} className={adminLinkClass}>
          Admin
        </NavLink>
      )}
    </>
  )

  const userInfo = (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 truncate max-w-[160px]">
        {user?.first_name
          ? `${user.first_name}${user.last_name ? ' ' + user.last_name : ''}`
          : user?.email}
      </span>
      {user && (
        <span
          className={cn(
            'text-xs font-medium px-1.5 py-0.5 rounded flex-shrink-0',
            user.role === 'admin'
              ? 'bg-amber-500/20 text-amber-300'
              : 'bg-sky-500/20 text-sky-300',
          )}
        >
          {user.role}
        </span>
      )}
    </div>
  )

  return (
    <nav className="sticky top-0 z-10 bg-[#111118]/95 backdrop-blur-sm border-b border-slate-800">
      <div className="max-w-4xl mx-auto px-4 flex items-center gap-6 h-14">
        <span className="font-bold text-slate-100 text-sm tracking-tight mr-2">
          CV Analyzer<span className="text-sky-500"> AI</span>
        </span>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-6">{links()}</div>

        {isLoggedIn && (
          <div className="ml-auto flex items-center gap-3">
            {/* User info + logout only inline on desktop */}
            <div className="hidden md:flex items-center gap-3">
              {userInfo}
              <button
                onClick={handleLogout}
                className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cerrar sesión
              </button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="md:hidden text-slate-300 hover:text-slate-100 transition-colors"
              aria-label="Menú"
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        )}
      </div>

      {/* Mobile dropdown menu */}
      {isLoggedIn && menuOpen && (
        <div className="md:hidden border-t border-slate-800 bg-[#111118] px-4 py-4 flex flex-col gap-4">
          {links(() => setMenuOpen(false))}
          <div className="border-t border-slate-800 pt-3 flex items-center justify-between">
            {userInfo}
            <button
              onClick={handleLogout}
              className="text-sm text-slate-400 hover:text-slate-200 transition-colors flex-shrink-0"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
