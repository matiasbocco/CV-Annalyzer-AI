import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { getToken, getUser, setToken, setUser } from '../auth'
import { refreshSession } from '../api/client'

type State = 'checking' | 'authenticated' | 'unauthenticated' | 'forbidden'

function deriveInitialState(): State {
  if (!getToken()) return 'checking'
  const user = getUser()
  if (!user) return 'checking'
  return user.role === 'admin' ? 'authenticated' : 'forbidden'
}

/**
 * Like ProtectedRoute but also enforces role="admin".
 * - No token / failed refresh → /login
 * - Authenticated but role="recruiter" → / (home)
 */
export default function AdminRoute() {
  const [state, setState] = useState<State>(deriveInitialState)

  useEffect(() => {
    if (state !== 'checking') return

    refreshSession()
      .then((res) => {
        setToken(res.access_token)
        setUser(res.user)
        setState(res.user.role === 'admin' ? 'authenticated' : 'forbidden')
      })
      .catch(() => {
        setState('unauthenticated')
      })
  }, [state])

  if (state === 'checking') {
    return (
      <div className="min-h-screen bg-[#111118] flex items-center justify-center">
        <span className="text-slate-400 text-sm">Verificando sesión...</span>
      </div>
    )
  }

  if (state === 'unauthenticated') return <Navigate to="/login" replace />
  if (state === 'forbidden') return <Navigate to="/" replace />

  return <Outlet />
}
