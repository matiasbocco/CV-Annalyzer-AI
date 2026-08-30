import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Search, Loader2 } from 'lucide-react'
import { useAnalyzeCVs, useJobStatus } from '../api/hooks'
import { cn, detectLang, getErrorMessage } from '../lib/utils'
import { LangProvider } from '../LangContext'
import type { Lang } from '../lib/utils'
import type { AnalyzeResponse, Candidate } from '../api/types'
import ResultsView from '../components/ResultsView'
import AsyncLoadingScreen from '../components/AsyncLoadingScreen'

const MAX_FILES = 30
const JD_MIN    = 50
const JD_MAX    = 3000

// ── Toggle switch ─────────────────────────────────────────────────────────────

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label
      style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', userSelect: 'none' }}
    >
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        style={{
          width: 44,
          height: 24,
          borderRadius: 12,
          border: `1px solid ${checked ? '#3b82f6' : '#2a3447'}`,
          background: checked ? '#2563eb' : '#1e2a3d',
          position: 'relative',
          cursor: 'pointer',
          transition: 'background 0.2s, border-color 0.2s',
          flexShrink: 0,
          marginTop: 2,
          padding: 0,
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 3,
            left: checked ? 22 : 3,
            width: 16,
            height: 16,
            borderRadius: '50%',
            background: 'white',
            transition: 'left 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
          }}
        />
      </button>
      <span>
        <span className="text-sm text-slate-300">Incluir candidatos del banco</span>
        <span className="block text-xs text-slate-600 mt-0.5">
          Busca candidatos similares en el historial
        </span>
      </span>
    </label>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AnalyzePage() {
  const [files, setFiles]                     = useState<File[]>([])
  const [jobDescription, setJobDescription]   = useState('')
  const [includeBank, setIncludeBank]         = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [rankingOverride, setRankingOverride] = useState<Candidate[] | null>(null)
  const [lang, setLang]                       = useState<Lang>('es')
  const [jobId, setJobId]                     = useState<string | null>(null)

  const analyze   = useAnalyzeCVs()
  const jobStatus = useJobStatus(jobId)

  const onDrop = useCallback((accepted: File[]) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      const combined = [...prev, ...accepted.filter(f => !existing.has(f.name))]
      return combined.length > MAX_FILES ? combined.slice(0, MAX_FILES) : combined
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
    },
    multiple: true,
  })

  function removeFile(name: string) {
    setFiles(prev => prev.filter(f => f.name !== name))
  }

  function validate(): string | null {
    if (files.length === 0) return 'Seleccioná al menos un archivo.'
    if (files.length > MAX_FILES) return `Máximo ${MAX_FILES} archivos.`
    if (jobDescription.trim().length < JD_MIN) return `La descripción debe tener al menos ${JD_MIN} caracteres.`
    if (jobDescription.length > JD_MAX) return `La descripción no puede superar los ${JD_MAX} caracteres.`
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    setLang(detectLang(jobDescription))
    analyze.mutate(
      { files, jobDescription: jobDescription.trim(), includeBank },
      { onSuccess: data => setJobId(data.job_id) },
    )
  }

  function resetAll() {
    analyze.reset()
    setFiles([])
    setJobDescription('')
    setIncludeBank(false)
    setValidationError(null)
    setRankingOverride(null)
    setJobId(null)
  }

  // ── Views ──────────────────────────────────────────────────────────────────

  const isProcessing =
    analyze.isPending ||
    (jobId !== null &&
      jobStatus.data?.status !== 'completed' &&
      jobStatus.data?.status !== 'failed')

  if (isProcessing) return <AsyncLoadingScreen mode="analyze" fileCount={files.length} />

  if (analyze.isError || (jobId && jobStatus.data?.status === 'failed')) {
    const msg = analyze.isError
      ? getErrorMessage(analyze.error)
      : (jobStatus.data?.error ?? 'El análisis falló.')
    return (
      <div className="min-h-screen bg-[#0A0A0F] flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-[#111118] border border-red-500/30 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-semibold text-red-400">Error al analizar</h2>
          <p className="text-sm text-slate-400">{msg}</p>
          <button
            onClick={resetAll}
            className="text-sm bg-slate-800 text-slate-300 border border-slate-700 px-4 py-2 rounded-lg hover:bg-slate-700 transition-colors"
          >
            ← Intentar de nuevo
          </button>
        </div>
      </div>
    )
  }

  if (jobId && jobStatus.data?.status === 'completed' && jobStatus.data.result) {
    const data = jobStatus.data.result as AnalyzeResponse
    const displayRanking = rankingOverride ?? data.ranking
    return (
      <LangProvider value={lang}>
        <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
          <div className="max-w-3xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-xl font-bold text-slate-100">Resultados</h1>
              <button
                onClick={resetAll}
                className="text-sm bg-slate-800 border border-slate-700 text-slate-400 px-4 py-2 rounded-lg hover:bg-slate-700 hover:text-slate-200 transition-colors"
              >
                + Nuevo análisis
              </button>
            </div>
            <ResultsView
              data={data}
              ranking={displayRanking}
              onRankingUpdate={setRankingOverride}
            />
          </div>
        </div>
      </LangProvider>
    )
  }

  // ── Form ───────────────────────────────────────────────────────────────────

  const charState =
    jobDescription.length > JD_MAX ? 'over' :
    jobDescription.length >= JD_MIN ? 'ok' : 'under'

  const canSubmit = files.length > 0 && charState !== 'over' && charState !== 'under'

  return (
    <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-xl font-bold text-slate-100 mb-6">Analizar candidatos</h1>

        <form onSubmit={handleSubmit} className="bg-[#111118] border border-slate-800 rounded-2xl p-6 space-y-5">

          {/* Dropzone */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Archivos de CV{' '}
              <span className="text-slate-600 font-normal">PDF · DOCX · JPG · PNG · WEBP</span>
            </label>
            <div
              {...getRootProps()}
              className={cn(
                'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all',
                isDragActive
                  ? 'border-sky-500 bg-sky-500/5'
                  : 'border-slate-700 hover:border-slate-600',
              )}
            >
              <input {...getInputProps()} />
              <p className="text-2xl mb-2">📂</p>
              <p className="text-sm text-slate-400">
                {isDragActive ? 'Soltá los archivos aquí…' : 'Arrastrá CVs aquí, o hacé clic para seleccionar'}
              </p>
            </div>

            {files.length > 0 && (
              <div className="mt-2 space-y-1">
                {files.map(f => (
                  <div
                    key={f.name}
                    className="flex items-center justify-between bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2"
                  >
                    <span className="text-sm text-slate-300 truncate">{f.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(f.name)}
                      className="ml-3 text-slate-500 hover:text-red-400 flex-shrink-0 text-lg leading-none transition-colors"
                    >
                      ×
                    </button>
                  </div>
                ))}
                <p className={cn(
                  'text-xs mt-1',
                  files.length >= MAX_FILES ? 'text-amber-400' : 'text-slate-600',
                )}>
                  {files.length} / {MAX_FILES} archivos
                  {files.length >= MAX_FILES ? ' — límite alcanzado' : ''}
                </p>
              </div>
            )}
          </div>

          {/* Job description */}
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

          {/* Include bank — styled toggle */}
          <ToggleSwitch checked={includeBank} onChange={setIncludeBank} />

          {validationError && (
            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2.5">
              {validationError}
            </p>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit || analyze.isPending}
            className={cn(
              'w-full flex items-center justify-center gap-2 font-semibold py-2.5 rounded-xl transition-all',
              canSubmit && !analyze.isPending
                ? 'bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-500 hover:to-sky-400 text-white hover:scale-[1.01]'
                : 'bg-gradient-to-r from-blue-600 to-sky-500 text-white opacity-40 cursor-not-allowed',
            )}
          >
            {analyze.isPending
              ? <><Loader2 size={16} className="animate-spin" /> Enviando...</>
              : <><Search size={16} /> Analizar CVs</>
            }
          </button>
        </form>
      </div>
    </div>
  )
}
