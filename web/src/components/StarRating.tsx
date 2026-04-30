import { useState } from 'react'
import { useSubmitFeedback } from '../api/hooks'

interface Props {
  analysisId: string
  onRated?: () => void
}

export default function StarRating({ analysisId, onRated }: Props) {
  const [hovered, setHovered] = useState(0)
  const [selected, setSelected] = useState(0)
  const feedback = useSubmitFeedback()

  function handleSelect(rating: number) {
    setSelected(rating)
    feedback.mutate({ analysisId, rating }, { onSuccess: () => onRated?.() })
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-col items-center gap-3">
      <p className="text-sm font-medium text-gray-700">¿Qué tan útil fue este ranking?</p>

      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            type="button"
            disabled={feedback.isPending}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => handleSelect(star)}
            className="text-2xl leading-none transition-colors disabled:cursor-wait"
            aria-label={`${star} estrellas`}
          >
            <span className={(hovered || selected) >= star ? 'text-amber-400' : 'text-gray-300'}>
              {(hovered || selected) >= star ? '★' : '☆'}
            </span>
          </button>
        ))}
      </div>

      {feedback.isSuccess && (
        <p className="text-sm text-green-600 font-medium">✓ Gracias por tu feedback</p>
      )}
      {feedback.isError && (
        <p className="text-xs text-red-500">No se pudo guardar el feedback.</p>
      )}
    </div>
  )
}
