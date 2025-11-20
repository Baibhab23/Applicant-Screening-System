import asyncio
from gen_ai_hub.proxy.langchain.init_models import init_llm
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.llm_client import LLMClient

class ValidationAgent:
    def __init__(self, mcp_url: str = None, model_name="gpt-4o"):
        """
        Initialize validation agent with SAP AI Core
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

    async def validate_interview(self, interview_data: dict, candidate_profile: dict = None):
        """Validate interview with AI-powered evaluation (no MCP server needed)"""
        
        if candidate_profile is None:
            candidate_profile = {"experience": "Unknown", "skills": []}
        
        # Use SAP AI Core LLM directly for evaluation
        evaluation = await self.llm_client.evaluate_interview(interview_data, candidate_profile)
        
        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("overall_score", 75)
        }

    def run_validation(self, interview_data: dict, candidate_profile: dict = None):
        return asyncio.run(self.validate_interview(interview_data, candidate_profile))