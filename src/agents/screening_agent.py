import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.llm_client import LLMClient


class ScreeningAgent:
    def __init__(self, mcp_url: str = None, model_name: str = None):
        self.llm_client = LLMClient(model_name)

    async def process_resume(self, resume_text: str, job_requirements: dict = None):
        if job_requirements is None:
            job_requirements = {
                "required_experience": "3+ years",
                "required_skills": ["Python", "JavaScript", "SQL"],
                "preferred_skills": ["AWS", "Docker", "Kubernetes"],
                "education": "Bachelor's degree in CS or related field",
            }

        evaluation = await self.llm_client.evaluate_resume(resume_text, job_requirements)

        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("match_score", 70),
        }
