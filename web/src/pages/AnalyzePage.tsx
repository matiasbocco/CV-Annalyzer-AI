import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import { useAnalyzeCVs } from '../api/hooks'
import { cn, formatScore, getNivelColor } from '../lib/utils'
import type { AnalyzeResponse, Availability, Candidate, ContactInfo } from '../api/types'

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyzePage() {
  const [files, setFiles]               = useState<File[]>([])
  const [jobDescription, setJobDescription] = useState('')
  const [includeBank, setIncludeBank]   = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  const analyze = useAnalyzeCVs()

  const onDrop = useCallback((accepted: File[]) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...accepted.filter(f => !existing.has(f.name))]
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  function removeFile(name: string) {
    setFiles(prev => prev.filter(f => f.name !== name))
  }

  function validate(): string | null {
    if (files.length === 0) return 'Select at least one PDF file.'
    if (jobDescription.trim().length < 50) return 'Job description must be at least 50 characters.'
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    analyze.mutate({ files, jobDescription: jobDescription.trim(), includeBank })
  }

  function resetAll() {
    analyze.reset()
    setFiles([])
    setJobDescription('')
    setIncludeBank(false)
    setValidationError(null)
  }

  // ── Views ──────────────────────────────────────────────────────────────────

  if (analyze.isPending) return <LoadingScreen />

  if (analyze.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white border border-red-200 rounded-lg p-6 space-y-4">
          <h2 className="text-lg font-semibold text-red-700">Analysis failed</h2>
          <p className="text-sm text-gray-600">{getErrorMessage(analyze.error)}</p>
          <button
            onClick={() => analyze.reset()}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            ← Try again
          </button>
        </div>
      </div>
    )
  }

  if (analyze.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Results</h1>
            <button
              onClick={resetAll}
              className="text-sm bg-white border border-gray-200 px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
            >
              + New analysis
            </button>
          </div>
          <ResultsView data={analyze.data} />
        </div>
      </div>
    )
  }

  // Default: form (idle)
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Analyze Candidates</h1>

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-lg p-6 space-y-5">

          {/* Dropzone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              CV Files <span className="text-gray-400 font-normal">(PDF)</span>
            </label>
            <div
              {...getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
                isDragActive
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400',
              )}
            >
              <input {...getInputProps()} />
              <p className="text-sm text-gray-500">
                {isDragActive
                  ? 'Drop the PDFs here…'
                  : 'Drag & drop PDFs here, or click to browse'}
              </p>
            </div>

            {files.length > 0 && (
              <ul className="mt-2 space-y-1">
                {files.map(f => (
                  <li
                    key={f.name}
                    className="flex items-center justify-between text-sm bg-gray-50 border border-gray-200 rounded px-3 py-1.5"
                  >
                    <span className="text-gray-700 truncate">{f.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(f.name)}
                      className="ml-3 text-gray-400 hover:text-red-500 flex-shrink-0 text-lg leading-none"
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Job description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Job Description{' '}
              <span className="text-gray-400 font-normal">(min 50 chars)</span>
            </label>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              rows={6}
              placeholder="Paste the full job description here…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 resize-y"
            />
            <p className={cn(
              'text-xs mt-1',
              jobDescription.length >= 50 ? 'text-green-600' : 'text-gray-400',
            )}>
              {jobDescription.length} chars{' '}
              {jobDescription.length < 50
                ? `(${50 - jobDescription.length} more needed)`
                : '✓'}
            </p>
          </div>

          {/* Bank checkbox */}
          <label className="flex items-start gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeBank}
              onChange={e => setIncludeBank(e.target.checked)}
              className="mt-0.5 w-4 h-4 cursor-pointer"
            />
            <span className="text-sm text-gray-700">
              Include candidates from the CV bank
              <span className="block text-xs text-gray-400 mt-0.5">
                Bank candidates are added to the ranking alongside uploaded CVs.
              </span>
            </span>
          </label>

          {/* Validation error */}
          {validationError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {validationError}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Analyze
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Loading screen ────────────────────────────────────────────────────────────

function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      <p className="text-gray-600 animate-pulse">
        Analyzing CVs… this can take 15–30 seconds
      </p>
    </div>
  )
}

// ── Results view ──────────────────────────────────────────────────────────────

function ResultsView({ data }: { data: AnalyzeResponse }) {
  return (
    <div className="space-y-6">
      {/* Job summary */}
      <div className="bg-indigo-50 border-l-4 border-indigo-500 rounded-r-lg p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 mb-1">
          Ideal Candidate Profile
        </p>
        <p className="text-sm text-gray-700 leading-relaxed">{data.job_summary}</p>
      </div>

      {/* Category badge */}
      {data.category && (
        <span className="inline-flex items-center gap-1.5 bg-purple-100 text-purple-800 text-xs font-semibold px-3 py-1 rounded-full">
          🏷 {data.category.display_name}
        </span>
      )}

      {/* Ranking table */}
      <RankingTable ranking={data.ranking} />

      {/* Detail cards */}
      <div className="space-y-4">
        {data.ranking.map((c, i) => (
          <CandidateCard key={c.filename} position={i + 1} candidate={c} />
        ))}
      </div>
    </div>
  )
}

// ── Ranking table ─────────────────────────────────────────────────────────────

function RankingTable({ ranking }: { ranking: Candidate[] }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-10">#</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Candidate</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-20">Score</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-24">Nivel</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-28">Source</th>
          </tr>
        </thead>
        <tbody>
          {ranking.map((c, i) => (
            <tr key={c.filename} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
              <td className="px-4 py-3 text-gray-400 font-medium">{i + 1}</td>
              <td className="px-4 py-3">
                <span className="font-medium text-gray-800">
                  {c.contact?.full_name ?? c.filename}
                </span>
                {c.contact?.full_name && (
                  <span className="block text-xs text-gray-400 font-mono">{c.filename}</span>
                )}
              </td>
              <td className="px-4 py-3 text-blue-600 font-bold text-base">
                {formatScore(c.score)}
              </td>
              <td className="px-4 py-3">
                <span className={cn(
                  'text-xs font-semibold px-2 py-0.5 rounded-full capitalize',
                  getNivelColor(c.nivel),
                )}>
                  {c.nivel}
                </span>
              </td>
              <td className="px-4 py-3">
                <SourceBadge source={c.source} recencyFactor={c.recency_factor_applied} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Candidate detail card ─────────────────────────────────────────────────────

function CandidateCard({ position, candidate: c }: { position: number; candidate: Candidate }) {
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
        <BulletList title="Strengths"       items={c.strengths}       color="text-green-600" />
        <BulletList title="Gaps"            items={c.gaps}            color="text-red-500" />
        <BulletList title="Recommendations" items={c.recommendations} color="text-blue-600" />
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-600 italic border-l-2 border-gray-200 pl-3 leading-relaxed">
        {c.summary}
      </p>
    </div>
  )
}

// ── Contact section ───────────────────────────────────────────────────────────

const AVAIL_COLORS: Record<NonNullable<Availability>, string> = {
  available:   'bg-green-100 text-green-700',
  open:        'bg-blue-100  text-blue-700',
  not_looking: 'bg-red-100   text-red-600',
}
const AVAIL_LABELS: Record<NonNullable<Availability>, string> = {
  available:   'Disponible',
  open:        'Abierto',
  not_looking: 'No busca',
}

function ContactSection({ contact }: { contact: ContactInfo }) {
  const hasAny = contact.email || contact.phone || contact.location || contact.availability
  if (!hasAny) return null

  const phoneDigits = contact.phone?.replace(/\D/g, '') ?? ''

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Contact</p>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
        {contact.email    && <span>✉ {contact.email}</span>}
        {contact.phone    && <span>📞 {contact.phone}</span>}
        {contact.location && <span>📍 {contact.location}</span>}
        {contact.availability != null && (
          <span className={cn(
            'text-xs font-semibold px-2 py-0.5 rounded-full',
            AVAIL_COLORS[contact.availability],
          )}>
            {AVAIL_LABELS[contact.availability]}
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

// ── Small helpers ─────────────────────────────────────────────────────────────

function SourceBadge({ source, recencyFactor }: { source: 'uploaded' | 'bank'; recencyFactor: number }) {
  if (source === 'uploaded') {
    return (
      <span className="text-xs font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
        Uploaded
      </span>
    )
  }
  const suffix = recencyFactor < 1.0 ? ` · ${recencyFactor}×` : ''
  return (
    <span className="text-xs font-semibold bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
      From bank{suffix}
    </span>
  )
}

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

function CopyEmailButton({ email }: { email: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(email)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard unavailable (non-HTTPS or permissions denied)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="text-xs border border-gray-200 bg-white text-gray-600 px-2.5 py-1 rounded hover:bg-gray-50"
    >
      {copied ? '✓ Copied' : '✉ Copy email'}
    </button>
  )
}

// ── Error utility ─────────────────────────────────────────────────────────────

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join(', ')
    if (error.response?.status === 422) return 'Invalid request — check your files and job description.'
    return error.message
  }
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred.'
}
