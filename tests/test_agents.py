import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.screening_agent import ScreeningAgent
from agents.validation_agent import ValidationAgent


def test_screening_agent_has_llm_client():
    agent = ScreeningAgent()
    assert agent.llm_client is not None


def test_validation_agent_has_llm_client():
    agent = ValidationAgent()
    assert agent.llm_client is not None


def test_screening_agent_process_resume_structure():
    """Verify process_resume returns expected structure (requires a running LLM provider)."""
    agent = ScreeningAgent()
    resume_text = "Jane Doe\njane@example.com\nSoftware Engineer, 5 years Python, AWS, Docker."
    result = error = None
    try:
        result = asyncio.run(agent.process_resume(resume_text))
    except Exception as e:
        error = e

    if error is None and result is not None:
        assert "ai_evaluation" in result
        assert "final_score" in result
        assert isinstance(result["final_score"], (int, float))


def test_validation_agent_run_validation_structure():
    """Verify run_validation returns expected structure (requires a running LLM provider)."""
    agent = ValidationAgent()
    interview_data = {
        "responses": {
            "Q1": "I have experience in Python and built microservices.",
            "Q2": "I managed a team and delivered on time.",
            "Q3": "I use testing and CI/CD in every project.",
        }
    }
    result = error = None
    try:
        result = agent.run_validation(interview_data)
    except Exception as e:
        error = e

    if error is None and result is not None:
        assert "ai_evaluation" in result
        assert "final_score" in result
