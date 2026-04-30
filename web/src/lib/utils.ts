import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import axios from 'axios'
import type { Nivel } from '../api/types'

/**
 * Merge Tailwind classes safely.
 * clsx handles conditional/array logic; twMerge resolves conflicting
 * utility classes (e.g. `p-2` + `p-4` → `p-4` instead of both).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Render a 0–100 score as a plain integer string. */
export function formatScore(score: number): string {
  return String(Math.round(score))
}

/**
 * Map a nivel to a Tailwind badge class pair (bg + text).
 * Returns a string you can spread directly into className.
 */
export function getNivelColor(nivel: Nivel): string {
  const map: Record<Nivel, string> = {
    excelente: 'bg-green-100 text-green-700',
    alto:      'bg-blue-100  text-blue-700',
    medio:     'bg-amber-100 text-amber-700',
    bajo:      'bg-red-100   text-red-600',
  }
  return map[nivel] ?? 'bg-gray-100 text-gray-600'
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail))
      return detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(', ')
    if (error.response?.status === 422)
      return 'Solicitud inválida — revisá los archivos y la descripción del puesto.'
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'Ocurrió un error inesperado.'
}
