import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { getToken, setToken, setUser } from '../auth'
import type { RefreshResponse } from '../api/types'
import client from '../api/client'

type State = 'checking' | 'authenticated' | 'unauthenticated'

/**
 * Wraps routes that require a valid access token.
 *
 * On first render: if no token is in memory, attempts a silent refresh using
 * the httpOnly cookie (user may have a live session from before a page reload).
 * If refresh succeeds the user is let through; if it fails they go to /login.
 */
export default function ProtectedRoute() {
  const [state, setState] = useState<State>(
    getToken() ? 'authenticated' : 'checking',
  )

  useEffect(() => {
    if (state !== 'checking') return

    client
      .post<RefreshResponse>('/auth/refresh')
      .then((res) => {
        setToken(res.data.access_token)
        setUser(res.data.user)
        setState('authenticated')
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

  if (state === 'unauthenticated') {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
