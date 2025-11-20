import asyncio
from gen_ai_hub.proxy.langchain.init_models import init_llm
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.llm_client import LLMClient

class ScreeningAgent:
    def __init__(self, mcp_url: str = None, model_name="gpt-4o"):
        """
        Initialize screening agent with SAP AI Core
        mcp_url is optional - we don't need custom MCP server
        """
        self.proxy_client = get_proxy_client('gen-ai-hub')
        self.model_name = model_name
        
        # Use GPT-4o via SAP AI Core
        self.llm = init_llm(
            model_name=model_name,
            proxy_client=self.proxy_client,
            temperature=0.7,
            max_tokens=4000
        )
        
        self.llm_client = LLMClient(model_name)

    async def process_resume(self, resume_text: str, job_requirements: dict = None):
        """Process resume with AI-powered evaluation (no MCP server needed)"""
        
        if job_requirements is None:
            job_requirements = {
                "required_experience": "3+ years",
                "required_skills": ["Python", "JavaScript", "SQL"],
                "preferred_skills": ["AWS", "Docker", "Kubernetes"],
                "education": "Bachelor's degree in CS or related field"
            }
        
        # Use SAP AI Core LLM directly for evaluation
        evaluation = await self.llm_client.evaluate_resume(resume_text, job_requirements)
        
        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("match_score", 70)
        }