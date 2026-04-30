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

/** Full shape returned by GET /categories — includes extra fields */
export interface Category extends CategoryInfo {
  description: string | null
  required_skills: string[] | null
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

/** Returned by GET /tiebreaker/{session_id} */
export interface TiebreakerSessionResponse {
  session_id: string
  status: 'pending' | 'completed'
  cluster_candidates: string[]
  questions: TiebreakerQuestion[]
  answers: TiebreakerAnswer[] | null
  final_ranking: string[] | null
}
