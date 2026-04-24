import uuid
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


class AnalysisResult(BaseModel):
    score: int = Field(ge=0, le=100)
    nivel: Nivel
    detailed_scores: DetailedScores
    strengths: list[str] = Field(max_length=5)
    gaps: list[str] = Field(max_length=4)
    recommendations: list[str] = Field(max_length=3)
    summary: str

    @model_validator(mode="after")
    def sync_nivel_with_score(self) -> "AnalysisResult":
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


class AnalyzeResponse(BaseModel):
    analysis: AnalysisResult
    analysis_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    processing_time_ms: int
    model_used: str
