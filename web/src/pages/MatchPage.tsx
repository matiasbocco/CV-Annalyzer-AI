import { useState } from 'react'
import { useMatchJob } from '../api/hooks'
import { cn, getErrorMessage } from '../lib/utils'
import LoadingScreen from '../components/LoadingScreen'
import RankingTable from '../components/RankingTable'
import CandidateCard from '../components/CandidateCard'

export default function MatchPage() {
  const [jobDescription, setJobDescription] = useState('')
  const [topN, setTopN]                     = useState(10)
  const [validationError, setValidationError] = useState<string | null>(null)

  const match = useMatchJob()

  function validate(): string | null {
    if (jobDescription.trim().length < 50) return 'La descripción debe tener al menos 50 caracteres.'
    if (topN < 1 || topN > 20) return 'El número de candidatos debe estar entre 1 y 20.'
    return null
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const err = validate()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    match.mutate({ jobDescription: jobDescription.trim(), topN })
  }

  if (match.isPending) return <LoadingScreen text="Buscando candidatos en el banco…" />

  if (match.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white border border-red-200 rounded-lg p-6 space-y-4">
          <h2 className="text-lg font-semibold text-red-700">Error al buscar</h2>
          <p className="text-sm text-gray-600">{getErrorMessage(match.error)}</p>
          <button
            onClick={() => match.reset()}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            ← Volver
          </button>
        </div>
      </div>
    )
  }

  if (match.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900">Candidatos del banco</h1>
            <button
              onClick={() => match.reset()}
              className="text-sm bg-white border border-gray-200 px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-50"
            >
              + Nueva búsqueda
            </button>
          </div>

          {match.data.job_summary && (
            <div className="bg-indigo-50 border-l-4 border-indigo-500 rounded-r-lg p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 mb-1">
                Perfil ideal
              </p>
              <p className="text-sm text-gray-700 leading-relaxed">{match.data.job_summary}</p>
            </div>
          )}

          <RankingTable ranking={match.data.ranking} />

          <div className="space-y-4">
            {match.data.ranking.map((c, i) => (
              <CandidateCard key={c.filename} position={i + 1} candidate={c} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  // Form (idle)
  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Buscar en banco de CVs</h1>

        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-lg p-6 space-y-5">

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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Número de candidatos{' '}
              <span className="text-gray-400 font-normal">(1–20)</span>
            </label>
            <input
              type="number"
              min={1}
              max={20}
              value={topN}
              onChange={e => setTopN(Number(e.target.value))}
              className="w-28 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            />
          </div>

          {validationError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
              {validationError}
            </p>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white font-semibold py-2.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Buscar candidatos
          </button>
        </form>
      </div>
    </div>
  )
}
