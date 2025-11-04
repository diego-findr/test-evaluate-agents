"""
Response data models for agent outputs and API responses
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ScoreOutput(BaseModel):
    """Structured output for evaluation agents."""
    
    score: int = Field(..., ge=0, le=100, description="Compatibility score (0-100)")
    reason: str = Field(..., description="Detailed reasoning for the score")
    
    @field_validator('score')
    @classmethod
    def validate_score_range(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Score must be between 0 and 100')
        return v


class ScoringAgentOutput(BaseModel):
    """Output from the scoring agent with weighted final score."""
    
    final_score: int = Field(..., ge=0, le=100, description="Weighted compatibility score")
    liked: bool = Field(..., description="Binary decision: True if score >= 70")
    aggregated_reason: str = Field(..., description="Combined reasoning from all evaluators")


class QAAgentOutput(BaseModel):
    """Output from the QA validation agent."""
    
    qa_required_human_review: bool = Field(..., description="Flag for human review requirement")
    qa_note: Optional[str] = Field(None, description="QA validation note or concern")


class EvaluationResult(BaseModel):
    """Final output model for the evaluation API."""
    
    liked: bool = Field(..., description="Final binary decision")
    reason: str = Field(..., description="Final explanation prioritizing QA notes")
    compatibility: int = Field(..., ge=0, le=100, description="Final compatibility score")
    ai_swipe_reasons: list[str] = Field(..., description="All reasoning steps from agents")
    models_liked: int = Field(default=5, description="Number of models in agreement")
    models_evaluated: int = Field(default=5, description="Total models evaluated")
    qa_required_human_review: bool = Field(..., description="Human review flag")

