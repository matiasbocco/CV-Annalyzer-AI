import { NavLink } from 'react-router-dom'
import { cn } from '../lib/utils'

const LINKS = [
  { to: '/',       label: 'Analizar CVs',    end: true  },
  { to: '/match',  label: 'Buscar en banco', end: false },
  { to: '/upload', label: 'Subir CV',        end: false },
]

export default function NavBar() {
  return (
    <nav className="sticky top-0 z-10 bg-[#111118]/95 backdrop-blur-sm border-b border-slate-800">
      <div className="max-w-4xl mx-auto px-4 flex items-center gap-8 h-14">
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
      </div>
    </nav>
  )
}
