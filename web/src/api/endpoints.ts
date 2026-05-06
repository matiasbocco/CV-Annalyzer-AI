import client from './client'
import type {
  ContactInfo,
  ExtractContactResponse,
  FeedbackResponse,
  JobStatusResponse,
  JobSubmitResponse,
  StartTiebreakerResponse,
  TiebreakerAnswer,
  TiebreakerAnswerResponse,
  UploadResponse,
} from './types'

// ── Analysis ──────────────────────────────────────────────────────────────────

/** Submits files for analysis. Returns a job_id immediately (HTTP 202). */
export async function analyzeCVs(
  files: File[],
  jobDescription: string,
  includeBank: boolean,
): Promise<JobSubmitResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('job_description', jobDescription)
  form.append('include_bank', includeBank ? 'true' : 'false')

  const { data } = await client.post<JobSubmitResponse>('/analyze', form)
  return data
}

/** Queues a bank-only search. Returns a job_id immediately (HTTP 202). */
export async function matchJob(
  jobDescription: string,
  topN = 10,
): Promise<JobSubmitResponse> {
  const { data } = await client.post<JobSubmitResponse>('/match-job', {
    job_description: jobDescription,
    top_n: topN,
  })
  return data
}

/** Poll job status. Returns pending / completed (with result) / failed. */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const { data } = await client.get<JobStatusResponse>(`/jobs/${jobId}`)
  return data
}

// ── CV upload (two-step) ──────────────────────────────────────────────────────

export async function extractContact(file: File): Promise<ExtractContactResponse> {
  const form = new FormData()
  form.append('file', file)

  const { data } = await client.post<ExtractContactResponse>('/cvs/extract-contact', form)
  return data
}

export async function uploadCV(
  file: File,
  contactInfo: Partial<ContactInfo>,
  expectedHash: string,
): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  form.append('contact_info', JSON.stringify(contactInfo))
  form.append('expected_hash', expectedHash)

  const { data } = await client.post<UploadResponse>('/cvs/batch', form)
  return data
}

// ── Feedback ──────────────────────────────────────────────────────────────────

export async function submitFeedback(
  analysisId: string,
  rating: number,
): Promise<FeedbackResponse> {
  const { data } = await client.post<FeedbackResponse>(
    `/analyses/${analysisId}/feedback`,
    { rating },
  )
  return data
}

// ── Tiebreaker ────────────────────────────────────────────────────────────────

export async function startTiebreaker(
  analysisId: string,
): Promise<StartTiebreakerResponse> {
  const { data } = await client.post<StartTiebreakerResponse>(
    `/analyses/${analysisId}/tiebreaker`,
  )
  return data
}

export async function submitTiebreakerAnswers(
  sessionId: string,
  answers: TiebreakerAnswer[],
): Promise<TiebreakerAnswerResponse> {
  const { data } = await client.post<TiebreakerAnswerResponse>(
    `/tiebreaker/${sessionId}/answer`,
    { answers },
  )
  return data
}

