"""
QA Validation Agent
Detects critical inconsistencies requiring human review.

Inconsistency Detection Rules:
1. Final Score >= 70 (LIKED) but Technical Score < 50
2. Final Score < 70 (REJECTED) but ALL THREE evaluator scores > 80
"""

from typing import Any, Callable

from ..models import EvaluationState, QAAgentOutput


class QAValidationAgent:
    """Agent for validating evaluation consistency and flagging human review."""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(self, state: EvaluationState, executor: Callable) -> dict[str, Any]:
        """Validate evaluation consistency."""
        
        system_prompt = """You are a **QA Validation Agent** responsible for detecting critical inconsistencies in the evaluation.

Your task is to identify situations requiring human review:

**CRITICAL INCONSISTENCY RULE 1:**
If Final Score >= 70 (LIKED) BUT Technical Skills Score < 50:
→ Flag for human review (qa_required_human_review = True)
→ Reason: Candidate lacks fundamental technical competency despite passing overall

**CRITICAL INCONSISTENCY RULE 2:**
If Final Score < 70 (REJECTED) BUT ALL THREE evaluator scores > 80:
→ Flag for human review (qa_required_human_review = True)
→ Reason: All evaluators scored highly but weighted formula rejected - potential edge case

If no critical inconsistencies detected:
→ qa_required_human_review = False
→ qa_note = "No critical inconsistencies detected. Evaluation validated."

Analyze the scores and make your determination."""

        user_prompt = f"""Perform QA validation on this evaluation:

**EVALUATION RESULTS:**
- Technical Skills Score: {state.technical_score}/100
- Career Trajectory Score: {state.trajectory_score}/100
- Cultural Fit Score: {state.cultural_score}/100
- Final Weighted Score: {state.final_score}/100
- Decision: {"LIKED" if state.liked else "REJECTED"}

**INCONSISTENCY CHECK:**

Rule 1: Is Final Score >= 70 AND Technical Score < 50?
- Final Score >= 70: {state.final_score >= 70}
- Technical Score < 50: {state.technical_score < 50}
- Rule 1 Triggered: {state.final_score >= 70 and state.technical_score < 50}

Rule 2: Is Final Score < 70 AND all three scores > 80?
- Final Score < 70: {state.final_score < 70}
- All scores > 80: {state.technical_score > 80 and state.trajectory_score > 80 and state.cultural_score > 80}
- Rule 2 Triggered: {state.final_score < 70 and state.technical_score > 80 and state.trajectory_score > 80 and state.cultural_score > 80}

Determine if human review is required and provide your QA note."""

        result = await executor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=QAAgentOutput,
            agent_name="QA Validation Agent"
        )
        
        return {
            "qa_required_human_review": result.qa_required_human_review,
            "qa_note": result.qa_note
        }

