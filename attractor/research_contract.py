from pydantic import BaseModel, Field


class ResearchContract(BaseModel):
    question: str = Field(min_length=3)
    acceptable_sources: list[str] = Field(default_factory=list)
    independent_sources_required: int = Field(default=1, ge=0)
    primary_source_required: bool = False
    max_age_days: int | None = Field(default=None, ge=0)
    falsification_question: str | None = None
    uncertainty_required: bool = True
