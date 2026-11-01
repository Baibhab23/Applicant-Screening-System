from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, field_validator


class ResumeEvaluation(BaseModel):
    match_score: float = Field(ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    experience_level: str
    skills_match: float = Field(ge=0, le=100)
    recommendation: str
    reasoning: str = ""

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        if v.upper() not in {"HIRE", "MAYBE", "REJECT"}:
            raise ValueError(f"recommendation must be HIRE, MAYBE, or REJECT; got '{v}'")
        return v.upper()

    @field_validator("experience_level")
    @classmethod
    def normalise_experience_level(cls, v: str) -> str:
        normalised = v.lower().strip()
        if normalised not in {"junior", "mid-level", "senior"}:
            # Coerce rather than reject — level is informational, not a gate.
            return "mid-level"
        return normalised


class InterviewEvaluation(BaseModel):
    technical_score: float = Field(ge=0, le=100)
    communication_score: float = Field(ge=0, le=100)
    problem_solving_score: float = Field(ge=0, le=100)
    # collaborative_evidence_score replaced cultural_fit_score (see llm_client.py)
    collaborative_evidence_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    recommendation: str
    key_insights: List[str] = []
    concerns: List[str] = []

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        if v.upper() not in {"STRONG_HIRE", "HIRE", "MAYBE", "NO_HIRE"}:
            raise ValueError(
                f"recommendation must be STRONG_HIRE, HIRE, MAYBE, or NO_HIRE; got '{v}'"
            )
        return v.upper()


class FinalRecommendation(BaseModel):
    decision: str
    confidence_score: float = Field(ge=0, le=100)
    key_strengths: List[str] = []
    key_concerns: List[str] = []
    next_steps: List[str] = []
    detailed_reasoning: str = ""

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v.upper() not in {"STRONG_HIRE", "HIRE", "MAYBE", "REJECT"}:
            raise ValueError(
                f"decision must be STRONG_HIRE, HIRE, MAYBE, or REJECT; got '{v}'"
            )
        return v.upper()
