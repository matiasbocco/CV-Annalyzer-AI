import { useState } from 'react'
import { cn, formatScore, getNivelColor } from '../lib/utils'
import { T, useLang } from '../LangContext'
import type { Availability, Candidate, ContactInfo } from '../api/types'

const AVAIL_COLORS: Record<NonNullable<Availability>, string> = {
  available:   'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  open:        'bg-sky-500/20 text-sky-400 border border-sky-500/30',
  not_looking: 'bg-red-500/20 text-red-400 border border-red-500/30',
}

// ── SourceBadge ───────────────────────────────────────────────────────────────

export function SourceBadge({
  source,
  recencyFactor,
}: {
  source: 'uploaded' | 'bank'
  recencyFactor: number
}) {
  const t = T[useLang()]
  if (source === 'uploaded') {
    return (
      <span className="text-xs font-semibold bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
        {t.sourceUploaded}
      </span>
    )
  }
  const suffix = recencyFactor < 1.0 ? ` · ${recencyFactor}×` : ''
  return (
    <span className="text-xs font-semibold bg-blue-900/50 text-blue-300 px-2 py-0.5 rounded-full">
      {t.sourceBank}{suffix}
    </span>
  )
}

// ── ContactSection ────────────────────────────────────────────────────────────

function ContactSection({ contact }: { contact: ContactInfo }) {
  const t = T[useLang()]
  const hasAny = contact.email || contact.phone || contact.location || contact.availability
  if (!hasAny) return null

  const phoneDigits = contact.phone?.replace(/\D/g, '') ?? ''

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t.contact}</p>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-400">
        {contact.email    && <span>✉ {contact.email}</span>}
        {contact.phone    && <span>📞 {contact.phone}</span>}
        {contact.location && <span>📍 {contact.location}</span>}
        {contact.availability != null && (
          <span className={cn(
            'text-xs font-semibold px-2 py-0.5 rounded-full',
            AVAIL_COLORS[contact.availability],
          )}>
            {t[contact.availability === 'not_looking' ? 'notLooking' : contact.availability]}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {contact.email && <CopyEmailButton email={contact.email} />}
        {contact.linkedin_url && (
          <a
            href={contact.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs border border-slate-700 bg-slate-800 text-slate-400 px-2.5 py-1 rounded hover:bg-slate-700 hover:text-slate-200 transition-colors"
          >
            in LinkedIn
          </a>
        )}
        {phoneDigits && (
          <a
            href={`https://wa.me/${phoneDigits}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs border border-slate-700 bg-slate-800 text-slate-400 px-2.5 py-1 rounded hover:bg-slate-700 hover:text-slate-200 transition-colors"
          >
            📱 WhatsApp
          </a>
        )}
        {contact.portfolio_url && (
          <a
            href={contact.portfolio_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs border border-slate-700 bg-slate-800 text-slate-400 px-2.5 py-1 rounded hover:bg-slate-700 hover:text-slate-200 transition-colors"
          >
            🔗 Portfolio
          </a>
        )}
      </div>
    </div>
  )
}

// ── BulletList ────────────────────────────────────────────────────────────────

function BulletList({ title, items, color }: { title: string; items: string[]; color: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1.5">{title}</p>
      {items.length > 0 ? (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className={cn('text-xs leading-snug', color)}>
              <span className="mr-1 select-none opacity-60">•</span>{item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-600">—</p>
      )}
    </div>
  )
}

// ── CopyEmailButton ───────────────────────────────────────────────────────────

function CopyEmailButton({ email }: { email: string }) {
  const t = T[useLang()]
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(email)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard unavailable */ }
  }

  return (
    <button
      onClick={handleCopy}
      className="text-xs border border-slate-700 bg-slate-800 text-slate-400 px-2.5 py-1 rounded hover:bg-slate-700 hover:text-slate-200 transition-colors"
    >
      {copied ? t.copied : t.copyEmail}
    </button>
  )
}

// ── CandidateCard ─────────────────────────────────────────────────────────────

export default function CandidateCard({
  position,
  candidate: c,
}: {
  position: number
  candidate: Candidate
}) {
  const t = T[useLang()]
  const name = c.contact?.full_name ?? c.filename

  const SCORE_LABELS: Record<string, string> = {
    technical_skills: 'Técnico',
    experience:       'Experiencia',
    education:        'Educación',
    soft_skills:      'Soft skills',
  }

  return (
    <div className="bg-[#111118] border border-slate-800 rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-sky-500 flex items-center justify-center text-white font-bold text-sm">
          {position}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-slate-100 text-base truncate">{name}</p>
            <span className="text-sky-400 font-bold text-lg leading-none">
              {formatScore(c.score)}
            </span>
            {c.original_score !== null && c.original_score !== undefined && (
              <span className="text-xs text-slate-500">orig. {c.original_score}</span>
            )}
          </div>
          {c.contact?.full_name && (
            <p className="text-xs text-slate-600 font-mono truncate">{c.filename}</p>
          )}
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className={cn(
              'text-xs font-semibold px-2 py-0.5 rounded-full capitalize',
              getNivelColor(c.nivel),
            )}>
              {c.nivel}
            </span>
            <SourceBadge source={c.source} recencyFactor={c.recency_factor_applied} />
          </div>
        </div>
      </div>

      {/* Score bars */}
      <div className="space-y-2">
        {(Object.entries(c.detailed_scores) as [string, number][]).map(([key, val]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-24 flex-shrink-0">
              {SCORE_LABELS[key] ?? key.replace(/_/g, ' ')}
            </span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-sky-500 rounded-full transition-all"
                style={{ width: `${val}%` }}
              />
            </div>
            <span className="text-xs font-medium text-slate-400 w-6 text-right flex-shrink-0">
              {val}
            </span>
          </div>
        ))}
      </div>

      {/* Contact */}
      {c.contact && <ContactSection contact={c.contact} />}

      <div className="border-t border-slate-800" />

      {/* Strengths / Gaps / Recommendations */}
      <div className="grid gap-4 sm:grid-cols-3">
        <BulletList title={t.strengths}       items={c.strengths}       color="text-emerald-400" />
        <BulletList title={t.gaps}            items={c.gaps}            color="text-red-400" />
        <BulletList title={t.recommendations} items={c.recommendations} color="text-sky-400" />
      </div>

      {/* Summary */}
      <p className="text-sm text-slate-400 italic border-l-2 border-slate-700 pl-3 leading-relaxed">
        {c.summary}
      </p>
    </div>
  )
}
