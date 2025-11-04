"""
Logging service for saving evaluation results to JSON files
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from ..models import EvaluationRequest, EvaluationResult


logger = logging.getLogger(__name__)


def save_evaluation_result(request: EvaluationRequest, result: EvaluationResult, test_name: str) -> Path:
    """
    Save evaluation results to a JSON file with timestamp.
    
    Args:
        request: The evaluation request data
        result: The evaluation result
        test_name: Name of the test case (e.g., 'good_candidate', 'bad_candidate')
        
    Returns:
        Path to the saved file
    """
    # Create results directory if it doesn't exist
    results_dir = Path("evaluation_results")
    results_dir.mkdir(exist_ok=True)
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare data to save
    evaluation_log = {
        "test_name": test_name,
        "timestamp": datetime.now().isoformat(),
        "request": {
            "offer": {
                "job_title": request.offer.job_title,
                "company_name": request.offer.company_name,
                "contract": request.offer.contract,
                "type": request.offer.type,
                "experience_required": request.offer.experience_required,
                "mandatory_skills": request.offer.mandatory_skills,
                "nice_to_have_skills": request.offer.nice_to_have_skills,
                "mandatory_languages": request.offer.mandatory_languages,
            },
            "candidate": {
                "heading": request.candidate.heading,
                "experience_years": request.candidate.experience_years,
                "skills": [{"name": s.name, "level": s.level} for s in request.candidate.skills],
                "languages": [{"name": l.name, "level": l.level} for l in request.candidate.languages],
                "experience_summary": [
                    {"role": exp.role, "company": exp.company, "duration": exp.duration}
                    for exp in request.candidate.experiences
                ]
            }
        },
        "result": {
            "liked": result.liked,
            "compatibility_score": result.compatibility,
            "qa_required_human_review": result.qa_required_human_review,
            "final_reason": result.reason,
            "models_liked": result.models_liked,
            "models_evaluated": result.models_evaluated,
            "detailed_evaluations": result.ai_swipe_reasons
        }
    }
    
    # Save to file
    filename = f"{test_name}_{timestamp}.json"
    filepath = results_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(evaluation_log, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📁 Evaluation result saved to: {filepath}")
    
    return filepath

