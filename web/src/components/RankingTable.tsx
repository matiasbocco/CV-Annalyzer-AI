import { cn, formatScore, getNivelColor } from '../lib/utils'
import { T, useLang } from '../LangContext'
import type { Candidate } from '../api/types'
import { SourceBadge } from './CandidateCard'

export default function RankingTable({ ranking }: { ranking: Candidate[] }) {
  const t = T[useLang()]

  return (
    <div className="bg-[#111118] border border-slate-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-800/50 border-b border-slate-800 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-10">#</th>
            <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t.rankCandidate}</th>
            <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-32">{t.rankScore}</th>
            <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-24">{t.rankLevel}</th>
            <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide w-28">{t.rankSource}</th>
          </tr>
        </thead>
        <tbody>
          {ranking.map((c, i) => (
            <tr key={c.filename} className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30 transition-colors">
              <td className="px-4 py-3 text-slate-500 font-medium">{i + 1}</td>
              <td className="px-4 py-3">
                <span className="font-medium text-slate-200">
                  {c.contact?.full_name ?? c.filename}
                </span>
                {c.contact?.full_name && (
                  <span className="block text-xs text-slate-600 font-mono">{c.filename}</span>
                )}
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden min-w-[40px]">
                    <div
                      className="h-full bg-gradient-to-r from-blue-600 to-sky-500 rounded-full"
                      style={{ width: `${c.score}%` }}
                    />
                  </div>
                  <span className="text-sky-400 font-bold text-sm w-8 text-right flex-shrink-0">
                    {formatScore(c.score)}
                  </span>
                </div>
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
