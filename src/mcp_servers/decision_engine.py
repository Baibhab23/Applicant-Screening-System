from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

MCP_URL = "http://127.0.0.1:8000/sse"


async def score_applicant(applicant_data: dict) -> dict:
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            score = {"applicant_id": applicant_data.get('id'), "score": 85}
            return score


async def validate_interview(interview_data: dict) -> dict:
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            validation_result = {"interview_id": interview_data.get('id'), "valid": True}
            return validation_result


async def generate_recommendations(applicant_data: dict) -> list:
    recommendations = ["Recommendation 1", "Recommendation 2"]
    return recommendations
