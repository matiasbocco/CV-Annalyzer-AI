import { useState, useRef, useLayoutEffect } from 'react'
import type { AnalyzeResponse, Candidate } from '../api/types'
import { T, useLang } from '../LangContext'
import RankingTable from './RankingTable'
import CandidateCard from './CandidateCard'
import StarRating from './StarRating'
import TiebreakerFlow from './TiebreakerFlow'

/**
 * Shared results view: rendered in AnalyzePage (after a new analysis) and
 * HistoryPage (when viewing a stored analysis).  Requires a LangProvider ancestor.
 */
export default function ResultsView({
  data,
  ranking,
  onRankingUpdate,
}: {
  data: AnalyzeResponse
  ranking: Candidate[]
  onRankingUpdate: (r: Candidate[]) => void
}) {
  const t = T[useLang()]
  const [jdExpanded, setJdExpanded] = useState(false)
  const [jdClamped, setJdClamped] = useState(false)
  const jdRef = useRef<HTMLParagraphElement>(null)

  useLayoutEffect(() => {
    const el = jdRef.current
    if (!el) return

    const measure = () => setJdClamped(el.scrollHeight > el.clientHeight + 1)

    // Measure while collapsed (line-clamp-3 is active).
    // Temporarily remove expanded state so scrollHeight reflects clamped height.
    el.classList.add('line-clamp-3')
    measure()
    el.classList.remove('line-clamp-3')

    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [data.job_description])

  return (
    <div className="space-y-5">
      {/* Job description entered by the user */}
      <div className="border-l-4 border-slate-500 bg-slate-800/50 rounded-r-xl p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
          {t.jobDescription}
        </p>
        <p ref={jdRef} className={`text-sm text-slate-300 leading-relaxed whitespace-pre-wrap${jdExpanded ? '' : ' line-clamp-3'}`}>
          {data.job_description}
        </p>
        {(jdClamped || jdExpanded) && (
          <button
            onClick={() => setJdExpanded(v => !v)}
            className="mt-1.5 text-xs text-sky-400 hover:text-sky-300 transition-colors"
          >
            {jdExpanded ? t.showLess : t.showAll}
          </button>
        )}
      </div>

      {/* Ideal profile */}
      <div className="border-l-4 border-sky-500 bg-sky-500/5 rounded-r-xl p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-sky-500 mb-1">
          {t.idealProfile}
        </p>
        <p className="text-sm text-slate-300 leading-relaxed">{data.job_summary}</p>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap items-center gap-2">
        {data.category && (
          <span className="inline-flex items-center bg-slate-800 border border-slate-700 text-slate-300 text-xs font-semibold px-3 py-1 rounded-full">
            🏷 {data.category.display_name}
          </span>
        )}
        {data.anonymized && (
          <span
            className="inline-flex items-center gap-1.5 bg-sky-500/10 text-sky-400 border border-sky-500/30 text-xs font-semibold px-3 py-1 rounded-full cursor-help"
            title="Los datos de contacto fueron ocultados al modelo de IA durante la evaluación para evitar sesgos."
          >
            🔒 Evaluado sin datos personales
          </span>
        )}
      </div>

      <RankingTable ranking={ranking} />

      <TiebreakerFlow
        analysisId={data.analysis_id}
        ranking={ranking}
        onComplete={onRankingUpdate}
      />

      <div className="space-y-4">
        {ranking.map((c, i) => (
          <CandidateCard key={c.filename} position={i + 1} candidate={c} />
        ))}
      </div>

      <StarRating analysisId={data.analysis_id} />
    </div>
  )
}
