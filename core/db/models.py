import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.db.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    cv_filename: Mapped[str] = mapped_column(String(255))
    job_description: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    nivel: Mapped[str] = mapped_column(String(20))
    detailed_scores: Mapped[dict] = mapped_column(JSON)
    strengths: Mapped[list] = mapped_column(JSON)
    gaps: Mapped[list] = mapped_column(JSON)
    recommendations: Mapped[list] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
