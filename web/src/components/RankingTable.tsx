import { cn, formatScore, getNivelColor } from '../lib/utils'
import type { Candidate } from '../api/types'
import { SourceBadge } from './CandidateCard'

export default function RankingTable({ ranking }: { ranking: Candidate[] }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200 text-left">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-10">#</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Candidato</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-20">Puntaje</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-24">Nivel</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide w-28">Fuente</th>
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
