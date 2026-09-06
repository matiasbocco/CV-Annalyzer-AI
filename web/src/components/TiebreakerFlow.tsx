import { useState } from 'react'
import { useStartTiebreaker, useSubmitTiebreakerAnswers } from '../api/hooks'
import { T, useLang } from '../LangContext'
import type {
  Candidate,
  CandidateAdjustment,
  TiebreakerAnswer,
  TiebreakerQuestion,
} from '../api/types'

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
  if (moved > 0) return { symbol: '↑', color: 'text-emerald-400' }
  if (moved < 0) return { symbol: '↓', color: 'text-red-400' }
  return { symbol: '→', color: 'text-slate-500' }
}

export default function TiebreakerFlow({ analysisId, ranking, onComplete }: Props) {
  const t = T[useLang()]
  const [phase, setPhase] = useState<Phase>({ tag: 'idle' })
  const [answers, setAnswers] = useState<Record<string, string>>({})

  const startMutation = useStartTiebreaker()
  const submitMutation = useSubmitTiebreakerAnswers()

  if (phase.tag === 'idle' && !detectCluster(ranking)) return null
  if (phase.tag === 'hidden') return null

  function handleStart() {
    setPhase({ tag: 'loading' })
    startMutation.mutate(analysisId, {
      onSuccess(result) {
        if (!result.needed) { setPhase({ tag: 'hidden' }); return }
        setPhase({
          tag: 'questioning',
          sessionId: result.session_id,
          questions: result.questions,
          cluster: result.cluster_candidates,
        })
      },
      onError() { setPhase({ tag: 'idle' }) },
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
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-amber-300">{t.tieTitle}</p>
          <p className="text-xs text-amber-500/80 mt-0.5">{t.tieHint}</p>
        </div>
        <button
          onClick={handleStart}
          className="flex-shrink-0 bg-amber-500 hover:bg-amber-400 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {t.tieBtn}
        </button>
      </div>
    )
  }

  // ── Loading ───────────────────────────────────────────────────────────────

  if (phase.tag === 'loading') {
    return (
      <div className="bg-[#111118] border border-slate-800 rounded-xl p-4 flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-slate-700 border-t-sky-500 rounded-full animate-spin flex-shrink-0" />
        <p className="text-sm text-slate-400">{t.tieLoadingQ}</p>
      </div>
    )
  }

  // ── Questioning ───────────────────────────────────────────────────────────

  if (phase.tag === 'questioning') {
    const { questions } = phase
    const allAnswered = questions.every(q => answers[q.id])

    return (
      <div className="bg-[#111118] border border-amber-500/30 rounded-xl p-5 space-y-5">
        <p className="text-sm font-semibold text-slate-200">{t.tiePrompt}</p>

        {questions.map((q, qi) => (
          <div key={q.id} className="space-y-2">
            <p className="text-sm font-medium text-slate-300">{qi + 1}. {q.text}</p>
            <div className="space-y-1.5 pl-2">
              {q.options.map(opt => (
                <label key={opt.id} className="flex items-start gap-2.5 cursor-pointer group">
                  <input
                    type="radio"
                    name={q.id}
                    value={opt.id}
                    checked={answers[q.id] === opt.id}
                    onChange={() => setAnswers(prev => ({ ...prev, [q.id]: opt.id }))}
                    className="mt-0.5 cursor-pointer accent-sky-500"
                  />
                  <span className="text-sm text-slate-400 group-hover:text-slate-200 transition-colors">
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
          className="w-full bg-gradient-to-r from-blue-600 to-sky-500 hover:from-blue-700 hover:to-sky-600 disabled:from-slate-700 disabled:to-slate-700 disabled:text-slate-500 text-white font-semibold py-2 rounded-lg text-sm transition-all"
        >
          {t.tieConfirm}
        </button>
      </div>
    )
  }

  // ── Submitting ────────────────────────────────────────────────────────────

  if (phase.tag === 'submitting') {
    return (
      <div className="bg-[#111118] border border-slate-800 rounded-xl p-4 flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-slate-700 border-t-sky-500 rounded-full animate-spin flex-shrink-0" />
        <p className="text-sm text-slate-400">{t.tieRecalc}</p>
      </div>
    )
  }

  // ── Done ──────────────────────────────────────────────────────────────────

  if (phase.tag === 'done') {
    const { adjustments, finalRanking } = phase

    return (
      <div className="bg-[#111118] border border-emerald-500/30 rounded-xl p-5 space-y-4">
        <p className="text-sm font-semibold text-emerald-400">{t.tieDone}</p>

        {adjustments.filter(a => a.moved !== 0).length === 0 ? (
          <p className="text-xs text-slate-500">{t.tieNoChange}</p>
        ) : (
          <div className="space-y-1.5">
            {adjustments.map(a => {
              const { symbol, color } = arrow(a.moved)
              return (
                <div key={a.filename} className="flex items-center gap-2 text-sm">
                  <span className={`text-base font-bold ${color}`}>{symbol}</span>
                  <span className="text-slate-300 font-medium">{a.filename}</span>
                  <span className="text-xs text-slate-600">
                    {a.original_position} → {a.new_position}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        <button
          onClick={() => {
            onComplete(buildUpdatedRanking(ranking, finalRanking))
            setPhase({ tag: 'hidden' })
          }}
          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-2 rounded-lg text-sm transition-colors"
        >
          {t.tieView}
        </button>
      </div>
    )
  }

  return null
}
