import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAnalysisDetail, useAnalysisHistory } from '../api/hooks'
import type { AnalysisHistoryItem, Candidate } from '../api/types'
import { LangProvider } from '../LangContext'
import { cn } from '../lib/utils'
import ResultsView from '../components/ResultsView'
import { getUser } from '../auth'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function Stars({ rating }: { rating: number | null }) {
  if (rating == null) return <span className="text-slate-600 text-xs">Sin calificación</span>
  return (
    <span className="text-sm" aria-label={`${rating} de 5 estrellas`}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < rating ? 'text-amber-400' : 'text-slate-700'}>
          ★
        </span>
      ))}
    </span>
  )
}

// ── Detail view ───────────────────────────────────────────────────────────────

function DetailView({
  analysisId,
  onBack,
}: {
  analysisId: string
  onBack: () => void
}) {
  const { data, isLoading, isError } = useAnalysisDetail(analysisId)
  const [rankingOverride, setRankingOverride] = useState<Candidate[] | null>(null)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="text-slate-400 text-sm">Cargando análisis...</span>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <p className="text-red-400 text-sm">No se pudo cargar el análisis.</p>
        <button onClick={onBack} className="text-sm text-sky-400 hover:text-sky-300 transition-colors">
          ← Volver al historial
        </button>
      </div>
    )
  }

  const displayRanking = rankingOverride ?? data.ranking

  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="text-sm bg-slate-800 border border-slate-700 text-slate-400 px-4 py-2 rounded-lg hover:bg-slate-700 hover:text-slate-200 transition-colors"
      >
        ← Volver al historial
      </button>

      <LangProvider value="es">
        <ResultsView
          data={data}
          ranking={displayRanking}
          onRankingUpdate={setRankingOverride}
        />
      </LangProvider>
    </div>
  )
}

// ── History card ──────────────────────────────────────────────────────────────

function HistoryCard({
  item,
  isAdmin,
  onClick,
}: {
  item: AnalysisHistoryItem
  isAdmin: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-[#111118] border border-slate-800 hover:border-slate-600 rounded-xl p-5 space-y-3 transition-colors group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-slate-500">{fmtDateTime(item.created_at)}</span>
            {item.category && (
              <span className="text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                🏷 {item.category.display_name}
              </span>
            )}
            {isAdmin && item.user_email && (
              <span className="text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-full">
                {item.user_email}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-200 line-clamp-2 leading-snug">
            {item.job_description_preview}
            {item.job_description_preview.length >= 100 && '…'}
          </p>
          {item.job_summary_preview && (
            <p className="text-xs text-slate-500 line-clamp-1 italic">
              {item.job_summary_preview}
              {item.job_summary_preview.length >= 150 && '…'}
            </p>
          )}
        </div>
        <span className="text-slate-600 group-hover:text-slate-400 flex-shrink-0 text-lg transition-colors">
          →
        </span>
      </div>

      <div className="flex items-center gap-4 pt-1 border-t border-slate-800">
        <span className="text-xs text-slate-400">
          {item.candidates_count} candidato{item.candidates_count !== 1 ? 's' : ''}
        </span>
        <Stars rating={item.feedback_rating} />
      </div>
    </button>
  )
}

// ── HistoryPage ───────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data, isLoading, isError } = useAnalysisHistory(page)
  const user = getUser()
  const isAdmin = user?.role === 'admin'

  // Show detail view when a card is selected.
  if (selectedId) {
    return (
      <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
        <div className="max-w-3xl mx-auto">
          <DetailView analysisId={selectedId} onBack={() => setSelectedId(null)} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0A0A0F] py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Historial de análisis</h1>
          <p className="text-sm text-slate-500 mt-1">
            Los análisis se conservan por 7 días.
          </p>
        </div>

        {isLoading && (
          <p className="text-slate-400 text-sm py-10 text-center">Cargando historial...</p>
        )}

        {isError && (
          <p className="text-red-400 text-sm">No se pudo cargar el historial.</p>
        )}

        {data && data.items.length === 0 && (
          <div className="text-center py-20 space-y-3">
            <p className="text-slate-400">No tenés análisis todavía.</p>
            <Link
              to="/"
              className="inline-block text-sm bg-sky-600 hover:bg-sky-500 text-white font-medium px-5 py-2 rounded-lg transition-colors"
            >
              Analizar candidatos
            </Link>
          </div>
        )}

        {data && data.items.length > 0 && (
          <>
            <div className="space-y-3">
              {data.items.map((item) => (
                <HistoryCard
                  key={item.id}
                  item={item}
                  isAdmin={isAdmin}
                  onClick={() => setSelectedId(item.id)}
                />
              ))}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between text-sm text-slate-400 pt-2">
              <span>
                {data.total} análisis en total · página {data.page} de {data.total_pages}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className={cn(
                    'px-3 py-1.5 rounded-lg border border-slate-700 text-sm transition-colors',
                    page === 1
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-slate-800 hover:text-slate-200',
                  )}
                >
                  ← Anterior
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages}
                  className={cn(
                    'px-3 py-1.5 rounded-lg border border-slate-700 text-sm transition-colors',
                    page === data.total_pages
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-slate-800 hover:text-slate-200',
                  )}
                >
                  Siguiente →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
