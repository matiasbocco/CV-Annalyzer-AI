import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import axios from 'axios'
import type { Nivel } from '../api/types'

export type Lang = 'es' | 'en'

export function detectLang(text: string): Lang {
  if (!text.trim()) return 'es'
  const lower = text.toLowerCase()
  const esScore =
    (lower.match(/[áéíóúñü]/g)?.length ?? 0) * 3 +
    (lower.match(/\b(para|con|los|las|del|una|que|por|como|este|esta|son|más|también|equipo|empresa|busca|años|experiencia)\b/g)?.length ?? 0)
  const enScore =
    (lower.match(/\b(the|and|for|with|our|will|have|this|that|are|from|you|your|we|job|team|company|years|experience|looking|required|position|role)\b/g)?.length ?? 0)
  return esScore >= enScore ? 'es' : 'en'
}

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
    excelente: 'bg-sky-600 text-white',
    alto:      'bg-blue-700/60 text-blue-200',
    medio:     'bg-blue-900/60 text-blue-300',
    bajo:      'bg-slate-700 text-slate-300',
  }
  return map[nivel] ?? 'bg-slate-700 text-slate-400'
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
