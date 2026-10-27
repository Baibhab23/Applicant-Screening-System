from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

MCP_URL = "http://127.0.0.1:8000/sse"


async def analyze_applicant_data(applicant_info: dict) -> dict:
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            analysis_result = {}
            return analysis_result


def extract_features(applicant_info: dict) -> dict:
    features = {}
    return features


def compare_against_criteria(features: dict, criteria: dict) -> bool:
    is_qualified = False
    return is_qualified
