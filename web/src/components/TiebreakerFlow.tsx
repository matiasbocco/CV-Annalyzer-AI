import { useState } from 'react'
import { useStartTiebreaker, useSubmitTiebreakerAnswers } from '../api/hooks'
import type {
  Candidate,
  CandidateAdjustment,
  TiebreakerAnswer,
  TiebreakerQuestion,
} from '../api/types'

// ── Phase machine ─────────────────────────────────────────────────────────────

type Phase =
  | { tag: 'idle' }
  | { tag: 'loading' }
  | { tag: 'questioning'; sessionId: string; questions: TiebreakerQuestion[]; cluster: string[] }
  | { tag: 'submitting'; sessionId: string }
  | { tag: 'done'; adjustments: CandidateAdjustment[]; finalRanking: string[] }
  | { tag: 'hidden' }

interface Props {
  analysisId: string
  ranking: Candidate[]
  onComplete: (newRanking: Candidate[]) => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function detectCluster(ranking: Candidate[]): boolean {
  if (ranking.length < 2) return false
  const topScore = ranking[0].score
  return ranking.filter(c => topScore - c.score <= 5).length >= 2
}

function buildUpdatedRanking(ranking: Candidate[], finalRanking: string[]): Candidate[] {
  const clusterSet = new Set(finalRanking)
  const byFilename = new Map(ranking.map(c => [c.filename, c]))
  const clusterIndices = ranking
    .map((c, i) => (clusterSet.has(c.filename) ? i : -1))
    .filter(i => i !== -1)
  const updated = [...ranking]
  finalRanking.forEach((fn, rank) => {
    const candidate = byFilename.get(fn)
    const idx = clusterIndices[rank]
    if (candidate !== undefined && idx !== undefined) updated[idx] = candidate
  })
  return updated
}

function arrow(moved: number) {
  if (moved > 0) return { symbol: '↑', color: 'text-green-600' }
  if (moved < 0) return { symbol: '↓', color: 'text-red-500' }
  return { symbol: '→', color: 'text-gray-400' }
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TiebreakerFlow({ analysisId, ranking, onComplete }: Props) {
  const [phase, setPhase] = useState<Phase>({ tag: 'idle' })
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const startMutation = useStartTiebreaker()
  const submitMutation = useSubmitTiebreakerAnswers()

  if (phase.tag === 'idle' && !detectCluster(ranking)) return null
  if (phase.tag === 'hidden') return null

  // ── Handlers ───────────────────────────────────────────────────────────────

  function handleStart() {
    setPhase({ tag: 'loading' })
    startMutation.mutate(analysisId, {
      onSuccess(result) {
        if (!result.needed) {
          setPhase({ tag: 'hidden' })
          return
        }
        setPhase({
          tag: 'questioning',
          sessionId: result.session_id,
          questions: result.questions,
          cluster: result.cluster_candidates,
        })
      },
      onError() {
        setPhase({ tag: 'idle' })
      },
    })
  }

  function handleSubmitAnswers() {
    if (phase.tag !== 'questioning') return
    const { sessionId, questions, cluster } = phase
    const payload: TiebreakerAnswer[] = questions.map(q => ({
      question_id: q.id,
      option_id: answers[q.id] ?? q.options[0].id,
    }))
    setPhase({ tag: 'submitting', sessionId })
    submitMutation.mutate(
      { sessionId, answers: payload },
      {
        onSuccess(result) {
          setPhase({ tag: 'done', adjustments: result.adjustments, finalRanking: result.final_ranking })
        },
        onError() {
          setPhase({ tag: 'questioning', sessionId, questions, cluster })
        },
      },
    )
  }

  // ── Idle ──────────────────────────────────────────────────────────────────

  if (phase.tag === 'idle') {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-amber-800">Hay candidatos empatados</p>
          <p className="text-xs text-amber-600 mt-0.5">
            Dos o más candidatos tienen puntajes muy cercanos. Respondé algunas preguntas para afinar el ranking.
          </p>
        </div>
        <button
          onClick={handleStart}
          className="flex-shrink-0 bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          Desempatar
        </button>
      </div>
    )
  }

  // ── Loading ───────────────────────────────────────────────────────────────

  if (phase.tag === 'loading') {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
        <p className="text-sm text-gray-600">Generando preguntas de desempate…</p>
      </div>
    )
  }

  // ── Questioning ───────────────────────────────────────────────────────────

  if (phase.tag === 'questioning') {
    const { questions } = phase
    const allAnswered = questions.every(q => answers[q.id])

    return (
      <div className="bg-white border border-amber-200 rounded-lg p-5 space-y-5">
        <p className="text-sm font-semibold text-gray-800">
          Indicá qué aspectos son más importantes para este puesto:
        </p>

        {questions.map((q, qi) => (
          <div key={q.id} className="space-y-2">
            <p className="text-sm font-medium text-gray-700">
              {qi + 1}. {q.text}
            </p>
            <div className="space-y-1.5 pl-2">
              {q.options.map(opt => (
                <label key={opt.id} className="flex items-start gap-2.5 cursor-pointer group">
                  <input
                    type="radio"
                    name={q.id}
                    value={opt.id}
                    checked={answers[q.id] === opt.id}
                    onChange={() => setAnswers(prev => ({ ...prev, [q.id]: opt.id }))}
                    className="mt-0.5 cursor-pointer"
                  />
                  <span className="text-sm text-gray-700 group-hover:text-gray-900">
                    {opt.text}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}

        <button
          onClick={handleSubmitAnswers}
          disabled={!allAnswered}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
        >
          Confirmar respuestas
        </button>
      </div>
    )
  }

  // ── Submitting ────────────────────────────────────────────────────────────

  if (phase.tag === 'submitting') {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin flex-shrink-0" />
        <p className="text-sm text-gray-600">Recalculando ranking…</p>
      </div>
    )
  }

  // ── Done ──────────────────────────────────────────────────────────────────

  if (phase.tag === 'done') {
    const { adjustments, finalRanking } = phase

    return (
      <div className="bg-white border border-green-200 rounded-lg p-5 space-y-4">
        <p className="text-sm font-semibold text-green-800">Ranking de desempate listo</p>

        {adjustments.filter(a => a.moved !== 0).length === 0 ? (
          <p className="text-xs text-gray-500">
            Sin cambios en el orden de los candidatos empatados.
          </p>
        ) : (
          <div className="space-y-1.5">
            {adjustments.map(a => {
              const { symbol, color } = arrow(a.moved)
              return (
                <div key={a.filename} className="flex items-center gap-2 text-sm">
                  <span className={`text-base font-bold ${color}`}>{symbol}</span>
                  <span className="text-gray-700 font-medium">{a.filename}</span>
                  <span className="text-xs text-gray-400">
                    {a.original_position} → {a.new_position}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        <button
          onClick={() => onComplete(buildUpdatedRanking(ranking, finalRanking))}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
        >
          Ver ranking actualizado
        </button>
      </div>
    )
  }

  return null
}
