import { NavLink, useNavigate } from 'react-router-dom'
import { cn } from '../lib/utils'
import { clearToken, getToken, getUser } from '../auth'
import { logout } from '../api/endpoints'

const LINKS = [
  { to: '/',       label: 'Analizar CVs',    end: true  },
  { to: '/match',  label: 'Buscar en banco', end: false },
  { to: '/upload', label: 'Subir CV',        end: false },
]

export default function NavBar() {
  const navigate = useNavigate()
  const isLoggedIn = !!getToken()
  const user = getUser()

  async function handleLogout() {
    try {
      await logout()
    } finally {
      clearToken()
      navigate('/login', { replace: true })
    }
  }

  return (
    <nav className="sticky top-0 z-10 bg-[#111118]/95 backdrop-blur-sm border-b border-slate-800">
      <div className="max-w-4xl mx-auto px-4 flex items-center gap-6 h-14">
        <span className="font-bold text-slate-100 text-sm tracking-tight mr-2">
          CV Analyzer<span className="text-sky-500"> AI</span>
        </span>

        {LINKS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'text-sm font-medium pb-1 border-b-2 transition-colors',
                isActive
                  ? 'border-sky-500 text-sky-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200',
              )
            }
          >
            {label}
          </NavLink>
        ))}

        {user?.role === 'admin' && (
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              cn(
                'text-sm font-medium pb-1 border-b-2 transition-colors',
                isActive
                  ? 'border-amber-400 text-amber-300'
                  : 'border-transparent text-amber-500 hover:text-amber-300',
              )
            }
          >
            Admin
          </NavLink>
        )}

        {isLoggedIn && (
          <div className="ml-auto flex items-center gap-3">
            {user && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">{user.email}</span>
                <span
                  className={cn(
                    'text-xs font-medium px-1.5 py-0.5 rounded',
                    user.role === 'admin'
                      ? 'bg-amber-500/20 text-amber-300'
                      : 'bg-sky-500/20 text-sky-300',
                  )}
                >
                  {user.role}
                </span>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cerrar sesión
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}
