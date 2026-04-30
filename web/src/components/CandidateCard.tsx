import { useState } from 'react'
import { cn, formatScore, getNivelColor } from '../lib/utils'
import { T, useLang } from '../LangContext'
import type { Availability, Candidate, ContactInfo } from '../api/types'

// ── Availability color map (keys don't change with lang) ──────────────────────

const AVAIL_COLORS: Record<NonNullable<Availability>, string> = {
  available:   'bg-green-100 text-green-700',
  open:        'bg-blue-100  text-blue-700',
  not_looking: 'bg-red-100   text-red-600',
}

// ── SourceBadge (also exported for RankingTable) ──────────────────────────────

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
      <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
        {t.sourceUploaded}
      </span>
    )
  }
  const suffix = recencyFactor < 1.0 ? ` · ${recencyFactor}×` : ''
  return (
    <span className="text-xs font-semibold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
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
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{t.contact}</p>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
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
            className="text-xs border border-gray-200 bg-white text-gray-600 px-2.5 py-1 rounded hover:bg-gray-50"
          >
            in LinkedIn
          </a>
        )}
        {phoneDigits && (
          <a
            href={`https://wa.me/${phoneDigits}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs border border-gray-200 bg-white text-gray-600 px-2.5 py-1 rounded hover:bg-gray-50"
          >
            📱 WhatsApp
          </a>
        )}
        {contact.portfolio_url && (
          <a
            href={contact.portfolio_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs border border-gray-200 bg-white text-gray-600 px-2.5 py-1 rounded hover:bg-gray-50"
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
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1.5">{title}</p>
      {items.length > 0 ? (
        <ul className="space-y-1">
          {items.map((item, i) => (
            <li key={i} className={cn('text-xs leading-snug', color)}>
              <span className="mr-1 select-none">•</span>{item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-gray-300">—</p>
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
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="text-xs border border-gray-200 bg-white text-gray-600 px-2.5 py-1 rounded hover:bg-gray-50"
    >
      {copied ? t.copied : t.copyEmail}
    </button>
  )
}

// ── CandidateCard (default export) ───────────────────────────────────────────

export default function CandidateCard({
  position,
  candidate: c,
}: {
  position: number
  candidate: Candidate
}) {
  const t = T[useLang()]
  const name = c.contact?.full_name ?? c.filename

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-3xl font-black text-blue-600 leading-none min-w-[2.5rem]">
          {formatScore(c.score)}
        </span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 text-base">
            <span className="text-gray-400 mr-1.5 font-normal text-sm">#{position}</span>
            {name}
          </p>
          {c.contact?.full_name && (
            <p className="text-xs text-gray-400 font-mono truncate">{c.filename}</p>
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
      <div className="space-y-1.5">
        {(Object.entries(c.detailed_scores) as [string, number][]).map(([key, val]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-32 capitalize flex-shrink-0">
              {key.replace(/_/g, ' ')}
            </span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${val}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-700 w-6 text-right flex-shrink-0">
              {val}
            </span>
          </div>
        ))}
      </div>

      {/* Contact */}
      {c.contact && <ContactSection contact={c.contact} />}

      <hr className="border-gray-100" />

      {/* Strengths / Gaps / Recommendations */}
      <div className="grid gap-4 sm:grid-cols-3">
        <BulletList title={t.strengths}        items={c.strengths}       color="text-green-600" />
        <BulletList title={t.gaps}             items={c.gaps}            color="text-red-500" />
        <BulletList title={t.recommendations}  items={c.recommendations} color="text-blue-600" />
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-600 italic border-l-2 border-gray-200 pl-3 leading-relaxed">
        {c.summary}
      </p>
    </div>
  )
}
