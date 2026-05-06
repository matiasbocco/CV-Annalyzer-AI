import { useMutation, useQuery } from '@tanstack/react-query'
import type { ContactInfo, JobStatusResponse, TiebreakerAnswer } from './types'
import {
  analyzeCVs,
  extractContact,
  getJobStatus,
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

/**
 * Polls GET /jobs/{jobId} every 2 seconds while status is "pending".
 * Stops polling automatically when status becomes "completed" or "failed".
 */
export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = (query.state.data as JobStatusResponse | undefined)?.status
      // Poll while we have no data yet or while the job is still running.
      if (!status || status === 'pending') return 2000
      return false
    },
    staleTime: 0,
  })
}
