import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useAnalyzeCVs } from '../api/hooks'
import { cn, detectLang, getErrorMessage } from '../lib/utils'
import { LangProvider, T, useLang } from '../LangContext'
import type { Lang } from '../lib/utils'
import type { AnalyzeResponse, Candidate } from '../api/types'
import LoadingScreen from '../components/LoadingScreen'
import RankingTable from '../components/RankingTable'
import CandidateCard from '../components/CandidateCard'
import StarRating from '../components/StarRating'
import TiebreakerFlow from '../components/TiebreakerFlow'

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyzePage() {
  const [files, setFiles]                     = useState<File[]>([])
  const [jobDescription, setJobDescription]   = useState('')
  const [includeBank, setIncludeBank]         = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [rankingOverride, setRankingOverride] = useState<Candidate[] | null>(null)
  const [lang, setLang]                       = useState<Lang>('es')

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
    if (files.length === 0) return 'Seleccioná al menos un archivo PDF.'
    if (jobDescription.trim().length < 50) return 'La descripción debe tener al menos 50 caracteres.'
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    setLang(detectLang(jobDescription))
    analyze.mutate({ files, jobDescription: jobDescription.trim(), includeBank })
  }

  function resetAll() {
    analyze.reset()
    setFiles([])
    setJobDescription('')
    setIncludeBank(false)
    setValidationError(null)
    setRankingOverride(null)
  }

  // ── Views ──────────────────────────────────────────────────────────────────

  if (analyze.isPending) return <LoadingScreen />

  if (analyze.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white border border-red-200 rounded-lg p-6 space-y-4">
          <h2 className="text-lg font-semibold text-red-700">Error al analizar</h2>
          <p className="text-sm text-gray-600">{getErrorMessage(analyze.error)}</p>
          <button
            onClick={() => analyze.reset()}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            ← Intentar de nuevo
          </button>
        </div>
      </div>
    )
  }

  if (analyze.isSuccess) {
    const displayRanking = rankingOverride ?? analyze.data.ranking
    return (
      <LangProvider value={lang}>
        <div className="min-h-screen bg-gray-50 py-10 px-4">
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-900">Resultados</h1>
              <button
                onClick={resetAll}
                className="text-sm bg-white border border-gray-200 px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
              >
                + Nuevo análisis
              </button>
            </div>
            <ResultsView
              data={analyze.data}
              ranking={displayRanking}
              onRankingUpdate={setRankingOverride}
            />
          </div>
        </div>
      </LangProvider>
    )
  }

  // Form (idle)
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Analizar candidatos</h1>

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-lg p-6 space-y-5">

          {/* Dropzone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Archivos de CV <span className="text-gray-400 font-normal">(PDF)</span>
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
                  ? 'Soltá los PDFs aquí…'
                  : 'Arrastrá PDFs aquí, o hacé clic para seleccionar'}
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

          {/* Descripción del puesto */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descripción del puesto{' '}
              <span className="text-gray-400 font-normal">(mín. 50 caracteres)</span>
            </label>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              rows={6}
              placeholder="Pegá la descripción completa del puesto aquí…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400 resize-y"
            />
            <p className={cn(
              'text-xs mt-1',
              jobDescription.length >= 50 ? 'text-green-600' : 'text-gray-400',
            )}>
              {jobDescription.length} chars{' '}
              {jobDescription.length < 50
                ? `(faltan ${50 - jobDescription.length})`
                : '✓'}
            </p>
          </div>

          {/* Banco de CVs */}
          <label className="flex items-start gap-2.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeBank}
              onChange={e => setIncludeBank(e.target.checked)}
              className="mt-0.5 w-4 h-4 cursor-pointer"
            />
            <span className="text-sm text-gray-700">
              Incluir candidatos del banco de CVs
              <span className="block text-xs text-gray-400 mt-0.5">
                Los candidatos del banco se agregan al ranking junto a los CVs subidos.
              </span>
            </span>
          </label>

          {validationError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {validationError}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Analizar
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Results view ──────────────────────────────────────────────────────────────

function ResultsView({
  data,
  ranking,
  onRankingUpdate,
}: {
  data: AnalyzeResponse
  ranking: Candidate[]
  onRankingUpdate: (r: Candidate[]) => void
}) {
  const t = T[useLang()]

  return (
    <div className="space-y-6">
      {/* Job summary */}
      <div className="bg-indigo-50 border-l-4 border-indigo-500 rounded-r-lg p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 mb-1">
          {t.idealProfile}
        </p>
        <p className="text-sm text-gray-700 leading-relaxed">{data.job_summary}</p>
      </div>

      {/* Category badge + anonymization notice */}
      <div className="flex flex-wrap items-center gap-2">
        {data.category && (
          <span className="inline-flex items-center gap-1.5 bg-purple-100 text-purple-800 text-xs font-semibold px-3 py-1 rounded-full">
            🏷 {data.category.display_name}
          </span>
        )}
        {data.anonymized && (
          <span
            className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold px-3 py-1 rounded-full cursor-help"
            title="Los datos de contacto fueron ocultados al modelo de IA durante la evaluación para evitar sesgos."
          >
            🔒 Evaluado sin datos personales
          </span>
        )}
      </div>

      {/* Ranking table */}
      <RankingTable ranking={ranking} />

      {/* Tiebreaker */}
      <TiebreakerFlow
        analysisId={data.analysis_id}
        ranking={ranking}
        onComplete={onRankingUpdate}
      />

      {/* Detail cards */}
      <div className="space-y-4">
        {ranking.map((c, i) => (
          <CandidateCard key={c.filename} position={i + 1} candidate={c} />
        ))}
      </div>

      {/* Feedback */}
      <StarRating analysisId={data.analysis_id} />
    </div>
  )
}
