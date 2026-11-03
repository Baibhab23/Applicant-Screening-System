import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from utils.llm_client import LLMClient
from utils.config_loader import load_mcp_config


class ValidationAgent:
    """
    Interview validation agent.

    The LLM is the caller of MCP tools: it calls get_scoring_rubric() to
    understand what a good answer looks like, and get_interview_questions()
    to see standard questions for the role — before it evaluates the candidate.
    Flask never calls the MCP server directly; only the LLM does.
    """

    def __init__(self, mcp_url: str = None, model_name: str = None):
        self.llm_client = LLMClient(model_name)
        cfg = load_mcp_config()
        self.mcp_url = mcp_url or cfg["mcpServers"]["interview_validator"]["url"]

    async def validate_interview(
        self,
        interview_data: dict,
        candidate_profile: dict = None,
        role: str = "software_engineer",
    ):
        if candidate_profile is None:
            candidate_profile = {"experience": "Unknown", "skills": []}

        async with sse_client(self.mcp_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)

                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert technical interviewer evaluating interview responses.

Use the available tools to inform your evaluation:
1. Call get_scoring_rubric with the role to understand what a good answer looks like.
2. Call get_interview_questions with the role and difficulty="medium" to see standard questions.

After calling the tools, evaluate the candidate and return ONLY a valid JSON object:
{{
  "technical_score": <0-100>,
  "communication_score": <0-100>,
  "problem_solving_score": <0-100>,
  "cultural_fit_score": <0-100>,
  "overall_score": <0-100>,
  "recommendation": "<STRONG_HIRE|HIRE|MAYBE|NO_HIRE>",
  "key_insights": ["..."],
  "concerns": ["..."]
}}"""),
                    ("human", (
                        "Role: {role}\n\n"
                        "Candidate Profile:\n{candidate_profile}\n\n"
                        "Interview Responses:\n{interview_data}"
                    )),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])

                agent = create_tool_calling_agent(self.llm_client.llm, tools, prompt)
                executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=False,
                    handle_parsing_errors=True,
                )

                result = await executor.ainvoke({
                    "role": role,
                    "interview_data": str(interview_data),
                    "candidate_profile": str(candidate_profile),
                })

        raw = result.get("output", "")
        evaluation = self.llm_client._parse_json_response(raw)

        if evaluation.get("evaluation_status") == "failed":
            return {
                "ai_evaluation": evaluation,
                "final_score": None,
                "evaluation_status": "failed",
            }

        return {
            "ai_evaluation": evaluation,
            "final_score": evaluation.get("overall_score"),
            "evaluation_status": "ok",
        }

    def run_validation(
        self,
        interview_data: dict,
        candidate_profile: dict = None,
        role: str = "software_engineer",
    ):
        return asyncio.run(self.validate_interview(interview_data, candidate_profile, role))
