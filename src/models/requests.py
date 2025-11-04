"""
Request data models for the evaluation API
"""

from typing import Optional
from pydantic import BaseModel, Field


class OfferData(BaseModel):
    """Pydantic model for Offer/Job data structure."""
    
    job_title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Company name")
    contract: str = Field(..., description="Contract type (full-time, part-time, etc.)")
    type: str = Field(..., description="Work type: remote, on-site, hybrid")
    description: str = Field(..., description="Job description")
    salary_range: Optional[str] = Field(None, description="Salary range")
    responsibilities: str = Field(..., description="Key responsibilities")
    experience_required: str = Field(..., description="Required experience level")
    mandatory_skills: list[str] = Field(default_factory=list, description="Mandatory technical skills")
    nice_to_have_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    mandatory_languages: list[str] = Field(default_factory=list, description="Required languages")
    nice_to_have_languages: list[str] = Field(default_factory=list, description="Nice-to-have languages")
    preferred_companies: list[str] = Field(default_factory=list, description="Preferred previous companies")
    extra_requirements_to_consider: Optional[str] = Field(None, description="Additional requirements")


class Education(BaseModel):
    """Candidate education entry."""
    
    degree: str = Field(..., description="Degree type (Bachelor's, Master's, etc.)")
    name: str = Field(..., description="Field of study")
    institute: str = Field(..., description="Educational institution")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")


class Experience(BaseModel):
    """Candidate work experience entry."""
    
    role: str = Field(..., description="Job role/title")
    company: str = Field(..., description="Company name")
    description: str = Field(..., description="Role description and achievements")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    duration: Optional[str] = Field(None, description="Duration of employment")


class Skill(BaseModel):
    """Candidate skill with proficiency level."""
    
    name: str = Field(..., description="Skill name")
    level: Optional[str] = Field(None, description="Proficiency level")


class Language(BaseModel):
    """Candidate language with proficiency level."""
    
    name: str = Field(..., description="Language name")
    level: str = Field(..., description="Proficiency level (native, fluent, intermediate, basic)")


class CandidateData(BaseModel):
    """Pydantic model for Candidate data structure."""
    
    heading: str = Field(..., description="Professional headline/summary")
    experience_years: int = Field(..., description="Total years of professional experience")
    educations: list[Education] = Field(default_factory=list, description="Education history")
    experiences: list[Experience] = Field(default_factory=list, description="Work experience history")
    skills: list[Skill] = Field(default_factory=list, description="Technical and soft skills")
    languages: list[Language] = Field(default_factory=list, description="Language proficiencies")


class EvaluationRequest(BaseModel):
    """Main input model for the evaluation endpoint."""
    
    offer: OfferData = Field(..., description="Job offer data")
    candidate: CandidateData = Field(..., description="Candidate profile data")

