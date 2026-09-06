import client from './client'
import type {
  AdminUser,
  AnalysisHistoryResponse,
  AnalyzeResponse,
  BulkUploadResponse,
  ContactInfo,
  CostsResponse,
  CreateUserResponse,
  CVListResponse,
  ExtractContactResponse,
  FeedbackResponse,
  JobStatusResponse,
  JobSubmitResponse,
  LoginResponse,
  MetricsResponse,
  ResetPasswordResponse,
  StartTiebreakerResponse,
  TiebreakerAnswer,
  TiebreakerAnswerResponse,
  UploadResponse,
  UserMetricsResponse,
} from './types'

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { email, password })
  return data
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout')
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await client.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

/** Attempts a silent token refresh using the httpOnly cookie. Throws on failure. */
export async function refreshToken(): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/refresh')
  return data
}

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
  form.append('files', file)
  form.append('contact_info', JSON.stringify(contactInfo))
  form.append('expected_hash', expectedHash)

  const { data } = await client.post<UploadResponse>('/cvs/batch', form)
  return data
}

export async function bulkUploadCVs(files: File[]): Promise<BulkUploadResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))

  const { data } = await client.post<BulkUploadResponse>('/cvs/batch', form)
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

// ── Admin ──────────────────────────────────────────────────────────────────────

export async function adminListUsers(): Promise<AdminUser[]> {
  const { data } = await client.get<AdminUser[]>('/admin/users')
  return data
}

export async function adminCreateUser(
  email: string,
  role: 'admin' | 'recruiter',
  firstName?: string,
  lastName?: string,
): Promise<CreateUserResponse> {
  const { data } = await client.post<CreateUserResponse>('/admin/users', {
    email,
    role,
    first_name: firstName || null,
    last_name: lastName || null,
  })
  return data
}

export async function adminPatchUser(
  userId: string,
  patch: { is_active?: boolean; role?: 'admin' | 'recruiter'; first_name?: string; last_name?: string },
): Promise<AdminUser> {
  const { data } = await client.patch<AdminUser>(`/admin/users/${userId}`, patch)
  return data
}

export async function adminResetPassword(userId: string): Promise<ResetPasswordResponse> {
  const { data } = await client.post<ResetPasswordResponse>(
    `/admin/users/${userId}/reset-password`,
  )
  return data
}

export async function adminGetMetrics(): Promise<MetricsResponse> {
  const { data } = await client.get<MetricsResponse>('/admin/metrics')
  return data
}

export async function adminGetCosts(): Promise<CostsResponse> {
  const { data } = await client.get<CostsResponse>('/admin/costs')
  return data
}

export async function adminGetUserMetrics(userId: string): Promise<UserMetricsResponse> {
  const { data } = await client.get<UserMetricsResponse>(`/admin/users/${userId}/metrics`)
  return data
}

export async function adminGetUserCosts(userId: string): Promise<CostsResponse> {
  const { data } = await client.get<CostsResponse>(`/admin/users/${userId}/costs`)
  return data
}

export async function adminListCVs(page = 1): Promise<CVListResponse> {
  const { data } = await client.get<CVListResponse>(`/admin/cvs?page=${page}`)
  return data
}

export async function adminExpireCVs(): Promise<{ expired: number }> {
  const { data } = await client.post<{ expired: number }>('/admin/expire-cvs')
  return data
}

export async function adminCleanupAnalyses(): Promise<{ deleted_count: number }> {
  const { data } = await client.post<{ deleted_count: number }>('/admin/cleanup-analyses')
  return data
}

// ── Analysis history ──────────────────────────────────────────────────────────

export async function getAnalysisHistory(
  page = 1,
  pageSize = 20,
): Promise<AnalysisHistoryResponse> {
  const { data } = await client.get<AnalysisHistoryResponse>(
    `/analyses?page=${page}&page_size=${pageSize}`,
  )
  return data
}

export async function getAnalysisDetail(analysisId: string): Promise<AnalyzeResponse> {
  const { data } = await client.get<AnalyzeResponse>(`/analyses/${analysisId}`)
  return data
}

