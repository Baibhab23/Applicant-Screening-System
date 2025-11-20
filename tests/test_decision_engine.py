from src.mcp_servers.decision_engine import score_applicant, validate_interview

def test_score_applicant():
    applicant_data = {
        "name": "John Doe",
        "experience": 5,
        "skills": ["Python", "Machine Learning", "Data Analysis"]
    }
    score = score_applicant(applicant_data)
    assert score >= 0  # Assuming score is non-negative

def test_validate_interview():
    interview_data = {
        "candidate_name": "John Doe",
        "responses": ["I have experience in Python.", "I am familiar with machine learning."],
        "scores": [4, 5]
    }
    validation_result = validate_interview(interview_data)
    assert validation_result["status"] == "valid"  # Assuming valid interviews return this status
    assert validation_result["score"] >= 0  # Assuming score is non-negative