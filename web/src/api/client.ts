import axios from 'axios'
import { clearToken, getToken, setToken } from '../auth'

// In production, set VITE_API_URL at build time (e.g. VITE_API_URL=https://api.example.com).
// Falls back to localhost:8000 when unset, matching local dev with no extra setup.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Separate instance used ONLY for token refresh to avoid interceptor recursion.
// No request/response interceptors — failure propagates as-is to the caller.
const _refreshClient = axios.create({ baseURL: BASE_URL, withCredentials: true })

/** Silent token refresh using the httpOnly cookie. Throws on any failure (401, network, etc.). */
export async function refreshSession(): Promise<import('../api/types').RefreshResponse> {
  const { data } = await _refreshClient.post<import('../api/types').RefreshResponse>('/auth/refresh')
  return data
}

const client = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // sends the httpOnly refresh_token cookie automatically
})

// Attach Bearer token to every outgoing request.
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Coalesce concurrent refresh calls into a single in-flight promise.
let _refreshPromise: Promise<string | null> | null = null

function attemptRefresh(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = _refreshClient
    .post<{ access_token: string }>('/auth/refresh')
    .then((res) => {
      setToken(res.data.access_token)
      return res.data.access_token
    })
    .catch(() => {
      clearToken()
      window.location.href = '/login'
      return null
    })
    .finally(() => {
      _refreshPromise = null
    })

  return _refreshPromise
}

// On 401: attempt a silent token refresh, then retry the original request once.
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config

    // Skip refresh if this is already a retry, or if the request itself was /auth/refresh.
    if (
      error.response?.status !== 401 ||
      original._retry ||
      original.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error)
    }

    original._retry = true
    const newToken = await attemptRefresh()

    if (!newToken) {
      return Promise.reject(error)
    }

    original.headers.Authorization = `Bearer ${newToken}`
    return client(original)
  },
)

export default client
