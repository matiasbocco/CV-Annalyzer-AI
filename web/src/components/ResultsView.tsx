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

  return (
    <div className="space-y-5">
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
