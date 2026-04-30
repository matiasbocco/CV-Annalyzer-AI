import client from './client'
import type {
  AnalyzeResponse,
  Category,
  ContactInfo,
  ExtractContactResponse,
  FeedbackResponse,
  MatchJobResponse,
  StartTiebreakerResponse,
  TiebreakerAnswer,
  TiebreakerAnswerResponse,
  TiebreakerSessionResponse,
  UploadResponse,
} from './types'

// ── Analysis ──────────────────────────────────────────────────────────────────

export async function analyzeCVs(
  files: File[],
  jobDescription: string,
  includeBank: boolean,
): Promise<AnalyzeResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('job_description', jobDescription)
  form.append('include_bank', includeBank ? 'true' : 'false')

  const { data } = await client.post<AnalyzeResponse>('/analyze', form)
  return data
}

export async function matchJob(
  jobDescription: string,
  topN = 10,
): Promise<MatchJobResponse> {
  const { data } = await client.post<MatchJobResponse>('/match-job', {
    job_description: jobDescription,
    top_n: topN,
  })
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

// ── Categories ────────────────────────────────────────────────────────────────

export async function listCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>('/categories')
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

export async function getTiebreakerSession(
  sessionId: string,
): Promise<TiebreakerSessionResponse> {
  const { data } = await client.get<TiebreakerSessionResponse>(
    `/tiebreaker/${sessionId}`,
  )
  return data
}
