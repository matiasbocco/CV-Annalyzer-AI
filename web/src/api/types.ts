// ── Auth ──────────────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string
  email: string
  role: 'admin' | 'recruiter'
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  must_change_password: boolean
  user: UserInfo
}

export interface RefreshResponse {
  access_token: string
  token_type: 'bearer'
  user: UserInfo
}

// ── Admin — users ─────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string
  email: string
  role: 'admin' | 'recruiter'
  is_active: boolean
  last_login: string | null
  created_at: string
  analysis_count: number
}

export interface CreateUserResponse {
  id: string
  email: string
  role: string
  temporary_password: string
  must_change_password: boolean
}

export interface ResetPasswordResponse {
  new_password: string
  must_change_password: boolean
}

// ── Admin — metrics ───────────────────────────────────────────────────────────

export interface DayCount {
  date: string
  count: number
}

export interface CategoryCount {
  slug: string
  display_name: string
  count: number
}

export interface MetricsResponse {
  total_analyses: number
  analyses_last_30_days: number
  analyses_by_day: DayCount[]
  top_categories: CategoryCount[]
  average_rating: number | null
  total_cvs_in_bank: number
  active_cvs: number
  expiring_soon_cvs: number
  expired_cvs: number
  total_users: number
  active_users: number
}

// ── Admin — costs ─────────────────────────────────────────────────────────────

export interface CostsResponse {
  total_analyses: number
  estimated_ranking_calls: number
  estimated_category_calls: number
  estimated_contact_extraction_calls: number
  estimated_embedding_calls: number
  estimated_total_cost_usd: number
  cost_breakdown: {
    ranking: number
    category: number
    contact: number
    embeddings: number
  }
}

// ── Admin — CV bank ───────────────────────────────────────────────────────────

export interface AdminCV {
  id: string
  filename: string
  full_name: string | null
  email: string | null
  created_at: string
  last_seen_at: string
  times_matched: number
  is_expired: boolean
  days_until_expiry: number
}

export interface CVListResponse {
  items: AdminCV[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ── Primitives ────────────────────────────────────────────────────────────────

export type Nivel = 'bajo' | 'medio' | 'alto' | 'excelente'

/** Mirrors backend Literal["available","open","not_looking"] | null */
export type Availability = 'available' | 'open' | 'not_looking' | null

// ── Shared sub-types ──────────────────────────────────────────────────────────

export interface DetailedScores {
  technical_skills: number
  experience: number
  education: number
  soft_skills: number
}

export interface ContactInfo {
  full_name: string | null
  email: string | null
  phone: string | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
  location: string | null
  availability: Availability
}

/** Slim version used inside AnalyzeResponse.category */
export interface CategoryInfo {
  slug: string
  display_name: string
}

// ── Ranking / analysis ────────────────────────────────────────────────────────

/**
 * One entry in a ranking response.
 * Field name is `recency_factor_applied` — matches backend CandidateRankingWithSource
 * exactly (not `recency_factor`).
 */
export interface Candidate {
  filename: string
  score: number
  /** Only present when recency_factor_applied < 1.0 */
  original_score: number | null
  nivel: Nivel
  detailed_scores: DetailedScores
  strengths: string[]
  gaps: string[]
  recommendations: string[]
  summary: string
  source: 'uploaded' | 'bank'
  recency_factor_applied: number
  contact: ContactInfo | null
}

export interface AnalyzeResponse {
  analysis_id: string
  ranking: Candidate[]
  job_summary: string
  category: CategoryInfo | null
  anonymized: boolean
}

/** /match-job returns the same shape as /analyze */
export type MatchJobResponse = AnalyzeResponse

// ── CV upload ─────────────────────────────────────────────────────────────────

export interface UploadResponse {
  status: 'added' | 'duplicate' | 'failed'
  filename: string
  cv_id: string | null
  message: string
}

/**
 * Step 1 of the two-step upload: extract contact from PDF without saving.
 * extracted_contact may be a partial dict (LLM returns only what it found).
 */
export interface ExtractContactResponse {
  extracted_text_hash: string
  extracted_contact: Partial<ContactInfo>
  missing_fields: string[]
  filename: string
}

// ── Async job status ──────────────────────────────────────────────────────────

/** Returned by POST /analyze and POST /match-job (HTTP 202). */
export interface JobSubmitResponse {
  job_id: string
  status: 'pending'
}

/** Returned by GET /jobs/{job_id}. */
export interface JobStatusResponse {
  status: 'pending' | 'completed' | 'failed'
  result?: AnalyzeResponse | MatchJobResponse
  error?: string
}

// ── Feedback ──────────────────────────────────────────────────────────────────

/**
 * Backend returns { updated: true } (200) or { created: true } (201).
 * Not a full Feedback row — the endpoint just confirms the write.
 */
export interface FeedbackResponse {
  updated?: boolean
  created?: boolean
}

// ── Tiebreaker ────────────────────────────────────────────────────────────────

export interface TiebreakerOption {
  id: string
  text: string
  /** Additive deltas for dimension weights, e.g. { technical_skills: 10, soft_skills: -5 } */
  weight_adjustments: Record<string, number>
}

export interface TiebreakerQuestion {
  id: string
  text: string
  options: TiebreakerOption[]
}

/**
 * Answer payload for POST /tiebreaker/{session_id}/answer.
 * Backend field is `option_id` — NOT `selected_option`.
 */
export interface TiebreakerAnswer {
  question_id: string
  option_id: string
}

export interface CandidateAdjustment {
  filename: string
  original_position: number
  new_position: number
  /** Positive = moved up, negative = moved down, 0 = unchanged */
  moved: number
}

/** Returned when POST /analyses/{id}/tiebreaker finds no cluster */
export interface TiebreakerNotNeeded {
  needed: false
}

/** Returned when POST /analyses/{id}/tiebreaker creates a session */
export interface TiebreakerCreated {
  needed: true
  session_id: string
  cluster_candidates: string[]
  questions: TiebreakerQuestion[]
}

export type StartTiebreakerResponse = TiebreakerNotNeeded | TiebreakerCreated

/** Returned by POST /tiebreaker/{session_id}/answer */
export interface TiebreakerAnswerResponse {
  final_ranking: string[]
  adjustments: CandidateAdjustment[]
}

