import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Nivel(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    EXCELENTE = "excelente"


class DetailedScores(BaseModel):
    technical_skills: int = Field(ge=0, le=100)
    experience: int = Field(ge=0, le=100)
    education: int = Field(ge=0, le=100)
    soft_skills: int = Field(ge=0, le=100)


class CandidateRanking(BaseModel):
    """Raw LLM output for one candidate.  Used internally; never returned directly."""
    filename: str
    score: int = Field(ge=0, le=100)
    nivel: Nivel
    detailed_scores: DetailedScores
    strengths: list[str] = Field(max_length=3)
    gaps: list[str] = Field(max_length=3)
    recommendations: list[str] = Field(max_length=2)
    summary: str

    @model_validator(mode="after")
    def sync_nivel_with_score(self) -> "CandidateRanking":
        if self.score <= 40:
            expected = Nivel.BAJO
        elif self.score <= 65:
            expected = Nivel.MEDIO
        elif self.score <= 84:
            expected = Nivel.ALTO
        else:
            expected = Nivel.EXCELENTE
        if self.nivel != expected:
            self.nivel = expected
        return self


class CandidateRankingWithSource(BaseModel):
    """API-facing candidate entry, enriched with bank metadata.

    score         — recency-adjusted (what the user sees in the ranking).
    original_score — LLM's raw score before recency multiplication; present only
                     when recency_factor_applied < 1.0 so the UI can show
                     'adjusted: 63 (orig: 90)'.
    """
    filename: str
    score: int = Field(ge=0, le=100)
    original_score: Optional[int] = None
    nivel: str
    detailed_scores: DetailedScores
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    summary: str
    source: str                           # "uploaded" | "bank"
    recency_factor_applied: float = 1.0


class RankingResponse(BaseModel):
    ranking: list[CandidateRanking]
    job_summary: str

    @model_validator(mode="after")
    def sort_ranking_desc(self) -> "RankingResponse":
        self.ranking.sort(key=lambda c: c.score, reverse=True)
        return self


class CategoryInfo(BaseModel):
    slug: str
    display_name: str


class AnalyzeResponse(BaseModel):
    analysis_id: uuid.UUID
    ranking: list[CandidateRankingWithSource]
    job_summary: str
    category: CategoryInfo | None = None
