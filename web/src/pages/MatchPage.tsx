import { useState } from 'react'
import { useMatchJob, useJobStatus } from '../api/hooks'
import { cn, detectLang, getErrorMessage } from '../lib/utils'
import type { Lang } from '../lib/utils'
import { LangProvider, T } from '../LangContext'
import type { AnalyzeResponse } from '../api/types'
import RankingTable from '../components/RankingTable'
import CandidateCard from '../components/CandidateCard'
import AsyncLoadingScreen from '../components/AsyncLoadingScreen'

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MatchPage() {
  const [jobDescription, setJobDescription]   = useState('')
  const [topN, setTopN]                       = useState(10)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [lang, setLang]                       = useState<Lang>('es')
  const [jobId, setJobId]                     = useState<string | null>(null)

  const match     = useMatchJob()
  const jobStatus = useJobStatus(jobId)

  const JD_MIN = 50
  const JD_MAX = 3000

  function validate(): string | null {
    if (jobDescription.trim().length < JD_MIN) return `La descripción debe tener al menos ${JD_MIN} caracteres.`
    if (jobDescription.length > JD_MAX) return `La descripción no puede superar los ${JD_MAX} caracteres.`
    if (topN < 1 || topN > 20) return 'El número de candidatos debe estar entre 1 y 20.'
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    setLang(detectLang(jobDescription))
    match.mutate(
      { jobDescription: jobDescription.trim(), topN },
      { onSuccess: data => setJobId(data.job_id) },
    )
  }

  function resetAll() {
    match.reset()
    setJobDescription('')
    setValidationError(null)
    setJobId(null)
  }

  // ── Views ──────────────────────────────────────────────────────────────────

  const isProcessing =
    match.isPending ||
    (jobId !== null &&
      jobStatus.data?.status !== 'completed' &&
      jobStatus.data?.status !== 'failed')

  if (isProcessing) return <AsyncLoadingScreen mode="match" />

  if (match.isError || (jobId && jobStatus.data?.status === 'failed')) {
    const msg = match.isError
      ? getErrorMessage(match.error)
      : (jobStatus.data?.error ?? 'La búsqueda falló.')
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-[#111118] border border-red-500/30 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-red-400">Error al buscar</h2>
          <p className="text-sm text-slate-400">{msg}</p>
          <button
            onClick={resetAll}
            className="text-sm bg-slate-800 text-slate-300 border border-slate-700 px-4 py-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            ← Volver
          </button>
        </div>
      </div>
    )
  }

  if (jobId && jobStatus.data?.status === 'completed' && jobStatus.data.result) {
    const data = jobStatus.data.result as AnalyzeResponse
    const t = T[lang]
    return (
      <LangProvider value={lang}>
        <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
          <div className="max-w-3xl mx-auto space-y-5">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-slate-100">Candidatos del banco</h1>
              <button
                onClick={resetAll}
                className="text-sm bg-slate-800 border border-slate-700 text-slate-400 px-4 py-2 rounded-lg hover:bg-slate-700 hover:text-slate-200 transition-colors"
              >
                + Nueva búsqueda
              </button>
            </div>

            {data.job_summary && (
              <div className="border-l-4 border-sky-500 bg-sky-500/5 rounded-r-xl p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-sky-500 mb-1">
                  {t.idealProfile}
                </p>
                <p className="text-sm text-slate-300 leading-relaxed">{data.job_summary}</p>
              </div>
            )}

            {data.anonymized && (
              <span
                className="inline-flex items-center gap-1.5 bg-sky-500/10 text-sky-400 border border-sky-500/30 text-xs font-semibold px-3 py-1 rounded-full cursor-help w-fit"
                title="Los datos de contacto fueron ocultados al modelo de IA durante la evaluación para evitar sesgos."
              >
                🔒 Evaluado sin datos personales
              </span>
            )}

            <RankingTable ranking={data.ranking} />

            <div className="space-y-4">
              {data.ranking.map((c, i) => (
                <CandidateCard key={c.filename} position={i + 1} candidate={c} />
              ))}
            </div>
          </div>
        </div>
      </LangProvider>
    )
  }

  // ── Form ───────────────────────────────────────────────────────────────────

  const charState =
    jobDescription.length > JD_MAX ? 'over' :
    jobDescription.length >= JD_MIN ? 'ok' : 'under'

  return (
    <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-slate-100 mb-6">Buscar en banco de CVs</h1>

        <form onSubmit={handleSubmit} className="bg-[#111118] border border-slate-800 rounded-2xl p-6 space-y-5">

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Descripción del puesto{' '}
              <span className="text-slate-600 font-normal">mín. {JD_MIN} caracteres</span>
            </label>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              rows={6}
              placeholder="Pegá la descripción del puesto aquí…"
              className={cn(
                'w-full rounded-xl px-3 py-2.5 text-sm bg-slate-800/50 text-slate-200 placeholder-slate-600 resize-y',
                'border focus:outline-none focus:ring-1 transition-colors',
                charState === 'over'
                  ? 'border-red-500/60 focus:border-red-500 focus:ring-red-500/30'
                  : 'border-slate-700 focus:border-sky-500 focus:ring-sky-500/20',
              )}
            />
            <div className="flex justify-between mt-1.5">
              <span className={cn(
                'text-xs',
                charState === 'over'  ? 'text-red-400' :
                charState === 'ok'    ? 'text-emerald-500' :
                                        'text-slate-600',
              )}>
                {charState === 'under' && `faltan ${JD_MIN - jobDescription.length} caracteres`}
                {charState === 'ok'    && '✓'}
                {charState === 'over'  && `${jobDescription.length - JD_MAX} de más`}
              </span>
              <span className={cn(
                'text-xs',
                charState === 'over' ? 'text-red-400' : 'text-slate-600',
              )}>
                {jobDescription.length} / {JD_MAX}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Número de candidatos{' '}
              <span className="text-slate-600 font-normal">1–20</span>
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={topN}
              onChange={e => setTopN(Number(e.target.value))}
              className="w-28 border border-slate-700 bg-slate-800/50 text-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20 transition-colors"
            />
          </div>

          {validationError && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5">
              {validationError}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 text-white font-semibold py-2.5 rounded-xl transition-all"
          >
            Buscar candidatos
          </button>
        </form>
      </div>
    </div>
  )
}
