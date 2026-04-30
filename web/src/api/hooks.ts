import { useMutation, useQuery } from '@tanstack/react-query'
import type { ContactInfo, TiebreakerAnswer } from './types'
import {
  analyzeCVs,
  extractContact,
  getTiebreakerSession,
  listCategories,
  matchJob,
  startTiebreaker,
  submitFeedback,
  submitTiebreakerAnswers,
  uploadCV,
} from './endpoints'

// ── Mutations — user-triggered actions ───────────────────────────────────────

export function useAnalyzeCVs() {
  return useMutation({
    mutationFn: ({
      files,
      jobDescription,
      includeBank,
    }: {
      files: File[]
      jobDescription: string
      includeBank: boolean
    }) => analyzeCVs(files, jobDescription, includeBank),
  })
}

export function useMatchJob() {
  return useMutation({
    mutationFn: ({
      jobDescription,
      topN,
    }: {
      jobDescription: string
      topN?: number
    }) => matchJob(jobDescription, topN),
  })
}

export function useExtractContact() {
  return useMutation({
    mutationFn: (file: File) => extractContact(file),
  })
}

export function useUploadCV() {
  return useMutation({
    mutationFn: ({
      file,
      contactInfo,
      expectedHash,
    }: {
      file: File
      contactInfo: Partial<ContactInfo>
      expectedHash: string
    }) => uploadCV(file, contactInfo, expectedHash),
  })
}

export function useSubmitFeedback() {
  return useMutation({
    mutationFn: ({
      analysisId,
      rating,
    }: {
      analysisId: string
      rating: number
    }) => submitFeedback(analysisId, rating),
  })
}

export function useStartTiebreaker() {
  return useMutation({
    mutationFn: (analysisId: string) => startTiebreaker(analysisId),
  })
}

export function useSubmitTiebreakerAnswers() {
  return useMutation({
    mutationFn: ({
      sessionId,
      answers,
    }: {
      sessionId: string
      answers: TiebreakerAnswer[]
    }) => submitTiebreakerAnswers(sessionId, answers),
  })
}

// ── Queries — passive data fetching ──────────────────────────────────────────

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: listCategories,
    staleTime: 5 * 60 * 1000, // categories change rarely; cache for 5 min
  })
}

export function useTiebreakerSession(sessionId: string | null) {
  return useQuery({
    queryKey: ['tiebreaker', sessionId],
    queryFn: () => getTiebreakerSession(sessionId!),
    enabled: sessionId !== null,
  })
}
