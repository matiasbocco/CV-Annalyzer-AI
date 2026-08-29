// In-memory token and user store — never persisted to localStorage (XSS risk).
// The refresh token lives in an httpOnly cookie managed by the browser/backend.

export interface UserInfo {
  id: string
  email: string
  role: 'admin' | 'recruiter'
}

let _accessToken: string | null = null
let _user: UserInfo | null = null

export function getToken(): string | null {
  return _accessToken
}

export function setToken(token: string): void {
  _accessToken = token
}

export function clearToken(): void {
  _accessToken = null
  _user = null
}

export function getUser(): UserInfo | null {
  return _user
}

export function setUser(user: UserInfo): void {
  _user = user
}

export function clearUser(): void {
  _user = null
}
