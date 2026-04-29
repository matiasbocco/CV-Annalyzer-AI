import uuid
from typing import Optional

from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    id: str
    text: str
    # Additive delta applied to each dimension's base weight (25 each).
    # Range kept to [-15, +15] so no single answer dominates completely.
    weight_adjustments: dict[str, int]


class TiebreakerQuestion(BaseModel):
    id: str
    text: str
    options: list[QuestionOption] = Field(min_length=2, max_length=4)


class LLMQuestionsPayload(BaseModel):
    questions: list[TiebreakerQuestion] = Field(min_length=2, max_length=3)


class AnswerInput(BaseModel):
    question_id: str
    option_id: str


class TiebreakerAnswerRequest(BaseModel):
    answers: list[AnswerInput]


class CandidateAdjustment(BaseModel):
    filename: str
    original_position: int   # 0-indexed position within the cluster before tiebreaker
    new_position: int        # 0-indexed position within the cluster after tiebreaker
    moved: int               # positive = moved up, negative = moved down, 0 = unchanged


class TiebreakerAnswerResponse(BaseModel):
    final_ranking: list[str]
    adjustments: list[CandidateAdjustment]


class TiebreakerNeededResponse(BaseModel):
    needed: bool


class TiebreakerCreatedResponse(BaseModel):
    needed: bool
    session_id: uuid.UUID
    cluster_candidates: list[str]
    questions: list[TiebreakerQuestion]


class TiebreakerSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    cluster_candidates: list[str]
    questions: list[TiebreakerQuestion]
    answers: Optional[list[AnswerInput]] = None
    final_ranking: Optional[list[str]] = None
