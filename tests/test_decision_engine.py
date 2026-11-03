import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_servers.interview_validator import (
    get_scoring_rubric,
    get_job_requirements,
    get_interview_questions,
)


def test_get_scoring_rubric_returns_rubric():
    result = get_scoring_rubric(role="software_engineer")
    assert "rubric" in result
    rubric = result["rubric"]
    assert "technical_depth" in rubric
    assert "problem_solving" in rubric
    assert "red_flags" in rubric


def test_get_scoring_rubric_unknown_role_falls_back_to_default():
    result = get_scoring_rubric(role="wizard")
    assert "rubric" in result
    assert "technical_depth" in result["rubric"]


def test_get_job_requirements_software_engineer():
    result = get_job_requirements(role="software_engineer")
    assert "requirements" in result
    req = result["requirements"]
    assert "required_skills" in req
    assert "Python" in req["required_skills"]
    assert "required_experience" in req


def test_get_job_requirements_data_scientist():
    result = get_job_requirements(role="data_scientist")
    assert "requirements" in result
    req = result["requirements"]
    assert "Machine Learning" in req["required_skills"]


def test_get_job_requirements_unknown_role_falls_back_to_default():
    result = get_job_requirements(role="unknown_role")
    assert "requirements" in result
    assert "required_skills" in result["requirements"]


def test_get_interview_questions_returns_questions():
    result = get_interview_questions(role="software_engineer", difficulty="medium")
    assert "questions" in result
    assert result["count"] > 0
    assert len(result["questions"]) == result["count"]


def test_get_interview_questions_hard_difficulty():
    result = get_interview_questions(role="software_engineer", difficulty="hard")
    assert result["count"] > 0
    assert result["difficulty"] == "hard"
