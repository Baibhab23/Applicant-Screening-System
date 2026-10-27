import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_servers.interview_validator import validate_interview, score_interview, get_interview_questions


def test_validate_interview_valid():
    interview_data = {
        "responses": {
            "Q1": "I have five years of Python experience building scalable microservices.",
            "Q2": "I led a team of four engineers on a successful cloud migration project.",
            "Q3": "I use test-driven development and CI/CD pipelines in every project.",
        }
    }
    result = validate_interview(candidate_id="test-1", interview_data=interview_data)
    assert result["is_valid"] is True
    assert "checks" in result


def test_validate_interview_insufficient_responses():
    interview_data = {"responses": {"Q1": "Short"}}
    result = validate_interview(candidate_id="test-2", interview_data=interview_data)
    assert result["checks"]["sufficient_responses"] is False


def test_score_interview_returns_score():
    responses = [
        {"question": "Q1", "response": "I have implemented and developed several projects as a team lead."},
        {"question": "Q2", "response": "I managed a team and successfully delivered the project on time."},
    ]
    result = score_interview(candidate_id="test-3", interview_responses=responses)
    assert "score" in result
    assert result["score"] >= 0


def test_get_interview_questions():
    result = get_interview_questions(role="software_engineer", difficulty="medium")
    assert "questions" in result
    assert len(result["questions"]) > 0
