from enum import Enum

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


class RankingResponse(BaseModel):
    ranking: list[CandidateRanking]
    job_summary: str

    @model_validator(mode="after")
    def sort_ranking_desc(self) -> "RankingResponse":
        self.ranking.sort(key=lambda c: c.score, reverse=True)
        return self
