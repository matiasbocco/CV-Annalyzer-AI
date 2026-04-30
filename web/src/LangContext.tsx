import { createContext, useContext } from 'react'
import type { Lang } from './lib/utils'

export const T = {
  es: {
    // RankingTable
    rankCandidate:    'Candidato',
    rankScore:        'Puntaje',
    rankLevel:        'Nivel',
    rankSource:       'Fuente',
    // SourceBadge
    sourceUploaded:   'Subido',
    sourceBank:       'Del banco',
    // CandidateCard
    contact:          'Contacto',
    strengths:        'Fortalezas',
    gaps:             'Brechas',
    recommendations:  'Recomendaciones',
    // Availability
    available:        'Disponible',
    open:             'Abierto',
    notLooking:       'No busca',
    // CopyEmailButton
    copyEmail:        '✉ Copiar email',
    copied:           '✓ Copiado',
    // StarRating
    ratingPrompt:     '¿Qué tan útil fue este ranking?',
    ratingThanks:     '✓ Gracias por tu feedback',
    ratingError:      'No se pudo guardar el feedback.',
    // TiebreakerFlow
    tieTitle:         'Hay candidatos empatados',
    tieHint:          'Dos o más candidatos tienen puntajes muy cercanos. Respondé algunas preguntas para afinar el ranking.',
    tieBtn:           'Desempatar',
    tieLoadingQ:      'Generando preguntas de desempate…',
    tiePrompt:        'Indicá qué aspectos son más importantes para este puesto:',
    tieConfirm:       'Confirmar respuestas',
    tieRecalc:        'Recalculando ranking…',
    tieDone:          'Ranking de desempate listo',
    tieNoChange:      'Sin cambios en el orden de los candidatos empatados.',
    tieView:          'Ver ranking actualizado',
    // ResultsView
    idealProfile:     'Perfil ideal del candidato',
  },
  en: {
    rankCandidate:    'Candidate',
    rankScore:        'Score',
    rankLevel:        'Level',
    rankSource:       'Source',
    sourceUploaded:   'Uploaded',
    sourceBank:       'From bank',
    contact:          'Contact',
    strengths:        'Strengths',
    gaps:             'Gaps',
    recommendations:  'Recommendations',
    available:        'Available',
    open:             'Open',
    notLooking:       'Not looking',
    copyEmail:        '✉ Copy email',
    copied:           '✓ Copied',
    ratingPrompt:     'How useful was this ranking?',
    ratingThanks:     '✓ Thanks for your feedback',
    ratingError:      'Could not save feedback.',
    tieTitle:         'Tied candidates',
    tieHint:          'Two or more candidates have very close scores. Answer a few questions to refine the ranking.',
    tieBtn:           'Break tie',
    tieLoadingQ:      'Generating tiebreaker questions…',
    tiePrompt:        'Indicate which aspects matter most for this role:',
    tieConfirm:       'Confirm answers',
    tieRecalc:        'Recalculating ranking…',
    tieDone:          'Tiebreaker ranking ready',
    tieNoChange:      'No changes in tied candidates order.',
    tieView:          'View updated ranking',
    idealProfile:     'Ideal candidate profile',
  },
} as const

const LangContext = createContext<Lang>('es')

export const LangProvider = LangContext.Provider

export function useLang() {
  return useContext(LangContext)
}
