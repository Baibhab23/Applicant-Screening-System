from src.agents.screening_agent import ScreeningAgent
from src.agents.validation_agent import ValidationAgent

def test_screening_agent():
    agent = ScreeningAgent()
    resume_data = {
        "name": "John Doe",
        "experience": 5,
        "skills": ["Python", "Machine Learning", "Data Analysis"]
    }
    result = agent.process_resume(resume_data)
    assert result["status"] == "success"
    assert "extracted_info" in result

def test_validation_agent():
    agent = ValidationAgent()
    interview_data = {
        "candidate_id": 1,
        "responses": ["I am a team player.", "I have experience in Python."],
        "scores": [4, 5]
    }
    result = agent.validate_interview(interview_data)
    assert result["status"] == "validated"
    assert result["score"] >= 0