import { NavLink } from 'react-router-dom'
import { cn } from '../lib/utils'

const LINKS = [
  { to: '/',       label: 'Analizar',        end: true  },
  { to: '/match',  label: 'Buscar en banco',  end: false },
  { to: '/upload', label: 'Subir CV',         end: false },
]

export default function NavBar() {
  return (
    <nav className="sticky top-0 z-10 bg-white border-b border-gray-200">
      <div className="max-w-3xl mx-auto px-4 flex items-center gap-6 h-14">
        <span className="font-bold text-gray-900 text-base mr-2">CV Analyzer AI</span>
        {LINKS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'text-sm font-medium pb-1 border-b-2 transition-colors',
                isActive
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-800',
              )
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
