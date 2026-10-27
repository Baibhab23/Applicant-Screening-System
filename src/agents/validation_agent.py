import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.llm_client import LLMClient


class ValidationAgent:
    def __init__(self, mcp_url: str = None, model_name: str = None):
        self.llm_client = LLMClient(model_name)

    async def validate_interview(self, interview_data: dict, candidate_profile: dict = None):
        if candidate_profile is None:
            candidate_profile = {"experience": "Unknown", "skills": []}

        evaluation = await self.llm_client.evaluate_interview(interview_data, candidate_profile)

        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("overall_score", 75),
        }

    def run_validation(self, interview_data: dict, candidate_profile: dict = None):
        return asyncio.run(self.validate_interview(interview_data, candidate_profile))
