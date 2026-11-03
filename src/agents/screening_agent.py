import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp import ClientSession
from mcp.client.sse import sse_client

from utils.llm_client import LLMClient
from utils.config_loader import load_mcp_config


class ScreeningAgent:
    """
    Resume screening agent.

    Job requirements are fetched from the MCP server (get_job_requirements tool)
    so they live in one place — the MCP server — rather than being hardcoded
    in both the agent and the request payload.
    """

    def __init__(self, mcp_url: str = None, model_name: str = None):
        self.llm_client = LLMClient(model_name)
        cfg = load_mcp_config()
        self.mcp_url = mcp_url or cfg["mcpServers"]["interview_validator"]["url"]

    async def process_resume(
        self,
        resume_text: str,
        job_requirements: dict = None,
        role: str = "software_engineer",
    ):
        if job_requirements is None:
            try:
                async with sse_client(self.mcp_url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        resp = await session.call_tool("get_job_requirements", {"role": role})
                        payload = json.loads(resp.content[0].text)
                        job_requirements = payload.get("requirements", payload)
            except Exception:
                job_requirements = {
                    "required_experience": "3+ years",
                    "required_skills": ["Python", "JavaScript", "SQL"],
                    "preferred_skills": ["AWS", "Docker", "Kubernetes"],
                    "education": "Bachelor's degree in CS or related field",
                }

        evaluation = await self.llm_client.evaluate_resume(resume_text, job_requirements)

        if evaluation.get("evaluation_status") == "failed":
            return {
                "ai_evaluation": evaluation,
                "final_score": None,
                "evaluation_status": "failed",
            }

        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("match_score"),
            "evaluation_status": "ok",
        }
