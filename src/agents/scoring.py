"""
Scoring & Decision Agent
Applies weighted scoring formula and makes binary decision.

Weights:
- Technical Skills: 50%
- Career Trajectory: 35%
- Cultural Fit: 15%

Decision Rule: liked = True if final_score >= 70
"""

from typing import Any, Callable

from ..models import EvaluationState, ScoringAgentOutput


class ScoringAgent:
    """Agent for calculating final score and making binary decision."""
    
    def __init__(self, llm):
        self.llm = llm
    
    async def evaluate(self, state: EvaluationState, executor: Callable) -> dict[str, Any]:
        """Calculate final score and make decision."""
        
        system_prompt = """You are a **Scoring & Decision Agent** responsible for calculating the final compatibility score.

Your task:
1. Apply weighted scoring formula: (Technical × 0.50) + (Trajectory × 0.35) + (Cultural × 0.15)
2. Calculate the final score (0-100)
3. Make binary decision: LIKED if score >= 70, REJECTED if score < 70
4. Synthesize all reasoning into a cohesive explanation

The formula weights reflect business priorities:
- Technical competency is most critical (50%)
- Career fit is important but secondary (35%)
- Cultural alignment is a supporting factor (15%)

Provide the exact weighted score, binary decision, and comprehensive aggregated reasoning."""

        user_prompt = f"""Calculate the final compatibility score using the weighted formula:

**EVALUATION SCORES:**
- Technical Skills: {state.technical_score}/100 (Weight: 50%)
- Career Trajectory: {state.trajectory_score}/100 (Weight: 35%)
- Cultural Fit: {state.cultural_score}/100 (Weight: 15%)

**REASONING FROM EVALUATORS:**

Technical Skills Assessment:
{state.technical_reason}

Career Trajectory Assessment:
{state.trajectory_reason}

Cultural Fit Assessment:
{state.cultural_reason}

Calculate: Final Score = ({state.technical_score} × 0.50) + ({state.trajectory_score} × 0.35) + ({state.cultural_score} × 0.15)
Decision: LIKED if Final Score >= 70, REJECTED otherwise

Provide the final weighted score, decision, and synthesized reasoning."""

        result = await executor(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ScoringAgentOutput,
            agent_name="Scoring Agent"
        )
        
        return {
            "final_score": result.final_score,
            "liked": result.liked,
            "aggregated_reason": result.aggregated_reason
        }

