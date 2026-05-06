import { useState } from 'react'
import { useSubmitFeedback } from '../api/hooks'
import { T, useLang } from '../LangContext'

interface Props {
  analysisId: string
  onRated?: () => void
}

export default function StarRating({ analysisId, onRated }: Props) {
  const t = T[useLang()]
  const [hovered, setHovered] = useState(0)
  const [selected, setSelected] = useState(0)
  const feedback = useSubmitFeedback()

  function handleSelect(rating: number) {
    setSelected(rating)
    feedback.mutate({ analysisId, rating }, { onSuccess: () => onRated?.() })
  }

  return (
    <div className="bg-[#111118] border border-slate-800 rounded-xl p-4 flex flex-col items-center gap-3">
      <p className="text-sm font-medium text-slate-400">{t.ratingPrompt}</p>

      <div className="flex gap-1.5">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            type="button"
            disabled={feedback.isPending || selected > 0}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => handleSelect(star)}
            className="text-2xl leading-none transition-all disabled:cursor-default hover:scale-110"
            aria-label={`${star} stars`}
          >
            <span className={
              (hovered || selected) >= star
                ? 'text-amber-400'
                : 'text-slate-700'
            }>
              {(hovered || selected) >= star ? '★' : '☆'}
            </span>
          </button>
        ))}
      </div>

      {feedback.isSuccess && (
        <p className="text-sm text-emerald-400 font-medium">{t.ratingThanks}</p>
      )}
      {feedback.isError && (
        <p className="text-xs text-red-400">{t.ratingError}</p>
      )}
    </div>
  )
}
