"""
LangGraph state model for evaluation workflow
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class EvaluationState(BaseModel):
    """LangGraph state model tracking the evaluation process."""
    
    # Input data (stored as dicts for LangGraph compatibility)
    offer: dict[str, Any]
    candidate: dict[str, Any]
    
    # Evaluation agent outputs
    technical_score: Optional[int] = None
    technical_reason: Optional[str] = None
    
    trajectory_score: Optional[int] = None
    trajectory_reason: Optional[str] = None
    
    cultural_score: Optional[int] = None
    cultural_reason: Optional[str] = None
    
    # Scoring agent output
    final_score: Optional[int] = None
    liked: Optional[bool] = None
    aggregated_reason: Optional[str] = None
    
    # QA agent output
    qa_required_human_review: Optional[bool] = None
    qa_note: Optional[str] = None
    
    # Metadata
    models_evaluated: int = Field(default=5, description="Total number of agents")
    models_liked: int = Field(default=5, description="Number of agents in agreement")
    
    class Config:
        arbitrary_types_allowed = True

